import json
from comfy_execution.graph import ExecutionBlocker
from .utils import get_category, base64_to_image, base64_to_mask, image_to_base64, images_to_base64
from .api_server import POSTPATHS, OpenOutpainterServingManager


# global server manager
# current does not support more than a single active API workflow
oop_serving = OpenOutpainterServingManager()


########################
#     Serving Node     #
########################

class OpenOutpainterServing:
    CLASSNAME = "OpenOutpainterServingV1"
    NAME = "OpenOutpainter Serving"
    CATEGORY = get_category()

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_server": ("BOOLEAN", {"default": False}),
                "server_address": ("STRING",{"default": "127.0.0.1"}),
                "port": ("INT", {"default": 7860, "min": 1, "max": 65535}),
                "enable_cross_origin_requests": ("BOOLEAN", {"default": False}),
                "request_id": ("INT", {"default": -1, "min": -1, "max": 1125899906842624}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("OOP_REQUEST", "STRING")
    RETURN_NAMES = ("oop_request", "Server status")
    FUNCTION = "serve"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def serve(self, run_server, server_address, port, enable_cross_origin_requests, request_id, unique_id):
        print(f"{self.NAME} start - unique_id: {unique_id}")

        # server settings changed, restart
        if oop_serving.http_running and (
            not run_server or
            oop_serving.server_address != server_address or
            oop_serving.port != port or
            oop_serving.enable_cross_origin_requests != enable_cross_origin_requests
        ):
            oop_serving.stop_server()

        # start server
        if run_server and not oop_serving.http_running:
            oop_serving.start_server(
                server_address=server_address,
                port=port,
                enable_cross_origin_requests=enable_cross_origin_requests,
                node_type=OpenOutpainterServing.CLASSNAME,
                node_id=unique_id,
            )

        data = oop_serving.get_data(request_id=request_id)
        return (data, oop_serving.server_status)


########################
#     Upscale Nodes    #
########################
# upscale image: '/sdapi/v1/extra-single-image/'
# request
# {
#     "resize-mode": 0,
#     "upscaling_resize": "2",
#     "upscaler_1": "Lanczos",
#     "image": "data:image/png;base64,iVBORw0KGgoAAAANkJggg=="
# }
# response
# {
#     "html_info": "<p>Postprocess upscale by: 2.0, Postprocess upscaler: Lanczos</p>",
#     "image": "iVBORw0KGgoAAAANSUhEUgAACAAJggg=="
# }
# only "image" is needed

class OpenOutpainterServingInputUpscale:
    CLASSNAME = "OpenOutpainterServingInputUpscaleV1"
    NAME = "OpenOutpainter Serving Input Upscale"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "oop_request": ("OOP_REQUEST", {"lazy": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "FLOAT")
    RETURN_NAMES = ("image", "scale_by")
    FUNCTION = "out"

    def __init__(self):
        self.command_name = POSTPATHS.PATH_UPSCALE
        pass

    def check_lazy_status(self, oop_request):
        if oop_request is None:
            return ["oop_request"]
        if oop_request.is_command(self.command_name):
            return ["oop_request"]
        return None

    def out(self, oop_request):
        # lazy eval does not work for some reason
        if not oop_request.is_command(self.command_name):
            return (ExecutionBlocker(None), ExecutionBlocker(None))
        return (
            base64_to_image(oop_request.request_data["image"]),
            float(oop_request.request_data["upscaling_resize"]),
        )


class OpenOutpainterServingOutputUpscale:
    CLASSNAME = "OpenOutpainterServingOutputUpscaleV1"
    NAME = "OpenOutpainter Serving Output Upscale"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "oop_request": ("OOP_REQUEST", {"lazy": True}),
                "image": ("IMAGE", {"lazy": True}),
            },
        }

    FUNCTION = "out"
    RETURN_TYPES = ()
    OUTPUT_NODE = True

    def __init__(self):
        self.command_name = POSTPATHS.PATH_UPSCALE
        pass

    def check_lazy_status(self, oop_request, image=None):
        if oop_request is None:
            return ["oop_request"]
        if oop_request.is_command(self.command_name):
            return ["image", "oop_request"]
        return None

    def out(self, oop_request, image=None):
        print(f"{self.NAME} out '{self.command_name}' image: {bool(image is not None)}")
        if image is not None and oop_request.is_command(self.command_name):
            response = {"image": image_to_base64(image)}
            oop_request.finalize(response)
        return {}


