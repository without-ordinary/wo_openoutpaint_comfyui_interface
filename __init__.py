"""Top-level package for openoutpaint_comfyui_interface."""

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]

__author__ = """Without Ordinary"""
__email__ = "without-ordinary@users.noreply.github.com"
__version__ = "0.0.1"


from .py.nodes import register_nodes as openoutpaint_serving_register_nodes
NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = openoutpaint_serving_register_nodes()


WEB_DIRECTORY = "./web"
