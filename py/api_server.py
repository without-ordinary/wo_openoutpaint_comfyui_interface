import math
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import time
from server import PromptServer
from comfy.utils import ProgressBar, set_progress_bar_global_hook
from typing_extensions import override
from comfy_execution.progress import ProgressHandler, NodeProgressState, PreviewImageTuple, add_progress_handler, get_progress_state
from .utils import preview_to_base64, print_list_or_dic

# API POST endpoints that are handled by nodes
class POSTPATHS:
    PATH_UPSCALE = '/sdapi/v1/extra-single-image/'
    PATH_INTERROGATE = '/sdapi/v1/interrogate'
    PATH_TXT2IMG = '/sdapi/v1/txt2img'
    PATH_IMG2IMG = '/sdapi/v1/img2img'
    PATH_OPTIONS = '/sdapi/v1/options/'

VALID_POST_PATHS = [
    POSTPATHS.PATH_UPSCALE,
    POSTPATHS.PATH_INTERROGATE,
    POSTPATHS.PATH_TXT2IMG,
    POSTPATHS.PATH_IMG2IMG,
    POSTPATHS.PATH_OPTIONS,
]

class ProgressData:
    def __init__(self):
        self.preview_image = None
        self.start_time = None

    def store_preview_image(self, preview_image):
        if preview_image is not None:
            self.preview_image = preview_image

    def get_progress(self, skip_current_image):
        nodes = get_progress_state().nodes
        progress_value = 0
        progress_max = 0
        for node_id, state in nodes.items():
            progress_value =+ state["value"]
            progress_max =+ state["max"]

        current_image = None
        if self.preview_image is not None and not skip_current_image:
            image = self.preview_image[1]
            current_image = preview_to_base64(image)

        progress = 0
        eta = 0
        if self.start_time is not None and progress_value > 0:
            progress = progress_value / progress_max
            eta = ((time.time() - self.start_time) / progress_value) * (progress_max - progress_value)
        print(f"========== get_progress progress: {progress}  {progress_value}/{progress_max}  eta: {eta}")

        return progress, current_image, eta

    def reset(self):
        self.preview_image = None
        self.start_time = None

class OpenOutpainterProgressHandler(ProgressHandler):
    """
    Handler that stores progress to reply to OpenOutpainter's requires for progress.
    """

    def __init__(self, progress: ProgressData):
        super().__init__("openoutpainter")
        self.progress = progress
        self.progress.reset()

    @override
    def start_handler(self, node_id: str, state: NodeProgressState, prompt_id: str):
        if self.progress.start_time is None:
            self.progress.start_time = time.time()
        pass

    @override
    def update_handler(
        self,
        node_id: str,
        value: float,
        max_value: float,
        state: NodeProgressState,
        prompt_id: str,
        image: PreviewImageTuple | None = None,
    ):
        self.progress.store_preview_image(image)

    @override
    def finish_handler(self, node_id: str, state: NodeProgressState, prompt_id: str):
        pass

    @override
    def reset(self):
        self.progress.reset()


class OpenOutpainterRequest:
    def __init__(self, request_id, request_data, path):
        self.id = request_id
        self.request_data = request_data
        self.extra_data = {}
        self.path = path
        self.output_ready = threading.Event()
        self.output = None

    def is_command(self, command):
        return self.path is not None and command == self.path

    def finalize(self, result):
        self.output = result
        self.output_ready.set()


######################
#     API Server     #
######################

