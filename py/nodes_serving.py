from comfy_execution.graph import ExecutionBlocker
from .utils import get_category
from .api_server import OpenOutpainterServingManager


# global server manager
# current does not support more than a single active API workflow
# multiple serving nodes also unsupported be behavior unknown
# TODO: possibly add support for that
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
                "spammy_debug": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "oop_styles": ("OOP_STYLES", {}),
                "oop_checkpoints": ("OOP_CHECKPOINTS", {}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("OOP_REQUEST", "STRING")
    RETURN_NAMES = ("oop_request", "Server status")
    FUNCTION = "serve"

    # run this node every execution, it is speshul.
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def serve(
        self, run_server, server_address, port, enable_cross_origin_requests, request_id, spammy_debug,
        unique_id,
        oop_styles = None, oop_checkpoints = None,
    ):
        print(f"{self.NAME} start - unique_id: {unique_id}")

        # add progress handler each run
        oop_serving.add_progress_handler()

        # store styles to respond to API request for this list
        oop_serving.oop_styles = oop_styles or {}
        print(f"oop_styles: {oop_styles}")

        # store models for API requests
        oop_serving.oop_checkpoints = oop_checkpoints or ["Placeholder_Checkpoint_Name"]
        print(f"oop_checkpoints: {oop_checkpoints}")

        # server settings changed, restart
        if oop_serving.http_running and (
            not run_server or
            oop_serving.server_address != server_address or
            oop_serving.port != port or
            oop_serving.enable_cross_origin_requests != enable_cross_origin_requests or
            oop_serving.spammy_debug != spammy_debug
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
                spammy_debug=spammy_debug,
            )

        oop_request = oop_serving.get_data(request_id)

        if oop_request is None:
            oop_request = ExecutionBlocker(None)
        else:
            oop_request.extra_data["oop_styles"] = oop_styles
            oop_request.extra_data["oop_checkpoints"] = oop_checkpoints # not currently used

        return (oop_request, oop_serving.server_status)


#########################
#     Register Nodes    #
#########################
# I'm lazy and don't want to define a bunch of duplicate data in separate file to register nodes.

def get_nodes():
    return [
        OpenOutpainterServing,
    ]