############################
#     Interrogate Nodes    #
############################
# caption image: '/sdapi/v1/interrogate':
# request
# {"image":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABggg==","model":"clip"}
# model is hardcoded to always return "clip"
# response
# {"caption":"caption text here"}

class OpenOutpainterServingInputInterrogate:
    CLASSNAME = "OpenOutpainterServingInputInterrogateV1"
    NAME = "OpenOutpainter Serving Input Interrogate"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "oop_request": ("OOP_REQUEST", {"lazy": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "out"

    def __init__(self):
        self.command_name = POSTPATHS.PATH_INTERROGATE
        pass

    def check_lazy_status(self, oop_request):
        if oop_request is None:
            return ["oop_request"]
        if oop_request.is_command(self.command_name):
            return ["oop_request"]
        return None

    def out(self, oop_request):
        # lazy eval does not work for some reason
        if not oop_request.is_command(self.command_name):
            return (ExecutionBlocker(None),)
        return (base64_to_image(oop_request.request_data["image"]),)


class OpenOutpainterServingOutputInterrogate:
    CLASSNAME = "OpenOutpainterServingOutputInterrogateV1"
    NAME = "OpenOutpainter Serving Output Interrogate"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "oop_request": ("OOP_REQUEST", {"lazy": True}),
                "caption": ("STRING", {"lazy": True, "forceInput": True}),
            },
        }

    FUNCTION = "out"
    RETURN_TYPES = ()
    OUTPUT_NODE = True

    def __init__(self):
        self.command_name = POSTPATHS.PATH_INTERROGATE
        pass

    def check_lazy_status(self, oop_request, caption=None):
        if oop_request is None:
            return ["oop_request"]
        if oop_request.is_command(self.command_name):
            return ["caption", "oop_request"]
        return None

    def out(self, oop_request, caption=None):
        print(f"{self.NAME} out '{self.command_name}' caption: {caption}")
        if caption is not None and oop_request.is_command(self.command_name):
            response = {"caption": caption}
            oop_request.finalize(response)
        return {}


########################
#     TXT2IMG Nodes    #
########################
# txt2img: '/sdapi/v1/txt2img':
# request
# {
#     "prompt": "This is a prompt",
#     "negative_prompt": "This is a negative prompt",
#     "seed": "-1",
#     "cfg_scale": 7,
#     "sampler_index": "DDIM",
#     "steps": 30,
#     "denoising_strength": 1,
#     "mask_blur": 8,
#     "batch_size": 1,
#     "width": 128,
#     "height": 128,
#     "n_iter": 3,
#     "mask": "",
#     "init_images": [],
#     "inpaint_full_res": false,
#     "inpainting_fill": 1,
#     "outpainting_fill": 2,
#     "enable_hr": false,
#     "restore_faces": false,
#     "hr_scale": 2,
#     "hr_upscaler": "None",
#     "hr_second_pass_steps": 0,
#     "hr_resize_x": 0,
#     "hr_resize_y": 0,
#     "hr_square_aspect": false,
#     "styles": [],
#     "upscale_x": 2,
#     "hr_denoising_strength": 0.7,
#     "hr_fix_lock_px": 0,
#     "enable_refiner": false,
#     "alwayson_scripts": {}
# }

# response
# {
#     "images": [
#         "iVBORw0KGgoAAAANSUhEUgAAAIAAAACAC5DU117AAAAAElFTkSuQmCC",
#         "iVBORw0KGgoAAAANSUhEUgAAAIAAAACAC5DU117AAAAAElFTkSuQmCC",
#         "iVBORw0KGgoAAAANSUhEUgAAAIAAAACAC5DU117AAAAAElFTkSuQmCC"
#     ],
#     "parameters": {}, # not used
#     "info": {
#         "all_seeds": [
#             2742961909,
#             2742961910,
#             2742961911
#         ],
#     }
# }

