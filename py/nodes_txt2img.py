import json
from comfy_execution.graph import ExecutionBlocker
from .utils import get_category, images_to_base64
from .api_server import POSTPATHS


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


#########################
#     Register Nodes    #
#########################
# I'm lazy and don't want to define a bunch of duplicate data in separate file to register nodes.

def get_nodes():
    return [
        OpenOutpainterServingInputTXT2IMG,
        OpenOutpainterServingOutputTXT2IMG,
    ]

