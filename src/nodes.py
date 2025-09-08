"""
ComfyUI Prompt Companion - API Routes Registration

This module registers all HTTP API endpoints for managing prompt additions and groups.
The actual handler implementations are in separate modules for better organization.

Author: jfcantu
Version: 0.0.2
"""

# Import node classes from separate module
import os
import sys
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

from prompt_companion_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Register API endpoints only when running in ComfyUI
try:
    from server import PromptServer
    print("[ComfyUI-Prompt-Companion] PromptServer imported successfully")
    
    # Import API handlers from separate module
    from api_handlers import (
        get_prompt_additions,
        write_prompt_addition,
        delete_prompt_addition,
        get_prompt_groups,
        write_prompt_group,
        delete_prompt_group
    )
    print("[ComfyUI-Prompt-Companion] API handlers imported successfully")
    
    # Get the routes instance for registering API endpoints
    routes = PromptServer.instance.routes
    print(f"[ComfyUI-Prompt-Companion] Got routes instance: {routes}")
    
    # Register API endpoints using decorator pattern
    PromptServer.instance.routes.get("/prompt-companion/prompt-addition")(get_prompt_additions)
    PromptServer.instance.routes.post("/prompt-companion/prompt-addition")(write_prompt_addition)
    PromptServer.instance.routes.delete("/prompt-companion/prompt-addition/{prompt_addition_name}")(delete_prompt_addition)
    PromptServer.instance.routes.get("/prompt-companion/prompt-group")(get_prompt_groups)
    PromptServer.instance.routes.post("/prompt-companion/prompt-group")(write_prompt_group)
    PromptServer.instance.routes.delete("/prompt-companion/prompt-group/{prompt_group_id}")(delete_prompt_group)
    
    print(f"[ComfyUI-Prompt-Companion] API routes registered successfully - Total routes: {len(routes)}")
    
except ImportError as e:
    # Running outside ComfyUI - routes won't be registered
    print(f"[ComfyUI-Prompt-Companion] Running outside ComfyUI - API routes not registered: {e}")
except Exception as e:
    print(f"[ComfyUI-Prompt-Companion] Error during route registration: {e}")
    import traceback
    traceback.print_exc()

# Re-export node mappings for ComfyUI to find
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
