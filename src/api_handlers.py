"""
API Request Handlers for Prompt Companion

This module contains all HTTP request handlers for the REST API endpoints.
Separated from the main nodes.py file for better organization and testing.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from urllib.parse import unquote

from aiohttp import web
from server import PromptServer

from extension_config import CONFIG_PATH, PROMPT_ADDITIONS, PromptAddition, PromptGroup


def save_prompt_definitions() -> None:
    """
    Save current prompt definitions to disk and notify clients.
    
    This function:
    1. Serializes the current prompt additions and groups to JSON
    2. Writes the data to the configuration file
    3. Broadcasts the update to all connected clients
    
    Raises:
        IOError: If the file cannot be written
        JSONEncodeError: If the data cannot be serialized
    """
    # Ensure the directory exists before writing
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    
    with open(CONFIG_PATH, "w") as f:
        json.dump(PROMPT_ADDITIONS.prompt_additions_as_dict(), f, indent=2)

    # Send updated data to all connected clients
    PromptServer.instance.send_sync(
        "prompt-companion.addition-list", PROMPT_ADDITIONS.prompt_additions_as_dict()
    )


def validate_request_json(request_data: Any) -> tuple[bool, Optional[str], Optional[list[str]]]:
    """
    Validate basic request JSON structure.
    
    Args:
        request_data: The parsed JSON data from the request
        
    Returns:
        Tuple of (is_valid, error_message, error_details)
    """
    if not isinstance(request_data, dict):
        return False, "Request body must be a JSON object", ["Invalid data format"]
    
    return True, None, None


def validate_name_field(data: Dict[str, Any], field_name: str = "name") -> tuple[bool, Optional[str], Optional[list[str]]]:
    """
    Validate name field in request data.
    
    Args:
        data: Request data dictionary
        field_name: Name of the field to validate
        
    Returns:
        Tuple of (is_valid, error_message, error_details)
    """
    if field_name not in data or not data[field_name]:
        return False, f"Missing required field: {field_name}", [f"Field '{field_name}' is required"]
    
    name = data[field_name].strip()
    if not name or len(name) > 255:
        return False, "Invalid name", ["Name must be between 1 and 255 characters"]
    
    return True, None, None


def create_success_response(message: str, data: Any, status: int = 200) -> web.Response:
    """
    Create a standardized success response.
    
    Args:
        message: Success message
        data: Response data
        status: HTTP status code
        
    Returns:
        JSON response object
    """
    return web.json_response({
        "success": True,
        "message": message,
        "data": data,
        "errors": []
    }, status=status)


def create_error_response(message: str, errors: list[str], status: int = 400) -> web.Response:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        errors: List of error details
        status: HTTP status code
        
    Returns:
        JSON response object
    """
    return web.json_response({
        "success": False,
        "message": message,
        "errors": errors
    }, status=status)


async def get_prompt_additions(request: web.Request) -> web.Response:
    """
    Get all prompt additions and groups.
    
    Args:
        request: HTTP request object
        
    Returns:
        JSON response with prompt additions and groups data
    """
    try:
        if PROMPT_ADDITIONS is None:
            return create_error_response(
                "Prompt additions not initialized",
                ["PROMPT_ADDITIONS is None - configuration not loaded"],
                status=500
            )
            
        return create_success_response(
            "Prompt additions retrieved successfully",
            PROMPT_ADDITIONS.prompt_additions_as_dict()
        )
    except Exception as e:
        logging.error(f"Server error retrieving prompt additions: {e}")
        return create_error_response(
            "Failed to retrieve prompt additions",
            ["An unexpected error occurred"],
            status=500
        )


async def write_prompt_addition(request: web.Request) -> web.Response:
    """
    Create or update a prompt addition.
    
    Args:
        request: HTTP request containing JSON data for the prompt addition
        
    Returns:
        JSON response with updated prompt data
    """
    try:
        prompt_addition_data = await request.json()
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in prompt addition request: {e}")
        return create_error_response(
            "Invalid JSON format",
            [str(e)],
            status=400
        )

    # Input validation
    is_valid, message, errors = validate_request_json(prompt_addition_data)
    if not is_valid:
        return create_error_response(message or "Validation error", errors or [], status=400)
    
    # Validate required fields
    is_valid, message, errors = validate_name_field(prompt_addition_data)
    if not is_valid:
        return create_error_response(message or "Validation error", errors or [], status=400)

    name = prompt_addition_data["name"].strip()

    try:
        PROMPT_ADDITIONS.create_or_update_prompt_addition(
            PromptAddition(
                name,
                prompt_addition_data.get("trigger_words", ""),
                prompt_addition_data.get("positive_prompt_addition_text", ""),
                prompt_addition_data.get("negative_prompt_addition_text", ""),
                prompt_addition_data.get("id"),
            )
        )
        
        save_prompt_definitions()
        
        return create_success_response(
            "Prompt addition saved successfully",
            PROMPT_ADDITIONS.prompt_additions_as_dict()
        )
        
    except ValueError as e:
        logging.error(f"Validation error in prompt addition: {e}")
        return create_error_response(
            "Validation error",
            [str(e)],
            status=400
        )
    except Exception as e:
        logging.error(f"Server error in prompt addition: {e}")
        return create_error_response(
            "Internal server error",
            ["An unexpected error occurred"],
            status=500
        )


