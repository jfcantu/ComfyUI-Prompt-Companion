"""Top-level package for prompt_companion."""

WEB_DIRECTORY = "./src/web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

__author__ = """ComfyUI-Prompt-Companion"""
__email__ = "jfcantu@gmail.com"
__version__ = "0.0.1"

# Import and register everything from the src package
import sys
import os

# Add src directory to path to enable imports
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, src_dir)

try:
    # Import the node mappings using importlib to avoid conflicts
    import importlib.util
    nodes_file_path = os.path.join(src_dir, "nodes.py")
    
    spec = importlib.util.spec_from_file_location("prompt_companion_nodes", nodes_file_path)
    prompt_companion_nodes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prompt_companion_nodes)
    
    NODE_CLASS_MAPPINGS = prompt_companion_nodes.NODE_CLASS_MAPPINGS
    NODE_DISPLAY_NAME_MAPPINGS = prompt_companion_nodes.NODE_DISPLAY_NAME_MAPPINGS
    print(f"[ComfyUI-Prompt-Companion] Successfully imported node mappings: {list(NODE_CLASS_MAPPINGS.keys())}")
except ImportError as e:
    print(f"[ComfyUI-Prompt-Companion] Import error: {e}")
    import traceback
    traceback.print_exc()
    # Fallback empty mappings to prevent ComfyUI from crashing
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
except Exception as e:
    print(f"[ComfyUI-Prompt-Companion] Unexpected error during import: {e}")
    import traceback
    traceback.print_exc()
    # Fallback empty mappings to prevent ComfyUI from crashing
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
