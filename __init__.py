"""Top-level package for openoutpaint_comfyui_interface."""

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]

__author__ = """Without Ordinary"""
__email__ = "without-ordinary@users.noreply.github.com"
__version__ = "0.0.1"

WEB_DIRECTORY = "./web"

# from .py.nodes import register_nodes as openoutpaint_serving_register_nodes
# NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = openoutpaint_serving_register_nodes()

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
def add_nodes(node_classes):
    for node_class in node_classes:
        NODE_CLASS_MAPPINGS[node_class.CLASSNAME] = node_class
        NODE_DISPLAY_NAME_MAPPINGS[node_class.CLASSNAME] = node_class.NAME

from .py.nodes_serving import get_nodes as get_nodes_serving
from .py.nodes_upscale import get_nodes as get_nodes_upscale
from .py.nodes_interrogate import get_nodes as get_nodes_interrogate
from .py.nodes_txt2img import get_nodes as get_nodes_txt2img
from .py.nodes_img2img import get_nodes as get_nodes_img2img
from .py.nodes_style import get_nodes as get_nodes_style
from .py.nodes_model import get_nodes as get_nodes_model

add_nodes(get_nodes_serving())
add_nodes(get_nodes_upscale())
add_nodes(get_nodes_interrogate())
add_nodes(get_nodes_txt2img())
add_nodes(get_nodes_img2img())
add_nodes(get_nodes_style())
add_nodes(get_nodes_model())

