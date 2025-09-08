# Import the node classes and register API endpoints
from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Export the mappings for ComfyUI to find
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
