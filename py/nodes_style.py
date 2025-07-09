from comfy_execution.graph import ExecutionBlocker
from .utils import get_category


######################
#     Style Nodes    #
######################
# "Prompt Styles" is an A1111 feature where it adds saved prompts to the current prompt.
# In OOP, it functions as multi-select list below the prompts.
# This opens it up to creative uses outside of the indented use,
# though that use can still be use if implemented in the workflow.

class OpenOutpainterServingStyleDefine:
    CLASSNAME = "OpenOutpainterServingStyleDefineV1"
    NAME = "OpenOutpainter Serving Style Define"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "style_name":       ("STRING", {"multiline": False, "default": ""}),
                "prompt":           ("STRING", {"multiline": True, "default": ""}),
                "negative_prompt":  ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "oop_styles": ("OOP_STYLES", {}),
            }
        }

    OUTPUTS = {
        "oop_styles": "OOP_STYLES",
    }
    RETURN_TYPES = tuple(OUTPUTS.values())
    RETURN_NAMES = tuple(OUTPUTS.keys())
    FUNCTION = "out"

    def out(self, style_name, prompt, negative_prompt, oop_styles = None):
        if oop_styles is None: oop_styles = {}
        # will overwrite previous styles of the same name
        oop_styles[style_name] = {
            "name": style_name,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
        }
        return (oop_styles,)


class OpenOutpainterServingStyleGet:
    CLASSNAME = "OpenOutpainterServingStyleGetV1"
    NAME = "OpenOutpainter Serving Style Get"
    CATEGORY = get_category()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "oop_request": ("OOP_REQUEST", {}),
                "style_name": ("STRING", {"multiline": False, "default": ""}),
                "empty_strings_on_false": ("BOOLEAN", {"default": True, "tooltip": "Otherwise blocks execution on the prompt outputs."}),
            },
        }

    OUTPUTS = {
        "oop_request_if_true": "OOP_REQUEST",
        "oop_request_if_false": "OOP_REQUEST",
        "boolean": "BOOLEAN",
        "prompt": "STRING",
        "negative_prompt": "STRING",
    }
    RETURN_TYPES = tuple(OUTPUTS.values())
    RETURN_NAMES = tuple(OUTPUTS.keys())
    FUNCTION = "out"

    def out(self, oop_request, style_name, empty_strings_on_false):
        request_data = oop_request.request_data
        if "styles" not in request_data:
            return (
                ExecutionBlocker(None), # oop_request_if_true
                ExecutionBlocker(None), # oop_request_if_false
                False, # boolean
                "" if empty_strings_on_false else ExecutionBlocker(None), # prompt
                "" if empty_strings_on_false else ExecutionBlocker(None), # negative_prompt
            )
        styles = request_data["styles"]
        oop_styles = oop_request.extra_data["oop_styles"]
        if style_name in styles and style_name in oop_styles:
            return (
                oop_request, # oop_request_if_true
                ExecutionBlocker(None), # oop_request_if_false
                True, # boolean
                oop_styles[style_name]["prompt"], # prompt
                oop_styles[style_name]["negative_prompt"], # negative_prompt
            )
        else:
            return (
                ExecutionBlocker(None), # oop_request_if_true
                oop_request, # oop_request_if_false
                False, # boolean
                "" if empty_strings_on_false else ExecutionBlocker(None), # prompt
                "" if empty_strings_on_false else ExecutionBlocker(None), # negative_prompt
            )


#########################
#     Register Nodes    #
#########################
# I'm lazy and don't want to define a bunch of duplicate data in separate file to register nodes.

def get_nodes():
    return [
        OpenOutpainterServingStyleDefine,
        OpenOutpainterServingStyleGet,
    ]

