import json
from comfy_execution.graph import ExecutionBlocker
from .utils import get_category, base64_to_image, base64_to_mask, images_to_base64
from .api_server import POSTPATHS


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


#########################
#     Register Nodes    #
#########################
# I'm lazy and don't want to define a bunch of duplicate data in separate file to register nodes.

def get_nodes():
    return [
        OpenOutpainterServingInputIMG2IMG,
        OpenOutpainterServingOutputIMG2IMG,
    ]