class OpenOutpainterServingInputTXT2IMG:
    CLASSNAME = "OpenOutpainterServingInputTXT2IMGV1"
    NAME = "OpenOutpainter Serving Input TXT2IMG"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "oop_request": ("OOP_REQUEST", {"lazy": True}),
            }
        }

    OUTPUTS = {
        "prompt": "STRING",
        "negative_prompt": "STRING",
        "width": "INT",
        "height": "INT",
        "SEED": "INT",
        "steps": "INT",
        "cfg_scale": "FLOAT",
        "batch_size": "INT",
        "n_iter": "INT",
    }
    RETURN_TYPES = tuple(OUTPUTS.values())
    RETURN_NAMES = tuple(OUTPUTS.keys())
    FUNCTION = "out"

    def __init__(self):
        self.command_name = POSTPATHS.PATH_TXT2IMG
        pass

    def check_lazy_status(self, oop_request):
        if oop_request is None:
            return ["oop_request"]
        if oop_request.is_command(self.command_name):
            return ["oop_request"]
        return None

    def out(self, oop_request):
        # lazy eval does not work for some reason
        if not oop_request.is_command(self.command_name):
            return (ExecutionBlocker(None),) * len(self.OUTPUTS)
        request_data = oop_request.request_data
        return (
            request_data["prompt"],
            request_data["negative_prompt"],
            int(request_data["width"]),
            int(request_data["height"]),
            int(request_data["seed"]),
            int(request_data["steps"]),
            float(request_data["cfg_scale"]),
            int(request_data["batch_size"]),
            int(request_data["n_iter"]),
        )


class OpenOutpainterServingOutputTXT2IMG:
    CLASSNAME = "OpenOutpainterServingOutputTXT2IMGV1"
    NAME = "OpenOutpainter Serving Output TXT2IMG"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "oop_request": ("OOP_REQUEST", {"lazy": True}),
                "images": ("IMAGE", {"lazy": True}),
                "SEEDS": ("INT", {"lazy": True, "forceInput": True}),
            },
        }

    FUNCTION = "out"
    RETURN_TYPES = ()
    OUTPUT_NODE = True
    INPUT_IS_LIST = True

    def __init__(self):
        self.command_name = POSTPATHS.PATH_TXT2IMG
        pass

    def check_lazy_status(self, oop_request, images=None, SEEDS=None):
        if oop_request is None:
            return ["oop_request"]
        if oop_request[0] is None:
            return ["oop_request"]
        if oop_request[0].is_command(self.command_name):
            return ["SEEDS", "images", "oop_request"]
        return None

    def out(self, oop_request, images=None, SEEDS=None):
        print(f"{self.NAME} out '{self.command_name}' images: {bool(images is not None)}")
        if images is not None and SEEDS is not None and oop_request[0].is_command(self.command_name):
            response = {
                "images": images_to_base64(images),
                "info": json.dumps({"all_seeds": SEEDS}, default=lambda o: None)
            }
            oop_request[0].finalize(response)
        return {}



########################
#     IMG2IMG Nodes    #
########################
# txt2img: '/sdapi/v1/img2img':
# request
# {
#     "prompt": "This is a prompt",
#     "negative_prompt": "people, person, humans, human, divers, diver, glitch, error, text, watermark, bad quality, blurry",
#     "seed": "-1",
#     "cfg_scale": 7,
#     "steps": 30,
#     "denoising_strength": 0.5,
#     "mask_blur": 8,
#     "batch_size": 1,
#     "width": 512,
#     "height": 512,
#     "n_iter": 3,
#     "mask": "data:image/png;base64,iVBORw0KGgoAAPQAAAABJRU5ErkJggg==",
#     "init_images": ["data:image/png;base64,iVBORwo9jTl4TD/Er4/f5by6KwHISuQmCC"],
#     "image_cfg_scale": 8,
# }

# response
# {
#     "images": ["iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAIAAABAAElFTkSuQmCC"],
#     "parameters": {}, # not used
#     "info": {
#         "all_subseeds": [
#             3242546751,
#             3242546752,
#             3242546753
#         ],
#     }
# }

