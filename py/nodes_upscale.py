from comfy_execution.graph import ExecutionBlocker
from .utils import get_category, base64_to_image, image_to_base64
from .api_server import POSTPATHS


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


#########################
#     Register Nodes    #
#########################
# I'm lazy and don't want to define a bunch of duplicate data in separate file to register nodes.

def get_nodes():
    return [
        OpenOutpainterServingInputUpscale,
        OpenOutpainterServingOutputUpscale,
    ]

