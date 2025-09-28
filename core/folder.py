"""
Folder Data Model for ComfyUI-Prompt-Companion

This module provides the Folder class for representing and managing hierarchical folder structures
with UUID-based identification, maintaining architectural consistency with the Subprompt system.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FolderError(Exception):
    """Base exception for folder-related operations"""
    pass


class FolderValidationError(FolderError):
    """Exception raised when folder validation fails"""
    pass


class Folder:
    """
    Represents a hierarchical folder with UUID-based identification.
    
    Provides a consistent data model for organizing subprompts with immutable
    identifiers that support referential integrity during structural changes.
    """
    
    def __init__(self, id: str = None, name: str = "", parent_id: str = None, 
                 created: str = None, updated: str = None, **metadata):
        """
        Initialize a Folder instance.
        
        Args:
            id: Unique UUID identifier. If None, generates a new UUID.
            name: Display name of the folder
            parent_id: UUID of parent folder. None for root-level folders.
            created: ISO timestamp when folder was created
            updated: ISO timestamp when folder was last updated
            **metadata: Additional folder metadata
            
        Raises:
            FolderValidationError: If folder data is invalid
        """
        # Generate UUID if not provided
        self.id = id if id else str(uuid.uuid4())
        
        # Validate and set basic fields
        if not isinstance(name, str):
            raise FolderValidationError("Folder name must be a string")
        
        self.name = name.strip()
        if not self.name:
            raise FolderValidationError("Folder name cannot be empty")
        
        # Validate parent_id if provided
        if parent_id is not None:
            if not isinstance(parent_id, str) or not parent_id.strip():
                raise FolderValidationError("Parent ID must be a valid string")
            self.parent_id = parent_id.strip()
        else:
            self.parent_id = None
        
        # Set timestamps
        now = datetime.now(timezone.utc).isoformat()
        self.created = created if created else now
        self.updated = updated if updated else now
        
        # Store additional metadata
        self.metadata = metadata or {}
        
        # Validate UUID format
        try:
            uuid.UUID(self.id)
        except ValueError as e:
            raise FolderValidationError(f"Invalid UUID format for folder ID: {e}")
        
        if self.parent_id:
            try:
                uuid.UUID(self.parent_id)
            except ValueError as e:
                raise FolderValidationError(f"Invalid UUID format for parent ID: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert folder to dictionary representation for storage/API.
        
        Returns:
            Dictionary containing all folder data
        """
        result = {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "created": self.created,
            "updated": self.updated
        }
        
        # Include metadata if present
        if self.metadata:
            result.update(self.metadata)
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Folder':
        """
        Create Folder instance from dictionary data.
        
        Args:
            data: Dictionary containing folder data
            
        Returns:
            Folder instance
            
        Raises:
            FolderValidationError: If data is invalid or missing required fields
        """
        if not isinstance(data, dict):
            raise FolderValidationError("Folder data must be a dictionary")
        
        # Extract known fields
        known_fields = {"id", "name", "parent_id", "created", "updated"}
        folder_data = {}
        metadata = {}
        
        for key, value in data.items():
            if key in known_fields:
                folder_data[key] = value
            else:
                metadata[key] = value
        
        # Add metadata to folder_data
        if metadata:
            folder_data["metadata"] = metadata
        
        try:
            return cls(**folder_data)
        except Exception as e:
            raise FolderValidationError(f"Failed to create folder from data: {e}")
    
    @classmethod
    def from_path(cls, path: str, folder_hierarchy: Dict[str, 'Folder'] = None) -> 'Folder':
        """
        Create folder from legacy path string, with optional parent lookup.
        
        Args:
            path: Folder path string (e.g., "project/assets")
            folder_hierarchy: Optional dict mapping paths to existing folders
            
        Returns:
            Folder instance
        """
        if not isinstance(path, str) or not path.strip():
            raise FolderValidationError("Path must be a non-empty string")
        
        path = path.strip()
        path_parts = path.split('/')
        name = path_parts[-1]
        parent_path = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ""
        
        # Look up parent folder if hierarchy provided
        parent_id = None
        if folder_hierarchy and parent_path:
            parent_folder = folder_hierarchy.get(parent_path)
            if parent_folder:
                parent_id = parent_folder.id
        
        return cls(
            name=name,
            parent_id=parent_id,
            path=path  # Store original path in metadata for migration
        )
    
    def get_path(self, folder_lookup: Dict[str, 'Folder'] = None) -> str:
        """
        Generate path string from folder hierarchy.
        
        Args:
            folder_lookup: Dictionary mapping folder IDs to Folder objects
            
        Returns:
            Path string (e.g., "project/assets")
        """
        if not folder_lookup:
            # Cannot resolve path without lookup - return name only
            return self.name
        
        path_parts = []
        current = self
        visited = set()  # Prevent infinite loops
        
        while current and current.id not in visited:
            visited.add(current.id)
            path_parts.append(current.name)
            
            # Get parent folder
            if current.parent_id:
                current = folder_lookup.get(current.parent_id)
            else:
                break
        
        # Reverse to get correct order (root -> leaf)
        path_parts.reverse()
        return '/'.join(path_parts)
    
    def get_children(self, all_folders: List['Folder']) -> List['Folder']:
        """
        Get direct child folders.
        
        Args:
            all_folders: List of all available folders
            
        Returns:
            List of direct child folders
        """
        children = []
        for folder in all_folders:
            if folder.parent_id == self.id:
                children.append(folder)
        
        return sorted(children, key=lambda f: f.name.lower())
    
    def get_descendants(self, all_folders: List['Folder']) -> List['Folder']:
        """
        Get all descendant folders recursively.
        
        Args:
            all_folders: List of all available folders
            
        Returns:
            List of all descendant folders
        """
        descendants = []
        visited = set()  # Prevent infinite loops
        
        def collect_descendants(folder_id: str):
            if folder_id in visited:
                return
            visited.add(folder_id)
            
            for folder in all_folders:
                if folder.parent_id == folder_id:
                    descendants.append(folder)
                    collect_descendants(folder.id)
        
        collect_descendants(self.id)
        return descendants
    
    def is_ancestor_of(self, other: 'Folder', all_folders: List['Folder']) -> bool:
        """
        Check if this folder is an ancestor of another folder.
        
        Args:
            other: The folder to check
            all_folders: List of all available folders
            
        Returns:
            True if this folder is an ancestor of the other folder
        """
        if not other.parent_id:
            return False
        
        # Create lookup for efficient traversal
        folder_lookup = {f.id: f for f in all_folders}
        
        current = other
        visited = set()  # Prevent infinite loops
        
        while current and current.parent_id and current.id not in visited:
            visited.add(current.id)
            
            if current.parent_id == self.id:
                return True
            
            current = folder_lookup.get(current.parent_id)
        
        return False
    
    def can_move_to(self, new_parent_id: str, all_folders: List['Folder']) -> bool:
        """
        Check if folder can be moved to a new parent without creating cycles.
        
        Args:
            new_parent_id: UUID of potential new parent
            all_folders: List of all available folders
            
        Returns:
            True if move is valid
        """
        if new_parent_id is None:
            return True  # Can always move to root
        
        if new_parent_id == self.id:
            return False  # Cannot be parent of itself
        
        # Find the target parent
        target_parent = None
        for folder in all_folders:
            if folder.id == new_parent_id:
                target_parent = folder
                break
        
        if not target_parent:
            return False  # Target parent doesn't exist
        
        # Check if target parent is a descendant of this folder
        return not self.is_ancestor_of(target_parent, all_folders)
    
    def update_timestamp(self):
        """Update the folder's updated timestamp to current time."""
        self.updated = datetime.now(timezone.utc).isoformat()
    
    def __eq__(self, other) -> bool:
        """Check equality based on UUID."""
        if not isinstance(other, Folder):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on UUID."""
        return hash(self.id)
    
    def __str__(self) -> str:
        """String representation."""
        parent_info = f" (parent: {self.parent_id})" if self.parent_id else " (root)"
        return f"Folder({self.name}{parent_info})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"Folder(id='{self.id}', name='{self.name}', parent_id='{self.parent_id}')"


def build_folder_hierarchy(folders: List[Folder]) -> Dict[str, Folder]:
    """
    Build a lookup dictionary for folders by ID.
    
    Args:
        folders: List of folder objects
        
    Returns:
        Dictionary mapping folder IDs to folder objects
    """
    return {folder.id: folder for folder in folders}


def get_root_folders(folders: List[Folder]) -> List[Folder]:
    """
    Get all root-level folders (those without parents).
    
    Args:
        folders: List of folder objects
        
    Returns:
        List of root-level folders
    """
    return [folder for folder in folders if folder.parent_id is None]


def validate_folder_structure(folders: List[Folder]) -> List[str]:
    """
    Validate folder structure for consistency and detect issues.
    
    Args:
        folders: List of folder objects to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    folder_lookup = build_folder_hierarchy(folders)
    
    # Check for duplicate names within same parent
    parent_children = {}
    for folder in folders:
        parent_id = folder.parent_id or "ROOT"
        if parent_id not in parent_children:
            parent_children[parent_id] = []
        parent_children[parent_id].append(folder)
    
    for parent_id, children in parent_children.items():
        name_counts = {}
        for child in children:
            name = child.name.lower()
            name_counts[name] = name_counts.get(name, 0) + 1
        
        for name, count in name_counts.items():
            if count > 1:
                parent_name = "root" if parent_id == "ROOT" else folder_lookup.get(parent_id, {}).name
                errors.append(f"Duplicate folder name '{name}' in parent '{parent_name}'")
    
    # Check for orphaned folders (parent doesn't exist)
    for folder in folders:
        if folder.parent_id and folder.parent_id not in folder_lookup:
            errors.append(f"Folder '{folder.name}' has non-existent parent ID: {folder.parent_id}")
    
    # Check for circular references
    for folder in folders:
        visited = set()
        current = folder
        
        while current and current.parent_id and current.id not in visited:
            visited.add(current.id)
            current = folder_lookup.get(current.parent_id)
        
        if current and current.id in visited:
            errors.append(f"Circular reference detected in folder hierarchy at '{folder.name}'")
    
    return errors