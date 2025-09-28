"""
API Routes for ComfyUI-Prompt-Companion

This module provides REST API endpoints for managing subprompts from the web interface.
Integrates with ComfyUI's server to provide JSON API for CRUD operations.
"""

import json
import logging
import traceback
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from typing import Dict, Any

# Import core functionality
from .core.storage import get_global_storage
from .core.subprompt import Subprompt, ValidationError, CircularReferenceError
from .core.folder import Folder, FolderValidationError, build_folder_hierarchy
from .core.validation import validate_subprompt_structure

logger = logging.getLogger(__name__)

# Global storage instance
storage = get_global_storage()


def get_subprompt_folder_path(storage, subprompt) -> str:
    """
    Calculate actual folder path from folder_id hierarchy.
    
    Args:
        storage: Storage instance for folder lookups
        subprompt: Subprompt object with folder_id
        
    Returns:
        Hierarchical folder path (e.g., "Models/SD15") or empty string for root
    """
    # Handle both Subprompt objects and dict data
    if hasattr(subprompt, 'folder_id'):
        folder_id = subprompt.folder_id
    else:
        folder_id = subprompt.get('folder_id')
        
    if not folder_id:
        return ""
    
    try:
        # Get the folder object by ID
        folder = storage.load_folder_by_id(folder_id)
        if not folder:
            return ""
        
        # Load all folders and build hierarchy for path calculation
        all_folders = storage.load_all_folders()
        folder_lookup = build_folder_hierarchy(all_folders)
        
        # Calculate hierarchical path
        return folder.get_path(folder_lookup)
        
    except Exception as e:
        logger.warning(f"Error calculating folder path for folder_id {folder_id}: {e}")
        return ""


def check_for_circular_references(subprompt: Subprompt, all_subprompts: list[Subprompt]) -> bool:
    """
    Check if a subprompt would create circular references.
    
    Args:
        subprompt: The subprompt to validate
        all_subprompts: List of all existing subprompts (including the one being validated)
        
    Returns:
        True if circular references detected, False otherwise
    """
    try:
        # Convert JavaScript nested_subprompts format to order format for validation
        validation_subprompt = Subprompt(
            id=subprompt.id,
            name=subprompt.name,
            positive=subprompt.positive,
            negative=subprompt.negative,
            trigger_words=subprompt.trigger_words,
            order=subprompt.order,
            folder_path=subprompt.folder_path,
            **subprompt.metadata
        )
        
        # Check if nested_subprompts field needs conversion
        nested_list = None
        if hasattr(subprompt, 'nested_subprompts') and subprompt.nested_subprompts:
            nested_list = subprompt.nested_subprompts
        elif subprompt.metadata and 'nested_subprompts' in subprompt.metadata:
            nested_list = subprompt.metadata['nested_subprompts']
        
        # Apply field conversion if needed
        if nested_list and nested_list != []:
            converted_order = []
            for item in nested_list:
                if item == "[Self]":
                    converted_order.append("attached")
                else:
                    converted_order.append(item)
            validation_subprompt.order = converted_order
        
        # Convert list to dict for validation (temporary for compatibility)
        subprompt_dict = {s.id: s for s in all_subprompts}
        
        # Try to resolve the subprompt - this will raise CircularReferenceError if circular
        validation_subprompt.resolve_nested(subprompt_dict)
        return False  # No circular reference
        
    except CircularReferenceError:
        return True  # Circular reference detected
    except Exception:
        # Other errors don't indicate circular references
        return False


async def get_subprompts(request: Request) -> Response:
    """Get all subprompts as a list"""
    
    try:
        subprompts = storage.load_all_subprompts()
        
        # Convert to JSON-serializable format as list
        result = []
        for subprompt in subprompts:
            result.append(subprompt.to_dict())
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Failed to get subprompts: {e}")
        # If storage fails, return empty list instead of error
        return web.json_response([])