class OpenOutpainterServingManager:
    def __init__(self):
        self.server_address = None
        self.port = None
        self.enable_cross_origin_requests = None
        self.node_type = None
        self.node_id = None
        self.requests = {}
        self.request_id = 0 # next request id
        self.http_running = False
        self.server_status = ""
        self.server = None
        self.thread = None
        self.comfy_progress_hook = None
        self.progress = ProgressData()
        self.oop_styles = {}
        self.oop_models = []
        self.spammy_debug = False


    def start_server(self, server_address, port, enable_cross_origin_requests, node_type, node_id, spammy_debug = False):
        # server config from workflow
        self.server_address = server_address
        self.port = port
        self.enable_cross_origin_requests = enable_cross_origin_requests
        self.node_type = node_type
        self.node_id = node_id
        self.spammy_debug = spammy_debug

        if not self.http_running:
            try:
                self.thread = threading.Thread(target=self.http_handler, daemon=True)
                self.thread.start()
                self.http_running = True
                self.server_status = f"Server is running on {self.server_address}:{self.port}"
                print(f"OpenOutpaint API server running on port {self.port}")
            except Exception as e:
                self.http_running = False
                self.server_status = "ERROR: Could not start OpenOutpaint API server: {}".format(e)
                raise RuntimeError(self.server_status )

    def stop_server(self):
        for request_id, request in self.requests.items():
            print(f"OpenOutpaint API server stop_server, canceling request_id: {request_id} request: {request}")
            request.finalize({})
        if self.http_running:
            self.http_running = False
            if self.server:
                # server may have failed to start
                self.server.shutdown()
                self.server.server_close()
                self.thread.join()
            self.server_status = "Server not running"
            print(f"OpenOutpaint API server stopped on port {self.port}")

    def http_handler(self):
        class RequestHandler(BaseHTTPRequestHandler):
            def do_OPTIONS(self2):
                if (self.enable_cross_origin_requests):
                    self2.send_response(200)
                    self2.send_header('Access-Control-Allow-Origin', '*')
                    self2.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self2.send_header('Access-Control-Allow-Headers', '*')
                    self2.end_headers()

            def log_message(self, format, *args):
                # Override method to suppress noisy logging
                return

            def do_POST(self2):
                print(f"OpenOutpaint Received POST request: {self2.path}")

                # unsupported command
                if not self2.path in VALID_POST_PATHS:
                    self2.send_response(404)
                    self2.send_header('Content-type', 'application/json')
                    self2.cors_headers()
                    self2.end_headers()
                    self2.wfile.write(json.dumps({"error": "Command not found"}).encode('utf-8'))
                    return


                content_length = int(self2.headers['Content-Length'])
                post_data = self2.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                # debug request
                if self.spammy_debug:
                    print_list_or_dic(f"do_POST ({self2.path})", data)

                # /sdapi/v1/options/ POST just needs to be told everything is ok
                if self2.path == POSTPATHS.PATH_OPTIONS:
                    self2.send_response(200)
                    self2.send_header('Content-type', 'application/json')
                    self2.cors_headers()
                    self2.end_headers()
                    self2.wfile.write(json.dumps({"status": "Whatever that was, it worked. Stop complaining. :O"}).encode('utf-8'))
                    return

                request = OpenOutpainterRequest(self.request_id, data, self2.path)
                self.requests[self.request_id] = request
                self.request_id += 1

                # start workflow from webui so user can interact with it
                self.queue_prompt(request)

                # for some reason this was needed to fix wait not working sometimes
                request.output_ready.clear()

                # waits here till workflow finished running
                # if workflow errors, just manually run workflow again with same req id to complete API request
                request.output_ready.wait()

                request.output_ready.clear()

                response = request.output

                self2.send_response(200)
                self2.send_header('Content-type', 'application/json')
                self2.cors_headers()
                self2.end_headers()
                self2.wfile.write(json.dumps(response).encode('utf-8'))

                # clean up
                del self.requests[request.id]

                print("OpenOutpaint do_POST finished")

            def do_GET(self2):
                response = self.process_get_request(self2.path)

                # debug response
                if self.spammy_debug:
                    print_list_or_dic(f"do_GET ({self2.path})", response, True)

                # unsupported command
                if not response:
                    self2.send_response(404)
                    self2.send_header('Content-type', 'application/json')
                    self2.cors_headers()
                    self2.end_headers()
                    self2.wfile.write(json.dumps({"error": "Command not found"}).encode('utf-8'))
                    return

                self2.send_response(200)
                self2.send_header('Content-type', 'application/json')
                self2.cors_headers()
                self2.end_headers()
                self2.wfile.write(json.dumps(response).encode('utf-8'))

            def cors_headers(self2):
                if (self.enable_cross_origin_requests):
                    self2.send_header('Access-Control-Allow-Origin', '*')
                    self2.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self2.send_header('Access-Control-Allow-Headers', '*')

        self.server = ThreadingHTTPServer((self.server_address, self.port), RequestHandler)
        self.server.serve_forever()

    # trigger workflow to run from webui :)
    def queue_prompt(self, request):
        PromptServer.instance.send_sync("wo_QueuePrompt", {
            "node_type": self.node_type,
            "node_id": self.node_id,
            "port": self.port,
            "request_id": request.id,
        })

    def get_data(self, request_id):
        print(f"get_data: start r:{request_id}")
        return self.requests.get(request_id, None)

    def add_progress_handler(self):
        add_progress_handler(OpenOutpainterProgressHandler(self.progress))

    def process_get_request(self, url):
        url = urlparse(url)
        path = url.path

        print(f"process_get_request: {path}")

        match path:
            case '/startup-events':
                # output is not used for anything other than printing out server
                # startup errors when there is a connection error
                return {"status": "ok"}

            case '/sdapi/v1/interrupt':
                # cancel running gen
                # not yet implemented
                # ComfyUI doesn't respond super well to stopping anyway
                return {"hello": "ok"}

            case '/sdapi/v1/progress':
                # get progress of current running gen
                # request: skip_current_image: false = return latent preview
                # response: see notes below

                query = parse_qs(url.query)
                skip_current_image = query.get('skip_current_image', 'false')
                if isinstance(skip_current_image, list):
                    skip_current_image = skip_current_image[0]
                skip_current_image = str(skip_current_image).lower() != 'false'

                progress, current_image, eta = self.progress.get_progress(skip_current_image)

                return {
                    "progress": progress, # float
                    "eta_relative": eta, # estimated time remaining in seconds
                    "current_image": current_image, # latent preview as a base64 encoded png
                }

            case '/sdapi/v1/options':
                # Gets the current settings and config of the backend to fill in ui controls
                # and check for supported configuration
                # I don't use those controls in OOP, and not implemented
                # so mostly placeholder info can be returned that makes OOP not complain
                # data that is used:
                # `use_scale_latent_for_hires_fix` is False or undefined
                # `sd_model_checkpoint` for currently "loaded"/selected checkpoint
                # `sd_checkpoint_hash` only checked if the above is undefined
                # `img2img_color_correction` is not True
                # `inpainting_mask_weight` is set to 1.0
                return {
                    "status": "ok",
                    "sd_model_checkpoint": "", # TODO: make openoutpaint not change settings based on what the api returns
                    "sd_checkpoint_hash": "",
                    "img2img_color_correction": False,
                    "inpainting_mask_weight": 1.0,
                }

            case '/sdapi/v1/upscalers':
                # return list of upscalers, can just be dummy option and config this within workflow
                # only "name" is required
                return [
                    {"name": "None"},  # can be excluded, is ignored by oop
                    {"name": "Lanczos"},
                ]

            case '/sdapi/v1/sd-models':
                # return list of checkpoints, can just be dummy option and config this within workflow
                # only "title" and "sha256", the hash is only used for selecting the current returned from options
                # oop gets happy if the title contains "inpainting"
                # [
                #     {
                #         "title": "Placeholder_Checkpoint_Name",
                #         "sha256": "69",
                #     },
                # ]
                output = []
                for model_name in self.oop_models:
                    output.append({
                        "title": model_name,
                        "sha256": model_name, # fun fact, this doesn't actually have to be a hash
                    })
                return output

            case '/sdapi/v1/loras':
                # return list of loras, can be empty and config this within workflow
                # only "name" is used
                return [
                    {"name": "Configure LoRAs in workflow"},
                ]

            case '/sdapi/v1/samplers':
                # return list of samplers, can just be dummy option and config this within workflow
                # only "name" is used
                return [
                    {"name": "Configure sampler in workflow"},
                ]

            case '/sdapi/v1/schedulers':
                # return list of schedulers, can just be dummy option and config this within workflow
                # only "name" and "label" are used
                return [
                    {"name": "automatic", "label": "Automatic"},
                ]

            case '/sdapi/v1/prompt-styles':
                # return list of A1111 prompt-styles
                # These are passed by as a multiple selected list by name for txt2img and img2img in "styles"
                # only "name" is used, but the prompts are displayed in the tooltip for each
                # {"name": "", "prompt": "", "negative_prompt":""},
                return list(self.oop_styles.values())

            ########################
            # Extensions Functions #
            ########################

            case '/sdapi/v1/scripts':
                # list of extensions
                # OOP only looks for controlnet and dynamic prompts to enable those features in its UI
                # extension support in OOP is not very complete
                # cn can be omitted as can be done better in the workflow manually
                # return almost the minimum to make OOP not complain
                return {
                    "txt2img": [
                        "extra options",
                        "openoutpaint",
                        "refiner",
                        "sampler",
                        "seed"
                    ],
                    "img2img": [
                        "extra options",
                        "openoutpaint",
                        "refiner",
                        "sampler",
                        "seed"
                    ]
                }

            case '/controlnet/version':
                # a1111 cn extension version, needs to be > 0 to enable ui
                # sending 0 to disable, use workflow instead
                return {"version": 0}

            case '/controlnet/settings':
                # number of ref layers needs to be not < 2 or triggers warning
                return {"control_net_unit_count": 2}

            case '/controlnet/model_list':
                # list of controlnet models
                # use workflow instead, send empty
                return {"model_list": []}

            case '/controlnet/module_list':
                # list of controlnet modules
                # not sure if can just be empty it not used
                return {
                    "module_list": ["none", "inpaint"],
                    "module_detail": {
                        "none": {
                            "model_free": False,
                            "sliders": []
                        },
                        "inpaint": {
                            "model_free": False,
                            "sliders": []
                        }
                    }
                }

        return None