async def delete_prompt_addition(request: web.Request) -> web.Response:
    """
    Delete a specific prompt addition by name.
    
    Args:
        request: HTTP request containing prompt_addition_name in URL path
        
    Returns:
        JSON response with updated prompt additions data
    """
    prompt_addition_name = request.match_info.get("prompt_addition_name")
    
    # Validate prompt addition name
    if not prompt_addition_name:
        return create_error_response(
            "Prompt addition name is required",
            ["Missing prompt addition name in URL"],
            status=400
        )
    
    # URL decode the name in case it contains special characters
    prompt_addition_name = unquote(prompt_addition_name)
    
    try:
        PROMPT_ADDITIONS.delete_prompt_addition(prompt_addition_name)
        save_prompt_definitions()
        
        return create_success_response(
            f"Prompt addition '{prompt_addition_name}' deleted successfully",
            PROMPT_ADDITIONS.prompt_additions_as_dict()
        )
        
    except KeyError:
        return create_error_response(
            f"Prompt addition '{prompt_addition_name}' not found",
            [f"No prompt addition with name '{prompt_addition_name}' exists"],
            status=404
        )
    except Exception as e:
        logging.error(f"Server error deleting prompt addition '{prompt_addition_name}': {e}")
        return create_error_response(
            "Failed to delete prompt addition",
            ["An unexpected error occurred"],
            status=500
        )


async def get_prompt_groups(request: web.Request) -> web.Response:
    """
    Get all prompt groups (same as get_prompt_additions for now).
    
    Args:
        request: HTTP request object
        
    Returns:
        JSON response with prompt groups data
    """
    try:
        return create_success_response(
            "Prompt groups retrieved successfully",
            PROMPT_ADDITIONS.prompt_additions_as_dict()
        )
    except Exception as e:
        logging.error(f"Server error retrieving prompt groups: {e}")
        return create_error_response(
            "Failed to retrieve prompt groups",
            ["An unexpected error occurred"],
            status=500
        )


async def write_prompt_group(request: web.Request) -> web.Response:
    """
    Create or update a prompt group.
    
    Args:
        request: HTTP request containing JSON data for the prompt group
        
    Returns:
        JSON response with updated prompt data
    """
    try:
        prompt_group_data = await request.json()
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in prompt group request: {e}")
        return create_error_response(
            "Invalid JSON format",
            [str(e)],
            status=400
        )

    # Input validation
    is_valid, message, errors = validate_request_json(prompt_group_data)
    if not is_valid:
        return create_error_response(message or "Validation error", errors or [], status=400)
    
    # Validate required fields
    is_valid, message, errors = validate_name_field(prompt_group_data)
    if not is_valid:
        return create_error_response(message or "Validation error", errors or [], status=400)

    name = prompt_group_data["name"].strip()

    # Validate trigger_words if provided
    trigger_words = prompt_group_data.get("trigger_words", [])
    if not isinstance(trigger_words, list):
        return create_error_response(
            "Invalid trigger_words format",
            ["trigger_words must be an array of strings"],
            status=400
        )

    try:
        PROMPT_ADDITIONS.create_or_update_prompt_group(
            PromptGroup(
                name,
                trigger_words,
                prompt_group_data.get("additions", []),
                prompt_group_data.get("id"),
            )
        )
        
        save_prompt_definitions()
        
        return create_success_response(
            "Prompt group saved successfully",
            PROMPT_ADDITIONS.prompt_additions_as_dict()
        )
        
    except ValueError as e:
        logging.error(f"Validation error in prompt group: {e}")
        return create_error_response(
            "Validation error",
            [str(e)],
            status=400
        )
    except Exception as e:
        logging.error(f"Server error in prompt group: {e}")
        return create_error_response(
            "Internal server error",
            ["An unexpected error occurred"],
            status=500
        )


async def delete_prompt_group(request: web.Request) -> web.Response:
    """
    Delete a specific prompt group by ID.
    
    Args:
        request: HTTP request containing prompt_group_id in URL path
        
    Returns:
        JSON response with updated prompt data
    """
    # Initialize group_id to handle scope issues
    group_id = None
    group_id_str = request.match_info.get("prompt_group_id")
    
    if not group_id_str:
        return create_error_response(
            "Group ID is required",
            ["Missing group ID in URL"],
            status=400
        )
    
    # Validate and convert group ID to integer
    try:
        group_id = int(group_id_str)
    except ValueError:
        return create_error_response(
            "Invalid group ID format",
            ["Group ID must be a valid integer"],
            status=400
        )
    
    try:
        PROMPT_ADDITIONS.delete_prompt_group(group_id)
        save_prompt_definitions()
        
        return create_success_response(
            f"Prompt group with ID {group_id} deleted successfully",
            PROMPT_ADDITIONS.prompt_additions_as_dict()
        )
        
    except KeyError:
        return create_error_response(
            f"Prompt group with ID {group_id} not found",
            [f"No prompt group with ID {group_id} exists"],
            status=404
        )
    except Exception as e:
        logging.error(f"Server error deleting prompt group {group_id}: {e}")
        return create_error_response(
            "Failed to delete prompt group",
            ["An unexpected error occurred"],
            status=500
        )