async def get_subprompt_dropdown_options(request: Request) -> Response:
    """Get subprompt dropdown options with folder paths - matches INPUT_TYPES output"""
    
    try:
        # Use the same logic as PromptCompanionAddSubpromptNode._get_subprompts_with_folder_paths
        from .nodes.prompt_nodes import PromptCompanionAddSubpromptNode
        
        dropdown_options = PromptCompanionAddSubpromptNode._get_subprompts_with_folder_paths()
        
        return web.json_response(dropdown_options)
        
    except Exception as e:
        logger.error(f"Failed to get dropdown options: {e}")
        # Return fallback with just "None"
        return web.json_response(["None"])


async def get_subprompt(request: Request) -> Response:
    """Get a specific subprompt by UUID"""
    try:
        subprompt_id = request.match_info["id"]
        
        # Load all subprompts and search by UUID
        subprompts = storage.load_all_subprompts()
        subprompt = None
        
        for s in subprompts:
            if s.id == subprompt_id:
                subprompt = s
                break
        
        if subprompt:
            return web.json_response(subprompt.to_dict())
        else:
            return web.json_response({"error": "Subprompt not found"}, status=404)
    except Exception as e:
        logger.error(f"Failed to get subprompt {request.match_info.get('id')}: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def create_subprompt(request: Request) -> Response:
    """Create a new subprompt"""
    try:
        data = await request.json()
        
        # Validate required fields
        if "name" not in data:
            return web.json_response({"error": "Missing required field: name"}, status=400)
        
        subprompt_name = data["name"]
        
        # Create temporary subprompt object to calculate its folder path
        temp_subprompt = Subprompt.from_dict(data)
        current_folder_path = get_subprompt_folder_path(storage, temp_subprompt)
        
        # Load all subprompts for validation and auditing
        all_subprompts = storage.load_all_subprompts()
        
        # Check for duplicates in same folder using calculated paths
        folder_distribution = {}
        
        for sp in all_subprompts:
            calculated_folder = get_subprompt_folder_path(storage, sp)
            if not calculated_folder:
                folder_key = "[ROOT_FOLDER]"
            else:
                folder_key = calculated_folder
            
            folder_distribution[folder_key] = folder_distribution.get(folder_key, 0) + 1
        
        
        # FIXED VALIDATION: Use calculated folder paths for duplicate checking
        same_folder_subprompts = []
        for s in all_subprompts:
            existing_folder_path = get_subprompt_folder_path(storage, s)
            
            
            if existing_folder_path == current_folder_path and s.name == subprompt_name:
                same_folder_subprompts.append(s)
        
        
        if same_folder_subprompts:
            folder_display = current_folder_path if current_folder_path else "root folder"
            logger.warning(f"DUPLICATE DETECTED: '{subprompt_name}' already exists in calculated folder '{current_folder_path}'")
            return web.json_response({
                "error": f"A subprompt named '{subprompt_name}' already exists in {folder_display}"
            }, status=409)
        
        # Create subprompt object (UUID will be auto-generated)
        subprompt = Subprompt.from_dict(data)
        
        # Check for circular references before saving
        validation_subprompts = all_subprompts + [subprompt]  # Include this subprompt in validation
        
        if check_for_circular_references(subprompt, validation_subprompts):
            return web.json_response({
                "error": "Circular reference detected: This subprompt configuration would create an infinite loop"
            }, status=400)
        
        # Save to storage
        success = storage.save_subprompt(subprompt)
        
        if success:
            return web.json_response(subprompt.to_dict(), status=201)
        else:
            return web.json_response({"error": "Failed to save subprompt"}, status=500)
            
    except ValidationError as e:
        return web.json_response({"error": f"Validation error: {e}"}, status=400)
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Failed to create subprompt: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def update_subprompt(request: Request) -> Response:
    """Update an existing subprompt by UUID"""
    try:
        subprompt_id = request.match_info["id"]
        data = await request.json()
        
        # Ensure the ID is preserved in the data
        data["id"] = subprompt_id
        
        # Find existing subprompt by UUID
        all_subprompts = storage.load_all_subprompts()
        existing_subprompt = None
        
        for s in all_subprompts:
            if s.id == subprompt_id:
                existing_subprompt = s
                break
        
        if not existing_subprompt:
            return web.json_response({"error": "Subprompt not found"}, status=404)
        
        # Create updated subprompt object
        subprompt = Subprompt.from_dict(data)
        
        # Check for circular references before saving
        validation_subprompts = [s if s.id != subprompt_id else subprompt for s in all_subprompts]
        
        if check_for_circular_references(subprompt, validation_subprompts):
            return web.json_response({
                "error": "Circular reference detected: This subprompt configuration would create an infinite loop"
            }, status=400)
        
        # Save to storage
        success = storage.save_subprompt(subprompt)
        
        if success:
            return web.json_response(subprompt.to_dict())
        else:
            return web.json_response({"error": "Failed to update subprompt"}, status=500)
            
    except ValidationError as e:
        return web.json_response({"error": f"Validation error: {e}"}, status=400)
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Failed to update subprompt {request.match_info.get('id')}: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def delete_subprompt(request: Request) -> Response:
    """Delete a subprompt by UUID with cascade cleanup of references"""
    try:
        subprompt_id = request.match_info["id"]
        
        # Use the storage delete method which now includes cascade cleanup
        success = storage.delete_subprompt(subprompt_id)
        
        if success:
            return web.json_response({"message": "Subprompt deleted successfully with cascade cleanup"})
        else:
            return web.json_response({"error": "Subprompt not found"}, status=404)
    except Exception as e:
        logger.error(f"Failed to delete subprompt {request.match_info.get('id')}: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def get_folders(request: Request) -> Response:
    """Get all folders as a list of folder objects"""
    
    try:
        folders = storage.load_all_folders()
        
        # Convert to JSON-serializable format as list
        result = []
        for folder in folders:
            result.append(folder.to_dict())
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Failed to get folders: {e}")
        # If storage fails, return empty list instead of error
        return web.json_response([])


async def create_folder(request: Request) -> Response:
    """Create a new folder with UUID-based identification"""
    try:
        data = await request.json()
        
        # Handle both new format (name, parent_id) and legacy format (folder_path)
        if "name" in data:
            # New format: create folder with name and optional parent_id
            folder_name = data["name"].strip()
            if not folder_name:
                return web.json_response({"error": "Folder name cannot be empty"}, status=400)
            
            parent_id = data.get("parent_id")
            
            # Validate parent_id if provided
            if parent_id:
                parent_folder = storage.load_folder_by_id(parent_id)
                if not parent_folder:
                    return web.json_response({"error": "Parent folder not found"}, status=404)
            
            # Check for name conflicts in the same parent
            existing_folders = storage.load_all_folders()
            for existing_folder in existing_folders:
                if existing_folder.name == folder_name and existing_folder.parent_id == parent_id:
                    parent_name = "root" if not parent_id else storage.load_folder_by_id(parent_id).name
                    return web.json_response({
                        "error": f"A folder named '{folder_name}' already exists in {parent_name}"
                    }, status=409)
            
            # Create folder object
            folder = Folder(name=folder_name, parent_id=parent_id)
            
        elif "folder_path" in data:
            # Legacy format: create folder from path
            folder_path = data["folder_path"].strip()
            if not folder_path:
                return web.json_response({"error": "Folder path cannot be empty"}, status=400)
            
            # Check if folder already exists by path
            existing_folders = storage.load_all_folders()
            folder_lookup = build_folder_hierarchy(existing_folders)
            
            for existing_folder in existing_folders:
                if existing_folder.get_path(folder_lookup) == folder_path:
                    return web.json_response({"error": "Folder already exists"}, status=409)
            
            # Create folder from path
            folder = Folder.from_path(folder_path, folder_lookup)
        else:
            return web.json_response({"error": "Missing required field: 'name' or 'folder_path'"}, status=400)
        
        # Save folder
        success = storage.save_folder(folder)
        
        if success:
            return web.json_response(folder.to_dict(), status=201)
        else:
            return web.json_response({"error": "Failed to create folder"}, status=500)
            
    except FolderValidationError as e:
        return web.json_response({"error": f"Validation error: {e}"}, status=400)
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Failed to create folder: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def get_folder(request: Request) -> Response:
    """Get a specific folder by UUID"""
    try:
        folder_id = request.match_info["id"]
        
        # Load folder by UUID
        folder = storage.load_folder_by_id(folder_id)
        
        if folder:
            return web.json_response(folder.to_dict())
        else:
            return web.json_response({"error": "Folder not found"}, status=404)
    except Exception as e:
        logger.error(f"Failed to get folder {request.match_info.get('id')}: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def update_folder(request: Request) -> Response:
    """Update an existing folder by UUID"""
    try:
        folder_id = request.match_info["id"]
        data = await request.json()
        
        # Ensure the ID is preserved in the data
        data["id"] = folder_id
        
        # Find existing folder by UUID
        existing_folder = storage.load_folder_by_id(folder_id)
        if not existing_folder:
            return web.json_response({"error": "Folder not found"}, status=404)
        
        # Create updated folder object
        folder = Folder.from_dict(data)
        
        # Validate folder move if parent_id changed
        if folder.parent_id != existing_folder.parent_id:
            all_folders = storage.load_all_folders()
            if not folder.can_move_to(folder.parent_id, all_folders):
                return web.json_response({
                    "error": "Cannot move folder: would create circular reference"
                }, status=400)
        
        # Save to storage
        success = storage.update_folder(folder)
        
        if success:
            return web.json_response(folder.to_dict())
        else:
            return web.json_response({"error": "Failed to update folder"}, status=500)
            
    except FolderValidationError as e:
        return web.json_response({"error": f"Validation error: {e}"}, status=400)
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Failed to update folder {request.match_info.get('id')}: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def delete_folder(request: Request) -> Response:
    """Delete a folder and optionally all its subprompts and nested folders"""
    try:
        # Handle both 'id' and 'folder_path' parameters due to routing issues
        folder_id = None
        if "id" in request.match_info:
            folder_id = request.match_info["id"]
        elif "folder_path" in request.match_info:
            folder_id = request.match_info["folder_path"]  # Route matching issue - using UUID as folder_path
        else:
            return web.json_response({"error": "Missing folder ID in URL"}, status=400)
        
        
        # Validate folder ID
        if not folder_id or folder_id == "null" or folder_id == "undefined":
            return web.json_response({"error": "Invalid folder ID"}, status=400)
        
        # Find folder by UUID
        try:
            folder = storage.load_folder_by_id(folder_id)
        except Exception as e:
            logger.error(f"DELETE FOLDER API: Error during folder lookup: {e}")
            return web.json_response({"error": f"Error loading folder: {e}"}, status=500)
            
        if not folder:
            return web.json_response({"error": "Folder not found"}, status=404)
        
        # Get query parameter for whether to delete subprompts
        delete_subprompts = request.query.get("delete_subprompts", "true").lower() == "true"
        
        deleted_subprompt_count = 0
        deleted_folder_count = 0
        
        if delete_subprompts:
            # Get all folders and subprompts to find nested items
            all_folders = storage.load_all_folders()
            all_subprompts = storage.load_all_subprompts()
            folder_lookup = build_folder_hierarchy(all_folders)
            
            # Find all descendant folders
            descendant_folders = folder.get_descendants(all_folders)
            
            # Delete all subprompts in target folder and all descendant folders
            folders_to_check = [folder] + descendant_folders
            
            for check_folder in folders_to_check:
                # Find subprompts in this folder by checking folder_path or folder_id
                folder_path = check_folder.get_path(folder_lookup)
                folder_subprompts = []
                
                for subprompt in all_subprompts:
                    # Support both old folder_path and new folder_id references
                    subprompt_folder_match = False
                    
                    if hasattr(subprompt, 'folder_id') and subprompt.folder_id == check_folder.id:
                        subprompt_folder_match = True
                    elif hasattr(subprompt, 'folder_path') and subprompt.folder_path == folder_path:
                        subprompt_folder_match = True
                    
                    if subprompt_folder_match:
                        folder_subprompts.append(subprompt)
                
                # Delete subprompts
                for subprompt in folder_subprompts:
                    if storage.delete_subprompt(subprompt.id):
                        deleted_subprompt_count += 1
            
            # Delete all descendant folders (deepest first)
            descendant_folders.sort(key=lambda f: len(f.get_descendants(all_folders)), reverse=True)
            for descendant_folder in descendant_folders:
                if storage.delete_folder(descendant_folder.id):
                    deleted_folder_count += 1
        
        # Delete the target folder itself
        folder_deleted = storage.delete_folder(folder_id)
        
        if folder_deleted:
            deleted_folder_count += 1  # Count the main folder
            
            message = f"Folder '{folder.name}' deleted successfully"
            if delete_subprompts:
                if deleted_subprompt_count > 0:
                    message += f" along with {deleted_subprompt_count} subprompts"
                if deleted_folder_count > 1:  # More than just the main folder
                    message += f" and {deleted_folder_count - 1} nested folders"
                
            return web.json_response({
                "message": message,
                "deleted_subprompts": deleted_subprompt_count,
                "deleted_folders": deleted_folder_count
            })
        else:
            return web.json_response({"error": "Failed to delete folder"}, status=500)
        
    except Exception as e:
        logger.error(f"Failed to delete folder {request.match_info.get('id')}: {e}")
        return web.json_response({"error": str(e)}, status=500)


# Legacy endpoint for backward compatibility
async def rename_folder_by_path(request: Request) -> Response:
    """Rename a folder by path (legacy endpoint for backward compatibility)"""
    try:
        old_path = request.match_info["folder_path"]
        data = await request.json()
        
        if "new_path" not in data:
            return web.json_response({"error": "Missing required field: new_path"}, status=400)
        
        new_path = data["new_path"].strip()
        if not new_path:
            return web.json_response({"error": "New folder path cannot be empty"}, status=400)
        
        # Find folder by path
        folder = storage.get_folder_by_path(old_path)
        if not folder:
            return web.json_response({"error": "Folder not found"}, status=404)
        
        # Update folder name based on new path
        new_path_parts = new_path.split('/')
        new_name = new_path_parts[-1]
        
        # Create updated folder
        updated_folder = Folder(
            id=folder.id,
            name=new_name,
            parent_id=folder.parent_id,
            created=folder.created,
            updated=folder.updated
        )
        
        # Save updated folder
        success = storage.update_folder(updated_folder)
        
        if success:
            return web.json_response({
                "message": f"Folder renamed from '{old_path}' to '{new_path}'",
                "folder": updated_folder.to_dict()
            })
        else:
            return web.json_response({"error": "Failed to update folder"}, status=500)
        
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Failed to rename folder {request.match_info.get('folder_path')}: {e}")
        return web.json_response({"error": str(e)}, status=500)


def setup_api_routes(server_instance):
    """Set up API routes using ComfyUI's proper RouteTableDef pattern"""
    
    try:
        # Import aiohttp web for RouteTableDef
        from aiohttp import web
        
        # Create RouteTableDef for our routes
        routes = web.RouteTableDef()
        
        # Subprompts endpoints using RouteTableDef pattern
        routes.get("/prompt_companion/subprompts")(get_subprompts)
        routes.get("/prompt_companion/subprompts/dropdown_options")(get_subprompt_dropdown_options)
        routes.post("/prompt_companion/subprompts")(create_subprompt)
        routes.get("/prompt_companion/subprompts/{id}")(get_subprompt)
        routes.put("/prompt_companion/subprompts/{id}")(update_subprompt)
        routes.delete("/prompt_companion/subprompts/{id}")(delete_subprompt)
        
        # Folders endpoints
        routes.get("/prompt_companion/folders")(get_folders)
        routes.post("/prompt_companion/folders")(create_folder)
        
        # Legacy endpoint for backward compatibility - MUST be registered BEFORE {id} routes to avoid conflicts
        routes.put("/prompt_companion/folders/path/{folder_path}")(rename_folder_by_path)
        routes.get("/prompt_companion/folders/{id}")(get_folder)
        routes.put("/prompt_companion/folders/{id}")(update_folder)
        routes.delete("/prompt_companion/folders/{id}")(delete_folder)
        
        # Add our routes to the server's app (ComfyUI pattern)
        if hasattr(server_instance, 'app'):
            server_instance.app.add_routes(routes)
        else:
            raise Exception("Server instance missing app attribute")
        
        
    except Exception as e:
        logger.error(f"API setup failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

