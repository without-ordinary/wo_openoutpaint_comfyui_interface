import re
from comfy_execution.graph import ExecutionBlocker
from .utils import get_category


######################
#     Model Nodes    #
######################

# "Model" in classnames is legacy from before rename to "Checkpoints"

class OpenOutpainterServingModelDefine:
    CLASSNAME = "OpenOutpainterServingModelDefineV1"
    NAME = "OpenOutpainter Serving Checkpoints List"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "checkpoint_names": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "oop_checkpoints": ("OOP_CHECKPOINTS", {}),
            }
        }

    OUTPUTS = {
        "oop_checkpoints": "OOP_CHECKPOINTS",
    }
    RETURN_TYPES = tuple(OUTPUTS.values())
    RETURN_NAMES = tuple(OUTPUTS.keys())
    FUNCTION = "out"

    def out(self, checkpoint_names, oop_checkpoints = None):
        if oop_checkpoints is None: oop_checkpoints = []
        oop_checkpoints.extend(x for x in checkpoint_names.splitlines() if x not in oop_checkpoints)
        return (oop_checkpoints,)


class OpenOutpainterServingModelSwitch:
    CLASSNAME = "OpenOutpainterServingModelSwitchV1"
    NAME = "OpenOutpainter Serving Checkpoint Switch"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "oop_request":      ("OOP_REQUEST", {}),
                "checkpoint_name":  ("STRING", {"multiline": False, "default": ""}),
                "use_regex":        ("BOOLEAN", {"default": False, "tooltip": "Use model_name input as regex pattern instead of exact string match. Use (?aiLmsux) format for flags, eg. (?i)pattern for ignore case."}),
                "output_checkpoint_name_on_no_match": ("BOOLEAN", {"default": True, "tooltip": "Otherwise blocks execution on the model_name output."}),
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

    def out(self, oop_request, checkpoint_name, use_regex, output_checkpoint_name_on_no_match):
        selected_checkpoint = oop_request.request_data.get('checkpoint', "")
        test = bool(checkpoint_name == selected_checkpoint)
        if use_regex:
            try:
                match = re.search(checkpoint_name, selected_checkpoint)
                test = match is not None
            except re.error:
                test = False
        if test:
            return (
                oop_request, # oop_request_if_true
                ExecutionBlocker(None), # oop_request_if_false
                True, # boolean
                selected_checkpoint, # selected_model
            )
        else:
            return (
                ExecutionBlocker(None), # oop_request_if_true
                oop_request, # oop_request_if_false
                False, # boolean
                selected_checkpoint if output_checkpoint_name_on_no_match else ExecutionBlocker(None), # selected_model
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

