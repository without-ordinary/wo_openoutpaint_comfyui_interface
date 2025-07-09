from comfy_execution.graph import ExecutionBlocker
from .utils import get_category, base64_to_image
from .api_server import POSTPATHS


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

#########################
#     Register Nodes    #
#########################
# I'm lazy and don't want to define a bunch of duplicate data in separate file to register nodes.

def get_nodes():
    return [
        OpenOutpainterServingInputInterrogate,
        OpenOutpainterServingOutputInterrogate,
    ]

