"""
Persistent JSON Storage System for ComfyUI-Prompt-Companion

This module provides comprehensive persistent storage functionality for subprompts,
with atomic file operations, backup/restore capabilities, and thread-safe access.

Key Features:
- Thread-safe JSON file storage for subprompts and collections
- Atomic file operations to prevent data corruption
- Automatic backup creation before major operations
- Import/export capabilities for sharing subprompt collections
- Integration with ComfyUI's folder structure
- Comprehensive error handling and validation
"""

import os
import json
import threading
import shutil
import tempfile
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Import ComfyUI folder management if available
try:
    import folder_paths
    COMFYUI_AVAILABLE = True
except ImportError:
    COMFYUI_AVAILABLE = False
    folder_paths = None

# Import core classes for integration
from .subprompt import Subprompt, SubpromptError, ValidationError
from .folder import Folder, FolderError, FolderValidationError, build_folder_hierarchy, get_root_folders, validate_folder_structure
from .validation import validate_collection_integrity, validate_subprompt_structure

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations"""
    pass


class SubpromptStorage:
    """
    Persistent JSON storage manager for subprompts with thread-safe operations.
    
    Provides comprehensive storage functionality including:
    - CRUD operations for individual subprompts
    - Collection management for entire subprompt sets
    - Atomic file operations to prevent corruption
    - Backup/restore capabilities
    - Import/export for sharing collections
    - Thread-safe concurrent access
    """
    
    STORAGE_VERSION = "1.0"
    DEFAULT_FILENAME = "subprompts.json"
    BACKUP_DIR = "backups"
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize SubpromptStorage with optional custom storage path.
        
        Args:
            storage_path: Custom storage directory path. If None, uses ComfyUI user directory
                         or creates default directory.
        
        Raises:
            StorageError: If storage directory cannot be created or accessed
        """
        self._lock = threading.RLock()
        self._storage_dir = self._resolve_storage_directory(storage_path)
        self._storage_file = os.path.join(self._storage_dir, self.DEFAULT_FILENAME)
        self._backup_dir = os.path.join(self._storage_dir, self.BACKUP_DIR)
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _resolve_storage_directory(self, custom_path: Optional[str] = None) -> str:
        """
        Resolve the storage directory path using ComfyUI user directory structure.
        
        Args:
            custom_path: Custom directory path if provided
            
        Returns:
            Resolved storage directory path
            
        Raises:
            StorageError: If ComfyUI user directory cannot be accessed
        """
        if custom_path:
            return os.path.abspath(custom_path)
        
        # Use ComfyUI user directory structure - must be available
        if not COMFYUI_AVAILABLE or not folder_paths:
            raise StorageError("ComfyUI folder_paths module not available - cannot initialize storage")
        
        try:
            base_user_dir = folder_paths.get_user_directory()
            
            # Determine user-specific directory
            user_specific_dir = self._get_or_create_user_directory(base_user_dir)
            
            # Storage should be in user/{user_name}/prompt_companion
            return os.path.join(user_specific_dir, "prompt_companion")
        except Exception as e:
            raise StorageError(f"Could not access ComfyUI user directory: {e}")
    
    def _get_or_create_user_directory(self, base_user_dir: str) -> str:
        """
        Get or create a user-specific directory within the ComfyUI user directory.
        
        This method implements the following logic:
        1. Check if there are existing user subdirectories
        2. If "default" exists, use it
        3. If other user subdirectories exist but no "default", use the first one
        4. If no user subdirectories exist, create and use "default"
        
        Args:
            base_user_dir: Base user directory from ComfyUI
            
        Returns:
            User-specific directory path
        """
        try:
            # Check if base user directory exists
            if not os.path.exists(base_user_dir):
                os.makedirs(base_user_dir, exist_ok=True)
            
            # Look for existing user subdirectories
            user_subdirs = []
            try:
                for item in os.listdir(base_user_dir):
                    item_path = os.path.join(base_user_dir, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        user_subdirs.append(item)
            except OSError:
                # If we can't list the directory, we'll create default
                pass
            
            # Determine which user directory to use
            if "default" in user_subdirs:
                user_dir = os.path.join(base_user_dir, "default")
            elif user_subdirs:
                # Use the first available user subdirectory (alphabetically sorted for consistency)
                first_user = sorted(user_subdirs)[0]
                user_dir = os.path.join(base_user_dir, first_user)
            else:
                # No user subdirectories exist, create "default"
                user_dir = os.path.join(base_user_dir, "default")
                os.makedirs(user_dir, exist_ok=True)
            
            return user_dir
            
        except Exception as e:
            # Fallback to creating default directory
            default_user_dir = os.path.join(base_user_dir, "default")
            try:
                os.makedirs(default_user_dir, exist_ok=True)
                logger.warning(f"Fallback: created default user directory after error: {e}")
                return default_user_dir
            except Exception as fallback_e:
                raise StorageError(f"Could not create user directory: {e}, fallback also failed: {fallback_e}")
    
    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist"""
        try:
            os.makedirs(self._storage_dir, exist_ok=True)
            os.makedirs(self._backup_dir, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create storage directories: {e}")
    
    def _atomic_write(self, filepath: str, data: Dict[str, Any]) -> None:
        """
        Perform atomic file write using temporary file and move operation.
        
        Args:
            filepath: Target file path
            data: Data to write as JSON
            
        Raises:
            StorageError: If write operation fails
        """
        # Create temporary file in same directory to ensure same filesystem
        temp_dir = os.path.dirname(filepath)
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', 
                encoding='utf-8', 
                dir=temp_dir, 
                delete=False,
                suffix='.tmp'
            ) as temp_file:
                json.dump(data, temp_file, indent=2, ensure_ascii=False)
                temp_path = temp_file.name
            
            # Atomic move operation
            if os.name == 'nt':  # Windows
                # Windows requires removing target file first
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            shutil.move(temp_path, filepath)
            
        except Exception as e:
            # Clean up temporary file if it exists
            if 'temp_path' in locals() and 'temp_path' in locals() and os.path.exists(locals().get('temp_path', '')):
                try:
                    os.remove(locals()['temp_path'])
                except:
                    pass
            raise StorageError(f"Atomic write failed for {filepath}: {e}")
    
    def _create_storage_structure(self, subprompts: List[Subprompt]) -> Dict[str, Any]:
        """
        Create storage data structure with metadata and subprompts.
        
        Args:
            subprompts: List of subprompts to store
            
        Returns:
            Complete storage data structure
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Convert subprompts to dictionary format
        subprompts_data = []
        for subprompt in subprompts:
            try:
                subprompts_data.append(subprompt.to_dict())
            except Exception as e:
                logger.error(f"Failed to serialize subprompt {subprompt.id}: {e}")
                raise StorageError(f"Serialization failed for subprompt {subprompt.id}: {e}")
        
        return {
            "version": self.STORAGE_VERSION,
            "created": now,
            "updated": now,
            "subprompts": subprompts_data,
            "folders": []  # Initialize empty folder list for new storage files
        }
    
    def _create_storage_structure_with_folders(self, subprompts: List[Subprompt], existing_folders: List[str]) -> Dict[str, Any]:
        """
        Create storage data structure with metadata, subprompts, and preserved folders.
        
        Args:
            subprompts: List of subprompts to store
            existing_folders: List of existing folders to preserve
            
        Returns:
            Complete storage data structure
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Convert subprompts to dictionary format
        subprompts_data = []
        for subprompt in subprompts:
            try:
                subprompts_data.append(subprompt.to_dict())
            except Exception as e:
                logger.error(f"Failed to serialize subprompt {subprompt.id}: {e}")
                raise StorageError(f"Serialization failed for subprompt {subprompt.id}: {e}")
        
        # Ensure all folders from subprompts are included in the folder list
        # Handle both legacy string format and new dict format
        all_folders_set = set()
        
        # Add existing folders (handle mixed string/dict format)
        for folder in existing_folders:
            if isinstance(folder, str) and folder.strip():
                # Legacy string format
                all_folders_set.add(folder.strip())
            elif isinstance(folder, dict) and folder.get("name"):
                # Keep dict objects as-is for the final list, but track paths to avoid duplicates
                folder_path = folder.get("path", "")  # Assuming dict has path info
                if folder_path:
                    all_folders_set.add(folder_path)
        
        # Add folder paths from subprompts
        for subprompt in subprompts:
            if subprompt.folder_path and subprompt.folder_path.strip():
                all_folders_set.add(subprompt.folder_path)
        
        # Create final folders list maintaining dict objects where they exist
        final_folders = []
        for folder in existing_folders:
            if isinstance(folder, dict):
                # Keep dict objects as-is
                final_folders.append(folder)
            elif isinstance(folder, str) and folder.strip():
                # Keep string format
                final_folders.append(folder.strip())
        
        # Add any new folder paths from subprompts that weren't already in existing_folders
        existing_paths = set()
        for folder in existing_folders:
            if isinstance(folder, str):
                existing_paths.add(folder.strip())
            elif isinstance(folder, dict):
                folder_path = folder.get("path", "")
                if folder_path:
                    existing_paths.add(folder_path)
        
        for subprompt in subprompts:
            if (subprompt.folder_path and
                subprompt.folder_path.strip() and
                subprompt.folder_path not in existing_paths):
                final_folders.append(subprompt.folder_path)
        
        return {
            "version": self.STORAGE_VERSION,
            "created": now,
            "updated": now,
            "subprompts": subprompts_data,
            "folders": final_folders
        }
    
    def _validate_storage_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and repair loaded storage data structure gracefully.
        
        Args:
            data: Storage data to validate and repair
            
        Returns:
            Repaired storage data dictionary with safe defaults
        """
        if not data or not isinstance(data, dict):
            logger.warning("Storage data is not a valid dictionary, creating default structure")
            return self._create_default_storage_structure()
        
        # Create a safe copy to modify
        safe_data = dict(data)
        
        # Ensure required 'subprompts' field exists
        if "subprompts" not in safe_data or safe_data["subprompts"] is None:
            logger.warning("Storage data missing 'subprompts' field, creating empty default")
            safe_data["subprompts"] = []
        
        # Handle both old dict format and new list format
        if isinstance(safe_data["subprompts"], dict):
            # Will be converted to list format during validation below
            pass
        elif not isinstance(safe_data["subprompts"], list):
            logger.warning("'subprompts' field is not a list or dict, resetting to empty")
            safe_data["subprompts"] = []
        
        # Ensure 'folders' field exists and is valid
        if "folders" not in safe_data:
            logger.info("Storage data missing 'folders' field, creating empty default")
            safe_data["folders"] = []
        elif not isinstance(safe_data["folders"], list):
            logger.warning("'folders' field is not a list, resetting to empty")
            safe_data["folders"] = []
        else:
            # Clean invalid folder entries - support both old string format and new object format
            clean_folders = []
            for folder in safe_data["folders"]:
                try:
                    if isinstance(folder, str) and folder.strip():
                        # Old format: path string
                        clean_folders.append(folder.strip())
                    elif isinstance(folder, dict):
                        # New format: folder object - validate required fields
                        if ("id" in folder and folder["id"] and
                            "name" in folder and folder["name"] and
                            isinstance(folder["name"], str) and folder["name"].strip()):
                            clean_folders.append(folder)
                        else:
                            logger.warning(f"Removing invalid folder entry (missing required fields): {folder}")
                    else:
                        logger.warning(f"Removing invalid folder entry (wrong type): {folder}")
                except Exception as e:
                    logger.warning(f"Removing corrupted folder entry: {folder} - Error: {e}")
                    continue
            safe_data["folders"] = clean_folders
        
        # Validate and repair version if present
        if "version" in safe_data:
            version = safe_data["version"]
            if version != self.STORAGE_VERSION:
                logger.warning(f"Storage version mismatch: {version} != {self.STORAGE_VERSION}")
        else:
            safe_data["version"] = self.STORAGE_VERSION
        
        # Add missing metadata fields
        now = datetime.now(timezone.utc).isoformat()
        if "created" not in safe_data:
            safe_data["created"] = now
        if "updated" not in safe_data:
            safe_data["updated"] = now
        
        # Validate and repair individual subprompts
        clean_subprompts = []
        subprompts_data = safe_data["subprompts"]
        
        # Handle both old dict format and new list format
        if isinstance(subprompts_data, dict):
            # Convert old format to new format
            for subprompt_id, subprompt_data in subprompts_data.items():
                try:
                    if isinstance(subprompt_data, dict):
                        # Ensure it has an ID
                        if "id" not in subprompt_data:
                            subprompt_data["id"] = subprompt_id
                        
                        result = validate_subprompt_structure(subprompt_data)
                        if result.is_valid:
                            clean_subprompts.append(subprompt_data)
                        else:
                            logger.warning(f"Subprompt {subprompt_id} has validation issues: {'; '.join(result.errors)}")
                            # Try to repair the subprompt data
                            repaired_data = self._repair_subprompt_data(subprompt_id, subprompt_data)
                            if repaired_data:
                                clean_subprompts.append(repaired_data)
                            else:
                                logger.error(f"Could not repair subprompt {subprompt_id}, skipping")
                    else:
                        logger.warning(f"Subprompt {subprompt_id} data is not a dictionary, skipping")
                except Exception as e:
                    logger.warning(f"Error validating subprompt {subprompt_id}: {e}, skipping")
                    continue
        elif isinstance(subprompts_data, list):
            # New list format
            for subprompt_data in subprompts_data:
                try:
                    if isinstance(subprompt_data, dict):
                        # Ensure it has an ID
                        if "id" not in subprompt_data:
                            import uuid
                            subprompt_data["id"] = str(uuid.uuid4())
                        
                        result = validate_subprompt_structure(subprompt_data)
                        if result.is_valid:
                            clean_subprompts.append(subprompt_data)
                        else:
                            logger.warning(f"Subprompt {subprompt_data.get('id', 'unknown')} has validation issues: {'; '.join(result.errors)}")
                            # Try to repair the subprompt data
                            repaired_data = self._repair_subprompt_data(subprompt_data.get("id", "unknown"), subprompt_data)
                            if repaired_data:
                                clean_subprompts.append(repaired_data)
                            else:
                                logger.error(f"Could not repair subprompt {subprompt_data.get('id', 'unknown')}, skipping")
                    else:
                        logger.warning(f"Subprompt data is not a dictionary, skipping")
                except Exception as e:
                    logger.warning(f"Error validating subprompt: {e}, skipping")
                    continue
        
        safe_data["subprompts"] = clean_subprompts
        
        return safe_data
    
    def _create_default_storage_structure(self) -> Dict[str, Any]:
        """Create a default storage structure when data is missing or corrupted."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "version": self.STORAGE_VERSION,
            "created": now,
            "updated": now,
            "subprompts": [],
            "folders": []
        }
    
    def _create_default_storage_file(self) -> None:
        """Create a default storage file when one doesn't exist."""
        try:
            default_data = self._create_default_storage_structure()
            self._atomic_write(self._storage_file, default_data)
        except Exception as e:
            logger.error(f"Failed to create default storage file: {e}")
            # Don't raise here - let the system continue with empty data
    
    def _repair_subprompt_data(self, subprompt_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Attempt to repair corrupted subprompt data.
        
        Args:
            subprompt_id: The ID of the subprompt
            data: The corrupted data dictionary
            
        Returns:
            Repaired data dictionary or None if unrepairable
        """
        try:
            import uuid
            
            # Start with safe defaults
            repaired = {
                "id": subprompt_id if subprompt_id else str(uuid.uuid4()),
                "name": data.get("name", "repaired_subprompt"),
                "positive": "",
                "negative": "",
                "trigger_words": [],
                "order": ["attached"],
                "folder_path": ""
            }
            
            # Try to salvage valid fields
            if isinstance(data.get("positive"), str):
                repaired["positive"] = data["positive"]
            if isinstance(data.get("negative"), str):
                repaired["negative"] = data["negative"]
            if isinstance(data.get("folder_path"), str):
                repaired["folder_path"] = data["folder_path"]
            
            # Handle trigger_words
            if isinstance(data.get("trigger_words"), list):
                clean_words = []
                for word in data["trigger_words"]:
                    if isinstance(word, str) and word.strip():
                        clean_words.append(word.strip())
                repaired["trigger_words"] = clean_words
            
            # Handle order field
            if isinstance(data.get("order"), list) and data["order"]:
                clean_order = []
                for item in data["order"]:
                    if isinstance(item, str) and item.strip():
                        clean_order.append(item.strip())
                if clean_order:
                    repaired["order"] = clean_order
            
            # Handle legacy nested_subprompts field
            if isinstance(data.get("nested_subprompts"), list):
                try:
                    converted_order = []
                    for item in data["nested_subprompts"]:
                        if item == "[Self]":
                            converted_order.append("attached")
                        elif isinstance(item, str) and item.strip():
                            converted_order.append(item.strip())
                    if converted_order:
                        repaired["order"] = converted_order
                except Exception:
                    pass  # Keep default order
            
            return repaired
            
        except Exception as e:
            logger.error(f"Failed to repair subprompt {subprompt_id}: {e}")
            return None
    
    def _cleanup_corrupted_composite_keys(self, subprompts_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect and clean up corrupted composite keys that contain duplicated folder paths.
        
        Args:
            subprompts_data: Dictionary of subprompt data with potentially corrupted keys
            
        Returns:
            Cleaned subprompts data with repaired composite keys
        """
        cleaned_data = {}
        repaired_count = 0
        
        for composite_key, subprompt_data in subprompts_data.items():
            try:
                # Check if composite key has duplicated path segments
                if "/" in composite_key:
                    path_parts = composite_key.split("/")
                    
                    # Detect patterns like "folder/subfolder/folder/subfolder/name"
                    # where the path is duplicated
                    if len(path_parts) > 2:
                        # Check if the first half matches the second half (minus the name)
                        mid_point = len(path_parts) // 2
                        first_half = path_parts[:mid_point]
                        second_half = path_parts[mid_point:-1]  # Exclude the name part
                        
                        # If we found a duplication pattern
                        if len(first_half) == len(second_half) and first_half == second_half:
                            # Reconstruct with just the first half and the name
                            name_part = path_parts[-1]
                            clean_composite_key = "/".join(first_half + [name_part])
                            
                            # Update the subprompt data's folder_path to match
                            clean_folder_path = "/".join(first_half) if first_half else ""
                            subprompt_data["folder_path"] = clean_folder_path
                            
                            cleaned_data[clean_composite_key] = subprompt_data
                            repaired_count += 1
                            logger.info(f"Repaired corrupted composite key: '{composite_key}' -> '{clean_composite_key}'")
                            continue
                        
                        # Also check for more complex duplications where middle parts repeat
                        # Look for any repeating sequence in the path
                        found_repetition = False
                        for seq_len in range(1, len(path_parts) // 2):
                            for start in range(len(path_parts) - seq_len * 2):
                                sequence = path_parts[start:start + seq_len]
                                next_sequence = path_parts[start + seq_len:start + seq_len * 2]
                                
                                if sequence == next_sequence:
                                    # Found a repetition, remove it
                                    # Keep everything before the repetition, skip the duplicate, keep the rest
                                    clean_parts = (path_parts[:start + seq_len] +
                                                 path_parts[start + seq_len * 2:])
                                    clean_composite_key = "/".join(clean_parts)
                                    
                                    # Update folder path (everything except the name)
                                    clean_folder_path = "/".join(clean_parts[:-1]) if len(clean_parts) > 1 else ""
                                    subprompt_data["folder_path"] = clean_folder_path
                                    
                                    cleaned_data[clean_composite_key] = subprompt_data
                                    repaired_count += 1
                                    logger.info(f"Repaired corrupted composite key with sequence repetition: '{composite_key}' -> '{clean_composite_key}'")
                                    found_repetition = True
                                    break
                            if found_repetition:
                                break
                        
                        if not found_repetition:
                            # No corruption detected, keep as is
                            cleaned_data[composite_key] = subprompt_data
                    else:
                        # Simple path, no corruption possible
                        cleaned_data[composite_key] = subprompt_data
                else:
                    # No folder path, no corruption possible
                    cleaned_data[composite_key] = subprompt_data
                    
            except Exception as e:
                logger.warning(f"Error cleaning composite key {composite_key}: {e}")
                # Keep original on error
                cleaned_data[composite_key] = subprompt_data
        
        if repaired_count > 0:
            logger.info(f"Composite key cleanup completed: repaired {repaired_count} corrupted keys")
        
        return cleaned_data
    
    def _clean_duplicated_folder_path(self, folder_path: str) -> str:
        """
        Clean up duplicated folder path segments in folder_path field.
        
        Args:
            folder_path: The folder path to clean
            
        Returns:
            Cleaned folder path with duplicate segments removed
        """
        if not folder_path or not folder_path.strip():
            return folder_path
        
        parts = folder_path.split("/")
        if len(parts) <= 2:
            return folder_path  # No duplication possible
        
        # Check for pattern like "folder/subfolder/folder/subfolder"
        mid_point = len(parts) // 2
        first_half = parts[:mid_point]
        second_half = parts[mid_point:]
        
        # If first half matches second half, it's duplicated
        if first_half == second_half:
            return "/".join(first_half)
        
        # Check for other repetition patterns
        for seq_len in range(1, len(parts) // 2):
            for start in range(len(parts) - seq_len * 2 + 1):
                sequence = parts[start:start + seq_len]
                next_sequence = parts[start + seq_len:start + seq_len * 2]
                
                if sequence == next_sequence:
                    # Found repetition, remove it
                    clean_parts = parts[:start + seq_len] + parts[start + seq_len * 2:]
                    return "/".join(clean_parts)
        
        return folder_path  # No duplication found
    
    def load_all_subprompts(self) -> List[Subprompt]:
        """
        Load all subprompts from storage file.
        
        Returns:
            List of Subprompt instances
            
        Raises:
            StorageError: If loading or validation fails
        """
        with self._lock:
            if not os.path.exists(self._storage_file):
                self._create_default_storage_file()
                return []
            
            try:
                with open(self._storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate and repair loaded data
                data = self._validate_storage_data(data)
                
                # Convert to Subprompt instances
                subprompts = []
                for subprompt_data in data["subprompts"]:
                    try:
                        subprompt = Subprompt.from_dict(subprompt_data)
                        subprompts.append(subprompt)
                    except Exception as e:
                        logger.error(f"Failed to deserialize subprompt {subprompt_data.get('id', 'unknown')}: {e}")
                        # Don't raise here - continue with other subprompts
                        logger.warning(f"Skipping corrupted subprompt {subprompt_data.get('id', 'unknown')}")
                        continue
                
                return subprompts
                
            except json.JSONDecodeError as e:
                raise StorageError(f"Invalid JSON in storage file: {e}")
            except Exception as e:
                raise StorageError(f"Failed to load subprompts: {e}")
    
    def load_all_folders(self) -> List[Folder]:
        """
        Load all folders from storage file as Folder objects.
        
        Returns:
            List of Folder instances
            
        Raises:
            StorageError: If loading fails
        """
        with self._lock:
            if not os.path.exists(self._storage_file):
                self._create_default_storage_file()
                return []
            
            try:
                with open(self._storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate and repair loaded data
                data = self._validate_storage_data(data)
                
                # Get folders from storage
                folders_data = data.get("folders", [])
                folders = []
                
                # Handle both old string format and new object format
                for folder_item in folders_data:
                    try:
                        if isinstance(folder_item, str):
                            # Old format: path string, convert to Folder object
                            folder = Folder.from_path(folder_item)
                            folders.append(folder)
                        elif isinstance(folder_item, dict):
                            # New format: folder object
                            folder = Folder.from_dict(folder_item)
                            folders.append(folder)
                        else:
                            logger.warning(f"Invalid folder data: {folder_item}")
                    except Exception as e:
                        logger.error(f"Failed to load folder {folder_item}: {e}")
                        continue
                
                # For backward compatibility, also create folders from subprompt folder_paths
                subprompt_folder_paths = set()
                for subprompt_data in data["subprompts"]:
                    folder_path = subprompt_data.get("folder_path")
                    if folder_path and folder_path.strip():
                        subprompt_folder_paths.add(folder_path)
                
                # Create folder objects for paths not already represented
                existing_paths = set()
                folder_lookup = build_folder_hierarchy(folders)
                for folder in folders:
                    path = folder.get_path(folder_lookup)
                    existing_paths.add(path)
                
                for path in subprompt_folder_paths:
                    if path not in existing_paths:
                        try:
                            folder = Folder.from_path(path, folder_lookup)
                            folders.append(folder)
                        except Exception as e:
                            logger.warning(f"Failed to create folder from path {path}: {e}")
                
                return folders
                
            except json.JSONDecodeError as e:
                raise StorageError(f"Invalid JSON in storage file: {e}")
            except Exception as e:
                raise StorageError(f"Failed to load folders: {e}")
    
    def _load_storage_data(self) -> Dict[str, Any]:
        """
        Load complete storage data structure.
        
        Returns:
            Complete storage data dictionary
            
        Raises:
            StorageError: If loading fails
        """
        if not os.path.exists(self._storage_file):
            return {
                "version": self.STORAGE_VERSION,
                "created": datetime.now(timezone.utc).isoformat(),
                "updated": datetime.now(timezone.utc).isoformat(),
                "subprompts": [],
                "folders": []
            }
        
        try:
            with open(self._storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate and repair loaded data
            data = self._validate_storage_data(data)
            
            # Ensure folders field exists for backward compatibility
            if "folders" not in data:
                data["folders"] = []
                
                # Migrate folders from subprompts for backward compatibility
                subprompt_folders = set()
                if isinstance(data["subprompts"], dict):
                    # Old format - convert to list
                    for subprompt_data in data["subprompts"].values():
                        folder_path = subprompt_data.get("folder_path")
                        if folder_path and folder_path.strip():
                            subprompt_folders.add(folder_path)
                else:
                    # New list format
                    for subprompt_data in data["subprompts"]:
                        folder_path = subprompt_data.get("folder_path")
                        if folder_path and folder_path.strip():
                            subprompt_folders.add(folder_path)
                
                data["folders"] = sorted(subprompt_folders)
                logger.info(f"Migrated {len(data['folders'])} folders from subprompts")
            
            return data
            
        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON in storage file: {e}")
        except Exception as e:
            raise StorageError(f"Failed to load storage data: {e}")
    
    def save_all_subprompts(self, subprompts: List[Subprompt]) -> bool:
        """
        Save entire subprompt collection to storage with validation and backup.
        
        Args:
            subprompts: List of subprompts to save
            
        Returns:
            True if save operation was successful
            
        Raises:
            StorageError: If save operation fails
        """
        with self._lock:
            # Create backup before major operation
            backup_path = None
            if os.path.exists(self._storage_file):
                try:
                    backup_path = self.backup_storage()
                    logger.info(f"Created backup before save: {backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            try:
                # Load current storage data to preserve folders
                current_data = self._load_storage_data()
                
                # Create storage structure with preserved folders
                storage_data = self._create_storage_structure_with_folders(subprompts, current_data.get("folders", []))
                
                # Atomic write operation
                self._atomic_write(self._storage_file, storage_data)
                
                # Invalidate dynamic combo box cache after successful save
                _invalidate_combo_cache()
                
                return True
                
            except Exception as e:
                # Attempt to restore from backup on failure
                if backup_path and os.path.exists(backup_path):
                    try:
                        shutil.copy2(backup_path, self._storage_file)
                        logger.info(f"Restored from backup after save failure")
                    except Exception as restore_e:
                        logger.error(f"Failed to restore from backup: {restore_e}")
                
                raise StorageError(f"Failed to save subprompts: {e}")
    
    def load_subprompt(self, subprompt_id: str) -> Optional[Subprompt]:
        """
        Load a specific subprompt by UUID.
        
        Args:
            subprompt_id: UUID of subprompt to load
            
        Returns:
            Subprompt instance or None if not found
            
        Raises:
            StorageError: If loading fails
        """
        all_subprompts = self.load_all_subprompts()
        for subprompt in all_subprompts:
            if subprompt.id == subprompt_id:
                return subprompt
        return None
    
    def save_subprompt(self, subprompt: Subprompt) -> bool:
        """
        Save or update a single subprompt using UUID for uniqueness.
        
        Args:
            subprompt: Subprompt instance to save
            
        Returns:
            True if save operation was successful
            
        Raises:
            StorageError: If save operation fails
        """
        with self._lock:
            # Ensure folder exists if subprompt has one
            if subprompt.folder_path and subprompt.folder_path.strip():
                self.ensure_folder_exists(subprompt.folder_path)
            
            # Load existing subprompts
            try:
                all_subprompts = self.load_all_subprompts()
            except StorageError:
                # If loading fails, start with empty collection
                all_subprompts = []
            
            # Check if this subprompt already exists (by UUID) and update it
            found_index = -1
            for i, existing_subprompt in enumerate(all_subprompts):
                if existing_subprompt.id == subprompt.id:
                    found_index = i
                    break
            
            if found_index >= 0:
                # Update existing subprompt
                all_subprompts[found_index] = subprompt
            else:
                # Add new subprompt
                all_subprompts.append(subprompt)
            
            # Save entire collection and invalidate combo cache
            result = self.save_all_subprompts(all_subprompts)
            if result:
                _invalidate_combo_cache()
            return result
    
    def cleanup_subprompt_references(self, deleted_subprompt_id: str, deleted_subprompt_name: Optional[str] = None) -> int:
        """
        Remove references to a deleted subprompt from all other subprompts' order arrays.
        
        This function implements cascade deletion to maintain data integrity by cleaning up
        orphaned references when a subprompt is deleted.
        
        Args:
            deleted_subprompt_id: UUID of the deleted subprompt
            deleted_subprompt_name: Name of the deleted subprompt (for legacy references)
            
        Returns:
            Number of subprompts that were updated (had references cleaned up)
            
        Raises:
            StorageError: If cleanup operation fails
        """
        try:
            # Load all existing subprompts
            all_subprompts = self.load_all_subprompts()
            updated_subprompts = []
            cleanup_count = 0
            
            for subprompt in all_subprompts:
                # Skip the deleted subprompt itself (shouldn't be in the list anyway)
                if subprompt.id == deleted_subprompt_id:
                    continue
                    
                original_order = subprompt.order.copy()
                cleaned_order = []
                references_removed = False
                
                # Clean up the order array
                for item in subprompt.order:
                    # Keep "attached" references
                    if item == "attached":
                        cleaned_order.append(item)
                    # Remove references to deleted subprompt by ID
                    elif item == deleted_subprompt_id:
                        references_removed = True
                        logger.info(f"Removed reference to deleted subprompt ID '{deleted_subprompt_id}' from subprompt '{subprompt.name}'")
                    # Remove references to deleted subprompt by name (legacy support)
                    elif deleted_subprompt_name and item == deleted_subprompt_name:
                        references_removed = True
                        logger.info(f"Removed reference to deleted subprompt name '{deleted_subprompt_name}' from subprompt '{subprompt.name}'")
                    else:
                        # Keep other references
                        cleaned_order.append(item)
                
                # If we removed references, update the subprompt
                if references_removed:
                    # Ensure we have at least "attached" if order becomes empty
                    if not cleaned_order:
                        cleaned_order = ["attached"]
                        logger.warning(f"Order array became empty for subprompt '{subprompt.name}', added 'attached' as fallback")
                    
                    subprompt.order = cleaned_order
                    updated_subprompts.append(subprompt)
                    cleanup_count += 1
                else:
                    updated_subprompts.append(subprompt)
                    
                # Also check and clean up legacy nested_subprompts metadata if present
                if hasattr(subprompt, 'metadata') and subprompt.metadata:
                    nested_subprompts = subprompt.metadata.get('nested_subprompts')
                    if nested_subprompts and isinstance(nested_subprompts, list):
                        original_nested = nested_subprompts.copy()
                        cleaned_nested = []
                        nested_references_removed = False
                        
                        for item in nested_subprompts:
                            # Keep "[Self]" references
                            if item == "[Self]":
                                cleaned_nested.append(item)
                            # Remove references to deleted subprompt by ID
                            elif item == deleted_subprompt_id:
                                nested_references_removed = True
                                logger.info(f"Removed nested reference to deleted subprompt ID '{deleted_subprompt_id}' from subprompt '{subprompt.name}'")
                            # Remove references to deleted subprompt by name (legacy support)
                            elif deleted_subprompt_name and item == deleted_subprompt_name:
                                nested_references_removed = True
                                logger.info(f"Removed nested reference to deleted subprompt name '{deleted_subprompt_name}' from subprompt '{subprompt.name}'")
                            else:
                                # Keep other references
                                cleaned_nested.append(item)
                        
                        if nested_references_removed:
                            # Ensure we have at least "[Self]" if nested_subprompts becomes empty
                            if not cleaned_nested:
                                cleaned_nested = ["[Self]"]
                                logger.warning(f"nested_subprompts array became empty for subprompt '{subprompt.name}', added '[Self]' as fallback")
                            
                            subprompt.metadata['nested_subprompts'] = cleaned_nested
                            # If this subprompt wasn't already marked for update, mark it now
                            if subprompt not in updated_subprompts:
                                updated_subprompts.append(subprompt)
                                cleanup_count += 1
            
            # Save all subprompts if any were updated
            if cleanup_count > 0:
                success = self.save_all_subprompts(updated_subprompts)
                if not success:
                    raise StorageError("Failed to save subprompts after reference cleanup")
                    
                logger.info(f"Cascade deletion cleanup completed: updated {cleanup_count} subprompts")
            
            return cleanup_count
            
        except Exception as e:
            raise StorageError(f"Failed to cleanup subprompt references: {e}")
    
    def delete_subprompt(self, subprompt_id: str) -> bool:
        """
        Delete a subprompt by UUID with cascade cleanup of references.
        
        This method implements cascade deletion by:
        1. Finding and removing the target subprompt
        2. Cleaning up all references to it from other subprompts' order arrays
        3. Ensuring atomic operation with proper error handling
        
        Args:
            subprompt_id: UUID of subprompt to delete
            
        Returns:
            True if deletion was successful, False if subprompt not found
            
        Raises:
            StorageError: If delete operation fails
        """
        with self._lock:
            # Load existing subprompts
            all_subprompts = self.load_all_subprompts()
            
            # Find subprompt by UUID
            found_index = -1
            deleted_subprompt = None
            for i, subprompt in enumerate(all_subprompts):
                if subprompt.id == subprompt_id:
                    found_index = i
                    deleted_subprompt = all_subprompts[i]
                    break
            
            if found_index == -1:
                return False
            
            # Store subprompt name for reference cleanup (we know it's not None here)
            deleted_subprompt_name = deleted_subprompt.name if deleted_subprompt else ""
            
            # Create backup before deletion
            backup_path = None
            try:
                backup_path = self.backup_storage()
                logger.info(f"Created backup before cascade deletion: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create backup before deletion: {e}")
            
            try:
                # Remove subprompt from list
                all_subprompts.pop(found_index)
                
                # Perform cascade cleanup of references in remaining subprompts
                cleanup_count = 0
                for subprompt in all_subprompts:
                    original_order = subprompt.order.copy()
                    cleaned_order = []
                    references_removed = False
                    
                    # Clean up the order array
                    for item in subprompt.order:
                        # Keep "attached" references
                        if item == "attached":
                            cleaned_order.append(item)
                        # Remove references to deleted subprompt by ID or name
                        elif item == subprompt_id or item == deleted_subprompt_name:
                            references_removed = True
                            logger.info(f"Removed reference '{item}' from subprompt '{subprompt.name}'")
                        else:
                            # Keep other references
                            cleaned_order.append(item)
                    
                    # If we removed references, update the subprompt
                    if references_removed:
                        # Ensure we have at least "attached" if order becomes empty
                        if not cleaned_order:
                            cleaned_order = ["attached"]
                            logger.warning(f"Order array became empty for subprompt '{subprompt.name}', added 'attached' as fallback")
                        
                        subprompt.order = cleaned_order
                        cleanup_count += 1
                        
                    # Also clean up legacy nested_subprompts metadata if present
                    if hasattr(subprompt, 'metadata') and subprompt.metadata:
                        nested_subprompts = subprompt.metadata.get('nested_subprompts')
                        if nested_subprompts and isinstance(nested_subprompts, list):
                            cleaned_nested = []
                            nested_references_removed = False
                            
                            for item in nested_subprompts:
                                # Keep "[Self]" references
                                if item == "[Self]":
                                    cleaned_nested.append(item)
                                # Remove references to deleted subprompt by ID or name
                                elif item == subprompt_id or item == deleted_subprompt_name:
                                    nested_references_removed = True
                                    logger.info(f"Removed nested reference '{item}' from subprompt '{subprompt.name}'")
                                else:
                                    # Keep other references
                                    cleaned_nested.append(item)
                            
                            if nested_references_removed:
                                # Ensure we have at least "[Self]" if nested_subprompts becomes empty
                                if not cleaned_nested:
                                    cleaned_nested = ["[Self]"]
                                    logger.warning(f"nested_subprompts became empty for subprompt '{subprompt.name}', added '[Self]' as fallback")
                                
                                subprompt.metadata['nested_subprompts'] = cleaned_nested
                
                # Save updated collection and invalidate combo cache
                success = self.save_all_subprompts(all_subprompts)
                if not success:
                    raise StorageError("Failed to save subprompts after cascade deletion")
                
                _invalidate_combo_cache()
                
                if cleanup_count > 0:
                    logger.info(f"Cascade deletion completed: deleted subprompt '{deleted_subprompt_name}' and cleaned up references in {cleanup_count} other subprompts")
                else:
                    logger.info(f"Deleted subprompt '{deleted_subprompt_name}' (no references to clean up)")
                
                return True
                
            except Exception as e:
                # Attempt to restore from backup on failure
                if backup_path and os.path.exists(backup_path):
                    try:
                        shutil.copy2(backup_path, self._storage_file)
                        logger.info(f"Restored from backup after cascade deletion failure")
                    except Exception as restore_e:
                        logger.error(f"Failed to restore from backup: {restore_e}")
                
                raise StorageError(f"Cascade deletion failed for subprompt {subprompt_id}: {e}")
    
    def list_subprompt_ids(self) -> List[str]:
        """
        Get list of all subprompt UUIDs in storage.
        
        Returns:
            List of subprompt UUID strings
        """
        all_subprompts = self.load_all_subprompts()
        return [subprompt.id for subprompt in all_subprompts]
    
    def export_subprompts(self, export_path: str, subprompt_ids: Optional[List[str]] = None) -> bool:
        """
        Export subprompts to external JSON file for sharing.
        
        Args:
            export_path: Path to export file
            subprompt_ids: List of specific subprompt UUIDs to export. If None, exports all.
            
        Returns:
            True if export was successful
            
        Raises:
            StorageError: If export operation fails
        """
        try:
            # Load all subprompts
            all_subprompts = self.load_all_subprompts()
            
            # Filter if specific IDs requested
            if subprompt_ids is not None:
                export_subprompts = []
                missing_ids = []
                for subprompt_id in subprompt_ids:
                    found = False
                    for subprompt in all_subprompts:
                        if subprompt.id == subprompt_id:
                            export_subprompts.append(subprompt)
                            found = True
                            break
                    if not found:
                        missing_ids.append(subprompt_id)
                
                if missing_ids:
                    logger.warning(f"Missing subprompts for export: {missing_ids}")
            else:
                export_subprompts = all_subprompts
            
            # Create export data structure
            export_data = self._create_storage_structure(export_subprompts)
            export_data["exported"] = datetime.now(timezone.utc).isoformat()
            export_data["source"] = "ComfyUI-Prompt-Companion"
            
            # Ensure export directory exists
            export_dir = os.path.dirname(os.path.abspath(export_path))
            os.makedirs(export_dir, exist_ok=True)
            
            # Atomic write to export location
            self._atomic_write(export_path, export_data)
            
            logger.info(f"Exported {len(export_subprompts)} subprompts to: {export_path}")
            return True
            
        except Exception as e:
            raise StorageError(f"Export failed: {e}")
    
    def import_subprompts(self, import_path: str, merge: bool = True) -> Dict[str, str]:
        """
        Import subprompts from external JSON file.
        
        Args:
            import_path: Path to import file
            merge: If True, merge with existing. If False, replace existing.
            
        Returns:
            Dictionary mapping imported UUIDs to status messages
            
        Raises:
            StorageError: If import operation fails
        """
        with self._lock:
            try:
                # Load import file
                with open(import_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                
                # Validate and repair import data
                import_data = self._validate_storage_data(import_data)
                
                # Load existing subprompts if merging
                if merge:
                    existing_subprompts = self.load_all_subprompts()
                else:
                    existing_subprompts = []
                
                # Process imported subprompts
                import_results = {}
                imported_subprompts = []
                
                for subprompt_data in import_data["subprompts"]:
                    try:
                        # Create Subprompt instance
                        subprompt = Subprompt.from_dict(subprompt_data)
                        
                        # Check for conflicts by UUID
                        existing_found = False
                        if merge:
                            for i, existing_subprompt in enumerate(existing_subprompts):
                                if existing_subprompt.id == subprompt.id:
                                    existing_subprompts[i] = subprompt  # Update existing
                                    import_results[subprompt.id] = "updated"
                                    existing_found = True
                                    break
                        
                        if not existing_found:
                            imported_subprompts.append(subprompt)
                            import_results[subprompt.id] = "imported"
                        
                    except Exception as e:
                        import_results[subprompt_data.get("id", "unknown")] = f"failed: {e}"
                        logger.error(f"Failed to import subprompt {subprompt_data.get('id', 'unknown')}: {e}")
                
                # Merge collections
                final_subprompts = existing_subprompts if merge else []
                final_subprompts.extend(imported_subprompts)
                
                # Save merged collection
                self.save_all_subprompts(final_subprompts)
                
                successful_imports = sum(1 for status in import_results.values()
                                      if not status.startswith("failed"))
                logger.info(f"Import completed: {successful_imports}/{len(import_results)} successful")
                
                return import_results
                
            except Exception as e:
                raise StorageError(f"Import failed: {e}")
    
    def backup_storage(self) -> str:
        """
        Create timestamped backup of current storage file.
        
        Returns:
            Path to created backup file
            
        Raises:
            StorageError: If backup creation fails
        """
        if not os.path.exists(self._storage_file):
            raise StorageError("No storage file exists to backup")
        
        try:
            # Create timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"subprompts_backup_{timestamp}.json"
            backup_path = os.path.join(self._backup_dir, backup_filename)
            
            # Copy storage file to backup location
            shutil.copy2(self._storage_file, backup_path)
            
            logger.info(f"Created storage backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            raise StorageError(f"Backup creation failed: {e}")
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """
        Restore storage from backup file.
        
        Args:
            backup_path: Path to backup file to restore from
            
        Returns:
            True if restore was successful
            
        Raises:
            StorageError: If restore operation fails
        """
        with self._lock:
            if not os.path.exists(backup_path):
                raise StorageError(f"Backup file does not exist: {backup_path}")
            
            try:
                # Validate backup file before restore
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                # Validate and repair backup data
                backup_data = self._validate_storage_data(backup_data)
                
                # Create backup of current state before restore
                current_backup = None
                if os.path.exists(self._storage_file):
                    try:
                        current_backup = self.backup_storage()
                    except Exception as e:
                        logger.warning(f"Failed to backup current state: {e}")
                
                # Copy backup file to storage location
                shutil.copy2(backup_path, self._storage_file)
                
                logger.info(f"Restored storage from backup: {backup_path}")
                if current_backup:
                    logger.info(f"Previous state backed up to: {current_backup}")
                
                return True
                
            except Exception as e:
                raise StorageError(f"Restore failed: {e}")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about storage system status and statistics.
        
        Returns:
            Dictionary containing storage information
        """
        info = {
            "storage_directory": self._storage_dir,
            "storage_file": self._storage_file,
            "backup_directory": self._backup_dir,
            "version": self.STORAGE_VERSION,
            "file_exists": os.path.exists(self._storage_file)
        }
        
        if info["file_exists"]:
            try:
                stat = os.stat(self._storage_file)
                info["file_size"] = stat.st_size
                info["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                
                # Load to get counts
                subprompts = self.load_all_subprompts()
                info["subprompt_count"] = len(subprompts)
                
                # Folder organization stats
                folders = set()
                for subprompt in subprompts:
                    if subprompt.folder_path:
                        folders.add(subprompt.folder_path)
                info["folder_count"] = len(folders)
                
            except Exception as e:
                info["error"] = f"Failed to get file info: {e}"
        
        # Backup information
        backup_files = []
        if os.path.exists(self._backup_dir):
            try:
                for filename in os.listdir(self._backup_dir):
                    if filename.endswith('.json'):
                        backup_path = os.path.join(self._backup_dir, filename)
                        stat = os.stat(backup_path)
                        backup_files.append({
                            "filename": filename,
                            "path": backup_path,
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
            except Exception as e:
                logger.warning(f"Failed to get backup info: {e}")
        
        info["backups"] = sorted(backup_files, key=lambda x: x["created"], reverse=True)
        
        return info
    
    def save_folder(self, folder: Union[Folder, str]) -> bool:
        """
        Save a folder to storage (supports both Folder objects and legacy path strings).
        
        Args:
            folder: Folder object or legacy path string to save
            
        Returns:
            True if save operation was successful
            
        Raises:
            StorageError: If save operation fails
        """
        # Handle legacy string input
        if isinstance(folder, str):
            folder_path = folder.strip()
            if not folder_path:
                raise StorageError("Folder path cannot be empty")
            folder = Folder.from_path(folder_path)
        
        if not isinstance(folder, Folder):
            raise StorageError("Invalid folder input: must be Folder object or string")
        
        with self._lock:
            try:
                # Load current folders
                existing_folders = self.load_all_folders()
                folder_lookup = build_folder_hierarchy(existing_folders)
                
                # Check if folder already exists (by UUID)
                if folder.id not in folder_lookup:
                    # Add new folder
                    existing_folders.append(folder)
                else:
                    # Update existing folder
                    for i, existing_folder in enumerate(existing_folders):
                        if existing_folder.id == folder.id:
                            existing_folders[i] = folder
                            break
                
                # Save all folders
                return self._save_all_folders(existing_folders)
                
            except Exception as e:
                raise StorageError(f"Failed to save folder: {e}")
    
    def delete_folder(self, folder_id: str) -> bool:
        """
        Delete a folder from storage by UUID.
        
        Args:
            folder_id: UUID of the folder to delete
            
        Returns:
            True if deletion was successful, False if folder not found
            
        Raises:
            StorageError: If delete operation fails
        """
        # Validate folder_id first
        if not folder_id or folder_id in ('None', 'null', 'undefined'):
            logger.warning(f"Invalid folder_id provided to delete_folder: {folder_id}")
            raise StorageError("Invalid folder ID: cannot delete folder with null/undefined ID")
            
        with self._lock:
            try:
                # Load current folders
                existing_folders = self.load_all_folders()
                
                # Find folder to delete
                folder_to_delete = None
                remaining_folders = []
                
                for folder in existing_folders:
                    try:
                        if hasattr(folder, 'id') and folder.id == folder_id:
                            folder_to_delete = folder
                        else:
                            remaining_folders.append(folder)
                    except (AttributeError, KeyError) as e:
                        logger.warning(f"Skipping malformed folder object during deletion: {folder} - {e}")
                        # Skip malformed folders but don't add them to remaining
                        continue
                
                if not folder_to_delete:
                    return False  # Folder not found
                
                # Save remaining folders
                success = self._save_all_folders(remaining_folders)
                
                if success:
                    try:
                        folder_name = getattr(folder_to_delete, 'name', 'unknown')
                    except (AttributeError, KeyError):
                        pass
                
                return success
                    
            except Exception as e:
                logger.error(f"Exception in delete_folder for ID {folder_id}: {e}")
                raise StorageError(f"Failed to delete folder {folder_id}: {e}")
    
    def update_folder(self, folder: Folder) -> bool:
        """
        Update an existing folder in storage.
        
        Args:
            folder: Updated folder object
            
        Returns:
            True if update was successful, False if folder not found
            
        Raises:
            StorageError: If update operation fails
        """
        with self._lock:
            try:
                # Load current folders
                existing_folders = self.load_all_folders()
                
                # Find and update folder
                folder_found = False
                for i, existing_folder in enumerate(existing_folders):
                    if existing_folder.id == folder.id:
                        existing_folders[i] = folder
                        folder_found = True
                        break
                
                if not folder_found:
                    return False
                
                # Update timestamp
                folder.update_timestamp()
                
                # Save all folders
                success = self._save_all_folders(existing_folders)
                
                if success:
                    pass
                
                return success
                
            except Exception as e:
                raise StorageError(f"Failed to update folder: {e}")
    
    def ensure_folder_exists(self, folder_identifier: Union[str, Folder]) -> bool:
        """
        Ensure a folder exists in storage, creating it if necessary.
        
        Args:
            folder_identifier: Folder object, folder UUID, or legacy path string
            
        Returns:
            True if folder now exists
        """
        if isinstance(folder_identifier, Folder):
            # Check if folder exists by UUID
            existing_folders = self.load_all_folders()
            folder_lookup = build_folder_hierarchy(existing_folders)
            
            if folder_identifier.id not in folder_lookup:
                return self.save_folder(folder_identifier)
            return True
            
        elif isinstance(folder_identifier, str):
            if not folder_identifier.strip():
                return False
            
            # Check if it's a UUID or a path
            try:
                uuid.UUID(folder_identifier)
                # It's a UUID, check if it exists
                existing_folders = self.load_all_folders()
                folder_lookup = build_folder_hierarchy(existing_folders)
                return folder_identifier in folder_lookup
            except ValueError:
                # It's a legacy path, create folder if needed
                existing_folders = self.load_all_folders()
                folder_lookup = build_folder_hierarchy(existing_folders)
                
                for folder in existing_folders:
                    if folder.get_path(folder_lookup) == folder_identifier:
                        return True  # Already exists
                
                # Create new folder from path
                folder = Folder.from_path(folder_identifier, folder_lookup)
                return self.save_folder(folder)
        
        return False
    
    def _save_all_folders(self, folders: List[Folder]) -> bool:
        """
        Save all folders to storage with current subprompts.
        
        Args:
            folders: List of folder objects to save
            
        Returns:
            True if save operation was successful
        """
        try:
            # Load current storage data
            data = self._load_storage_data()
            
            # Convert folders to storage format
            folders_data = []
            for folder in folders:
                folders_data.append(folder.to_dict())
            
            # Update storage data
            data["folders"] = folders_data
            data["updated"] = datetime.now(timezone.utc).isoformat()
            
            # Atomic write operation
            self._atomic_write(self._storage_file, data)
            
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to save folders: {e}")
    
    def load_folder_by_id(self, folder_id: str) -> Optional[Folder]:
        """
        Load a specific folder by UUID.
        
        Args:
            folder_id: UUID of folder to load
            
        Returns:
            Folder instance or None if not found
        """
        # Validate folder_id
        if not folder_id or folder_id in ('None', 'null', 'undefined'):
            logger.warning(f"Invalid folder_id provided to load_folder_by_id: {folder_id}")
            return None
            
        try:
            folders = self.load_all_folders()
            for folder in folders:
                try:
                    if hasattr(folder, 'id') and folder.id == folder_id:
                        return folder
                except (AttributeError, KeyError) as e:
                    logger.warning(f"Malformed folder object encountered: {folder} - {e}")
                    continue
            return None
        except Exception as e:
            logger.error(f"Error in load_folder_by_id for ID {folder_id}: {e}")
            return None
    
    def get_folder_by_path(self, path: str) -> Optional[Folder]:
        """
        Get folder by legacy path string.
        
        Args:
            path: Folder path string
            
        Returns:
            Folder instance or None if not found
        """
        folders = self.load_all_folders()
        folder_lookup = build_folder_hierarchy(folders)
        
        for folder in folders:
            if folder.get_path(folder_lookup) == path:
                return folder
        return None
    
    def _create_composite_key(self, subprompt_name: str, folder_path: Optional[str] = None) -> str:
        """
        Create a composite key for internal storage uniqueness (legacy support).
        
        Args:
            subprompt_name: The subprompt name
            folder_path: The folder path (can be None or empty)
            
        Returns:
            Composite key for storage
        """
        if folder_path and folder_path.strip():
            return f"{folder_path}/{subprompt_name}"
        else:
            return subprompt_name


# Factory function for easy instantiation
def create_storage(storage_path: Optional[str] = None) -> SubpromptStorage:
    """
    Factory function to create SubpromptStorage instance.
    
    Args:
        storage_path: Optional custom storage path
        
    Returns:
        Configured SubpromptStorage instance
    """
    return SubpromptStorage(storage_path)


# Global storage instance for shared use
_global_storage: Optional[SubpromptStorage] = None


def get_global_storage() -> SubpromptStorage:
    """
    Get or create global storage instance for shared use across nodes.
    
    Returns:
        Global SubpromptStorage instance
    """
    global _global_storage
    if _global_storage is None:
        _global_storage = SubpromptStorage()
    return _global_storage


def _invalidate_combo_cache():
    """
    Invalidate the dynamic combo box cache in prompt nodes.
    Called after storage operations that modify subprompts.
    """
    try:
        # Import here to avoid circular imports
        from ..nodes.prompt_nodes import invalidate_combo_cache
        invalidate_combo_cache()
    except ImportError as e:
        # This is expected during testing or if prompt_nodes isn't available
        pass
    except Exception as e:
        logger.warning(f"Error invalidating combo cache: {e}")


def reset_global_storage():
    """
    Reset the global storage instance to force fresh loading.
    Useful for clearing cached data.
    """
    global _global_storage
    _global_storage = None
    
    # Also invalidate combo cache when storage is reset
    _invalidate_combo_cache()