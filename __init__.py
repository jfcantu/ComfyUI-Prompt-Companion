"""Top-level package for prompt_companion."""

WEB_DIRECTORY = "./src/web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

__author__ = """ComfyUI-Prompt-Companion"""
__email__ = "jfcantu@gmail.com"
__version__ = "0.0.1"

from .src.nodes import NODE_CLASS_MAPPINGS
from .src.nodes import NODE_DISPLAY_NAME_MAPPINGS