class OpenOutpainterServingInputIMG2IMG:
    CLASSNAME = "OpenOutpainterServingInputIMG2IMGV1"
    NAME = "OpenOutpainter Serving Input IMG2IMG"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "oop_request": ("OOP_REQUEST", {"lazy": True}),
            }
        }

    OUTPUTS = {
        "init_images": "IMAGE",
        "mask": "MASK",
        "prompt": "STRING",
        "negative_prompt": "STRING",
        "width": "INT",
        "height": "INT",
        "SEED": "INT", # seed
        "steps": "INT",
        "cfg_scale": "FLOAT",
        "denoising_strength": "FLOAT",
        "mask_blur": "INT",
        "ip2p_image_cfg_scale": "FLOAT", # image_cfg_scale
        "batch_size": "INT",
        "n_iter": "INT",
    }
    RETURN_TYPES = tuple(OUTPUTS.values())
    RETURN_NAMES = tuple(OUTPUTS.keys())
    FUNCTION = "out"

    def __init__(self):
        self.command_name = POSTPATHS.PATH_IMG2IMG
        pass

    def check_lazy_status(self, oop_request):
        if oop_request is None:
            return ["oop_request"]
        if oop_request.is_command(self.command_name):
            return ["oop_request"]
        return None

    def out(self, oop_request):
        # lazy eval does not work for some reason
        if not oop_request.is_command(self.command_name):
            return (ExecutionBlocker(None),) * len(self.OUTPUTS)
        request_data = oop_request.request_data
        return (
            base64_to_image(request_data["init_images"][0]),
            base64_to_mask(request_data["mask"]),
            request_data["prompt"],
            request_data["negative_prompt"],
            int(request_data["width"]),
            int(request_data["height"]),
            int(request_data["seed"]),
            int(request_data["steps"]),
            float(request_data["cfg_scale"]),
            float(request_data["denoising_strength"]),
            int(request_data["mask_blur"]),
            float(request_data.get("image_cfg_scale", 0)), # may be missing if txt2img tool calls img2img instead
            int(request_data["batch_size"]),
            int(request_data["n_iter"]),
        )


class OpenOutpainterServingOutputIMG2IMG:
    CLASSNAME = "OpenOutpainterServingOutputIMG2IMGV1"
    NAME = "OpenOutpainter Serving Output IMG2IMG"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "oop_request": ("OOP_REQUEST", {"lazy": True}),
                "images": ("IMAGE", {"lazy": True}),
                "SEEDS": ("INT", {"lazy": True, "forceInput": True}),
            },
        }

    FUNCTION = "out"
    RETURN_TYPES = ()
    OUTPUT_NODE = True
    INPUT_IS_LIST = True

    def __init__(self):
        self.command_name = POSTPATHS.PATH_IMG2IMG
        pass

    def check_lazy_status(self, oop_request, images=None, SEEDS=None):
        if oop_request is None:
            return ["oop_request"]
        if oop_request[0] is None:
            return ["oop_request"]
        if oop_request[0].is_command(self.command_name):
            return ["SEEDS", "images", "oop_request"]
        return None

    def out(self, oop_request, images=None, SEEDS=None):
        print(f"{self.NAME} out '{self.command_name}' images: {bool(images is not None)}")
        if images is not None and SEEDS is not None and oop_request[0].is_command(self.command_name):
            response = {
                "images": images_to_base64(images),
                "info": json.dumps({"all_seeds": SEEDS}, default=lambda o: None)
            }
            oop_request[0].finalize(response)
        return {}


########################



def register_nodes(node_class_mappings=None, node_display_name_mappings=None):
    if node_display_name_mappings is None:
        node_display_name_mappings = {}
    if node_class_mappings is None:
        node_class_mappings = {}

    node_classes = [
        OpenOutpainterServing,

        OpenOutpainterServingInputUpscale,
        OpenOutpainterServingOutputUpscale,

        OpenOutpainterServingInputInterrogate,
        OpenOutpainterServingOutputInterrogate,

        OpenOutpainterServingInputTXT2IMG,
        OpenOutpainterServingOutputTXT2IMG,

        OpenOutpainterServingInputIMG2IMG,
        OpenOutpainterServingOutputIMG2IMG,
    ]

    for node_class in node_classes:
        node_class_mappings[node_class.CLASSNAME] = node_class
        node_display_name_mappings[node_class.CLASSNAME] = node_class.NAME

    return node_class_mappings, node_display_name_mappings

