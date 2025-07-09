import re
from comfy_execution.graph import ExecutionBlocker
from .utils import get_category


######################
#     Model Nodes    #
######################
# Model selection from OOP occurs on a separate API from image gen because A1111 always has a model loaded
# and its changed via its own api call. So some things with how this is handled are funky to deal with that.

class OpenOutpainterServingModelDefine:
    CLASSNAME = "OpenOutpainterServingModelDefineV1"
    NAME = "OpenOutpainter Serving Model Define"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_names": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "oop_models": ("OOP_MODELS", {}),
            }
        }

    OUTPUTS = {
        "oop_models": "OOP_MODELS",
    }
    RETURN_TYPES = tuple(OUTPUTS.values())
    RETURN_NAMES = tuple(OUTPUTS.keys())
    FUNCTION = "out"

    def out(self, model_names, oop_models = None):
        if oop_models is None: oop_models = []
        oop_models.extend(x for x in model_names.splitlines() if x not in oop_models)
        return (oop_models,)


class OpenOutpainterServingModelSwitch:
    CLASSNAME = "OpenOutpainterServingModelSwitchV1"
    NAME = "OpenOutpainter Serving Model Switch"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "oop_request":      ("OOP_REQUEST", {}),
                "model_name":       ("STRING", {"multiline": False, "default": ""}),
                "use_regex":        ("BOOLEAN", {"default": False, "tooltip": "Use model_name input as regex pattern instead of exact string match. Use (?aiLmsux) format for flags, eg. (?i)pattern for ignore case."}),
                "output_model_name_on_no_match": ("BOOLEAN", {"default": True, "tooltip": "Otherwise blocks execution on the model_name output."}),
            },
        }

    OUTPUTS = {
        "oop_request_if_true": "OOP_REQUEST",
        "oop_request_if_false": "OOP_REQUEST",
        "boolean": "BOOLEAN",
        "selected_model": "STRING",
    }
    RETURN_TYPES = tuple(OUTPUTS.values())
    RETURN_NAMES = tuple(OUTPUTS.keys())
    FUNCTION = "out"

    def out(self, oop_request, model_name, use_regex, output_model_name_on_no_match):
        test = bool(model_name == oop_request.oop_selected_model)
        if use_regex:
            try:
                match = re.search(model_name, oop_request.oop_selected_model)
                test = match is not None
            except re.error:
                test = False
        if test:
            return (
                oop_request, # oop_request_if_true
                ExecutionBlocker(None), # oop_request_if_false
                True, # boolean
                oop_request.oop_selected_model, # selected_model
            )
        else:
            return (
                ExecutionBlocker(None), # oop_request_if_true
                oop_request, # oop_request_if_false
                False, # boolean
                oop_request.oop_selected_model if output_model_name_on_no_match else ExecutionBlocker(None), # selected_model
            )


#########################
#     Register Nodes    #
#########################
# I'm lazy and don't want to define a bunch of duplicate data in separate file to register nodes.

def get_nodes():
    return [
        OpenOutpainterServingModelDefine,
        OpenOutpainterServingModelSwitch,
    ]

