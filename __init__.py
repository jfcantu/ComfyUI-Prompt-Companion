# =============================================================================
# Standard Library Imports
# =============================================================================

import logging
import os

"""
ComfyUI-Prompt-Companion Custom Node Package

A comprehensive prompt management system for ComfyUI that provides hierarchical organization,
template-based subprompts, and advanced prompt manipulation capabilities.

This package includes:
- Core prompt manipulation nodes
- Checkpoint loading integration
- Persistent JSON storage for prompt templates
- Web-based editing interface with tree view
- Circular reference detection and validation

Author: ComfyUI-Prompt-Companion
License: See LICENSE file
"""

# =============================================================================
# Package Metadata
# =============================================================================

__version__ = "0.1.0"
__author__ = "ComfyUI-Prompt-Companion"
__email__ = "jfcantu@gmail.com"
__description__ = "A node that lets you save and reuse parts of prompts (embeddings, quality keywords, and so on.)"

# =============================================================================
# Constants & Configuration
# =============================================================================

# Web directory for frontend extensions
WEB_DIRECTORY = os.path.join(os.path.dirname(__file__), "web")

# Required web files for ComfyUI integration
_REQUIRED_WEB_FILES = [
    "edit_dialog.js",
    "tree_view.js",
    "prompt_companion.css",
    "extensions.js",
]

# NOTE: ComfyUI handles custom data types automatically through node validation
# No explicit registration is required - SUBPROMPT will be treated as a regular type

# =============================================================================
# Third-Party Imports (ComfyUI)
# =============================================================================

# ComfyUI server integration (imported in initialization section)

# =============================================================================
# Local/Project Imports
# =============================================================================

# Core functionality imports
try:
    from .core import (
        Subprompt,
        SubpromptCollection,
        ResolvedPrompts,
        SubpromptError,
        CircularReferenceError,
        ValidationError,
        get_global_storage,
    )
except Exception as e:
    logging.getLogger(__name__).error(f"Failed to import core functionality: {e}")
    raise

# Node classes imports
try:
    from .nodes import (
        PromptCompanionAddSubpromptNode,
        PromptCompanionSubpromptToStringsNode,
        PromptCompanionStringsToSubpromptNode,
        PromptCompanionLoadCheckpointWithSubpromptNode,
        NODE_CLASS_MAPPINGS as NODES_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS as NODES_DISPLAY_MAPPINGS,
    )
except Exception as e:
    logging.getLogger(__name__).error(f"Failed to import node classes: {e}")
    raise

# =============================================================================
# Module-Level Variables
# =============================================================================

# Set up logging
logger = logging.getLogger(__name__)

# ComfyUI node registration mappings
NODE_CLASS_MAPPINGS = {
    "PromptCompanion_AddSubprompt": PromptCompanionAddSubpromptNode,
    "PromptCompanion_SubpromptToStrings": PromptCompanionSubpromptToStringsNode,
    "PromptCompanion_StringsToSubprompt": PromptCompanionStringsToSubpromptNode,
    "PromptCompanion_LoadCheckpointWithSubprompt": PromptCompanionLoadCheckpointWithSubpromptNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptCompanion_AddSubprompt": "Prompt Companion: Add Subprompt",
    "PromptCompanion_SubpromptToStrings": "Prompt Companion: Subprompt to Strings",
    "PromptCompanion_StringsToSubprompt": "Prompt Companion: Strings to Subprompt",
    "PromptCompanion_LoadCheckpointWithSubprompt": "Prompt Companion: Load Checkpoint with Subprompt",
}

# Package exports
__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
    "Subprompt",
    "SubpromptCollection",
    "ResolvedPrompts",
    "get_global_storage",
]

# =============================================================================
# Utility Functions
# =============================================================================

def _ensure_web_files():
    """Ensure required web files exist and are accessible for ComfyUI integration."""
    missing_files = []
    for file in _REQUIRED_WEB_FILES:
        if not os.path.exists(os.path.join(WEB_DIRECTORY, file)):
            missing_files.append(file)
    
    if missing_files:
        logger.warning(f"Missing web files: {missing_files}")


def _print_node_info():
    """Print information about loaded nodes for debugging purposes."""
    try:
        # Reserved for future debugging functionality
        pass
    except Exception as e:
        logger.error(f"Error loading nodes: {e}")


def _register_api_routes():
    """Register API routes with ComfyUI's server instance."""
    try:
        from server import PromptServer
        from .api_routes import (
            get_subprompts,
            get_subprompt,
            create_subprompt,
            update_subprompt,
            delete_subprompt,
            get_folders,
            create_folder,
            delete_folder,
            rename_folder_by_path,
            get_subprompt_dropdown_options,
        )

        # Access ComfyUI's route system (standard pattern used by ComfyUI-Manager)
        routes = PromptServer.instance.routes

        # Register API routes using ComfyUI's standard decorator pattern
        @routes.get("/prompt_companion/subprompts")
        async def api_get_subprompts(request):
            return await get_subprompts(request)

        @routes.get("/prompt_companion/subprompts/dropdown_options")
        async def api_get_subprompt_dropdown_options(request):
            return await get_subprompt_dropdown_options(request)

        @routes.post("/prompt_companion/subprompts")
        async def api_create_subprompt(request):
            return await create_subprompt(request)

        @routes.get("/prompt_companion/subprompts/{id}")
        async def api_get_subprompt(request):
            return await get_subprompt(request)

        @routes.put("/prompt_companion/subprompts/{id}")
        async def api_update_subprompt(request):
            return await update_subprompt(request)

        @routes.delete("/prompt_companion/subprompts/{id}")
        async def api_delete_subprompt(request):
            return await delete_subprompt(request)

        @routes.get("/prompt_companion/folders")
        async def api_get_folders(request):
            return await get_folders(request)

        @routes.post("/prompt_companion/folders")
        async def api_create_folder(request):
            return await create_folder(request)

        @routes.delete("/prompt_companion/folders/{folder_path}")
        async def api_delete_folder(request):
            return await delete_folder(request)

        @routes.put("/prompt_companion/folders/{folder_path}")
        async def api_rename_folder(request):
            return await rename_folder_by_path(request)

    except ImportError as e:
        logger.error(f"Failed to import ComfyUI server: {e}")
    except Exception as e:
        logger.error(f"Failed to register API routes: {e}")

# =============================================================================
# Module Initialization
# =============================================================================

# Initialize global storage system
try:
    _storage = get_global_storage()
except Exception as e:
    logger.warning(f"Storage system initialization warning: {e}")

# Verify web files are available
_ensure_web_files()

# Print node information for debugging
_print_node_info()

# Register API routes with ComfyUI server
_register_api_routes()
