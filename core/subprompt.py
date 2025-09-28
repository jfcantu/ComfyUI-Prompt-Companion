"""
Core Subprompt Data Structure and Operations

This module defines the foundational data structures and operations for the hierarchical
prompt template system used throughout ComfyUI-Prompt-Companion.

The Subprompt class represents individual prompt templates with support for:
- Hierarchical nesting with circular reference prevention
- Comma-separated prompt combining with proper formatting
- Trigger word management
- Folder organization for UI purposes
"""

import re
import logging
import uuid
from typing import Dict, List, Optional, Union, Any, Set
from dataclasses import dataclass
import copy

logger = logging.getLogger(__name__)


class SubpromptError(Exception):
    """Base exception for subprompt operations"""
    pass


class CircularReferenceError(SubpromptError):
    """Raised when circular references are detected in nested subprompts"""
    pass


class ValidationError(SubpromptError):
    """Raised when subprompt validation fails"""
    pass


@dataclass
class ResolvedPrompts:
    """Container for resolved positive and negative prompts"""
    positive: str = ""
    negative: str = ""


class Subprompt:
    """
    Core data structure for individual prompt templates.
    
    A subprompt represents a reusable prompt component that can contain:
    - Direct positive/negative text content
    - References to other nested subprompts
    - Trigger words for automatic activation
    - Organization metadata for folder structure
    
    Example subprompt structure:
    {
        "id": "mario_character",
        "positive": "Mario, red cap, mustache",
        "negative": "low quality",
        "trigger_words": ["mario", "plumber"],
        "order": ["background_subprompt", "attached", "style_subprompt"],
        "folder_path": "characters/nintendo"
    }
    """
    
    def __init__(self,
                 name: str,
                 positive: Optional[str] = None,
                 negative: Optional[str] = None,
                 trigger_words: Optional[List[str]] = None,
                 order: Optional[List[str]] = None,
                 folder_path: Optional[str] = None,
                 folder_id: Optional[str] = None,
                 id: Optional[str] = None,
                 **kwargs):
        """
        Initialize a new Subprompt instance with graceful handling of missing/invalid data.
        
        Args:
            name: Display name for this subprompt (required)
            positive: Positive prompt text (optional)
            negative: Negative prompt text (optional)
            trigger_words: List of words that trigger this subprompt (optional)
            order: Ordered list of nested subprompt names and "attached" marker (optional)
            folder_path: Organization path for UI folder structure (legacy, optional)
            folder_id: UUID of folder for organization (modern, optional)
            **kwargs: Additional metadata
        
        Raises:
            ValidationError: If name is empty or invalid
        """
        # Handle name with graceful fallback
        if not name or not isinstance(name, str) or not name.strip():
            raise ValidationError("Subprompt name must be a non-empty string")
            
        self.name = str(name).strip()
        
        # Handle ID with UUID generation if not provided
        if id and isinstance(id, str) and id.strip():
            self.id = id.strip()
        else:
            self.id = str(uuid.uuid4())
        
        # Handle positive text with safe defaults
        self.positive = ""
        if positive is not None:
            try:
                self.positive = str(positive).strip()
            except (TypeError, ValueError):
                logger.warning(f"Invalid positive text for subprompt '{self.name}', using empty default")
                self.positive = ""
        
        # Handle negative text with safe defaults
        self.negative = ""
        if negative is not None:
            try:
                self.negative = str(negative).strip()
            except (TypeError, ValueError):
                logger.warning(f"Invalid negative text for subprompt '{self.name}', using empty default")
                self.negative = ""
        
        # Handle trigger words with safe defaults and cleanup
        self.trigger_words = []
        if trigger_words is not None:
            try:
                if isinstance(trigger_words, (list, tuple)):
                    cleaned_words = []
                    for word in trigger_words:
                        try:
                            word_str = str(word).strip()
                            if word_str:  # Only add non-empty strings
                                cleaned_words.append(word_str)
                        except (TypeError, ValueError):
                            continue  # Skip invalid words
                    self.trigger_words = cleaned_words
                else:
                    logger.warning(f"trigger_words for subprompt '{self.name}' is not a list, using empty default")
            except Exception as e:
                logger.warning(f"Error processing trigger_words for subprompt '{self.name}': {e}, using empty default")
        
        # Handle order with safe defaults and validation
        self.order = ["attached"]  # Safe default
        if order is not None:
            try:
                if isinstance(order, (list, tuple)) and len(order) > 0:
                    cleaned_order = []
                    for item in order:
                        try:
                            item_str = str(item).strip()
                            if item_str:  # Only add non-empty strings
                                cleaned_order.append(item_str)
                        except (TypeError, ValueError):
                            continue  # Skip invalid items
                    
                    if cleaned_order:  # Only use if we have valid items
                        self.order = cleaned_order
                    else:
                        logger.warning(f"No valid order items for subprompt '{self.name}', using default")
                else:
                    logger.warning(f"order for subprompt '{self.name}' is not a valid list, using default")
            except Exception as e:
                logger.warning(f"Error processing order for subprompt '{self.name}': {e}, using default")
        
        # Handle folder path with safe defaults (legacy)
        self.folder_path = ""
        if folder_path is not None:
            try:
                self.folder_path = str(folder_path).strip()
            except (TypeError, ValueError):
                logger.warning(f"Invalid folder_path for subprompt '{self.name}', using empty default")
                self.folder_path = ""
        
        # Handle folder ID with safe defaults (modern)
        self.folder_id = None
        if folder_id is not None:
            try:
                folder_id_str = str(folder_id).strip()
                if folder_id_str:
                    self.folder_id = folder_id_str
            except (TypeError, ValueError):
                logger.warning(f"Invalid folder_id for subprompt '{self.name}', using None default")
                self.folder_id = None
        
        # Additional metadata with safe handling
        self.metadata = {}
        if kwargs:
            try:
                self.metadata = dict(kwargs)  # Create a safe copy
            except Exception as e:
                logger.warning(f"Error processing metadata for subprompt '{self.name}': {e}, using empty metadata")
                self.metadata = {}
        
        # Validate the structure
        self.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize subprompt to dictionary format for JSON storage.
        
        Returns:
            Dictionary representation of the subprompt
            
        Example:
            >>> subprompt = Subprompt("test", positive="hello")
            >>> data = subprompt.to_dict()
            >>> print(data["positive"])
            "hello"
        """
        result = {
            "id": self.id,
            "name": self.name,
            "positive": self.positive,
            "negative": self.negative,
            "trigger_words": self.trigger_words.copy(),
            "order": self.order.copy(),
            "folder_path": self.folder_path,
            "folder_id": self.folder_id
        }
        
        # Include any additional metadata
        for key, value in self.metadata.items():
            if key not in result:
                result[key] = value
                
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subprompt':
        """
        Create Subprompt instance from dictionary data with graceful handling of missing/corrupted fields.
        
        Args:
            data: Dictionary containing subprompt data
            
        Returns:
            New Subprompt instance
            
        Raises:
            ValidationError: If required fields are missing or invalid
            
        Example:
            >>> data = {"id": "test", "positive": "hello world"}
            >>> subprompt = Subprompt.from_dict(data)
            >>> print(subprompt.positive)
            "hello world"
        """
        if not data:
            raise ValidationError("Data cannot be None or empty")
            
        if not isinstance(data, dict):
            raise ValidationError("Data must be a dictionary")
            
        # Extract name (required)
        name_val = data.get("name")
        if not name_val:
            raise ValidationError("Missing required field: name")
        
        # Extract or generate ID
        id_val = data.get("id")
        if not id_val:
            id_val = str(uuid.uuid4())
            
        # Extract known fields with safe defaults
        try:
            kwargs = dict(data)  # Safe copy
        except Exception:
            raise ValidationError("Unable to process data dictionary")
        
        # Remove field names that are handled separately
        kwargs.pop("name", None)
        kwargs.pop("id", None)
        positive = kwargs.pop("positive", None)
        negative = kwargs.pop("negative", None)
        trigger_words = kwargs.pop("trigger_words", None)
        order = kwargs.pop("order", None)
        folder_path = kwargs.pop("folder_path", None)
        folder_id = kwargs.pop("folder_id", None)
        
        # Handle legacy field names or corrupted data
        if positive is None:
            positive = kwargs.pop("positive_text", None) or kwargs.pop("prompt", None)
        
        if negative is None:
            negative = kwargs.pop("negative_text", None) or kwargs.pop("negative_prompt", None)
            
        if trigger_words is None:
            trigger_words = kwargs.pop("triggers", None) or kwargs.pop("keywords", None)
            
        if order is None:
            # Check for legacy nested_subprompts field
            nested_subprompts = kwargs.pop("nested_subprompts", None)
            if nested_subprompts is not None:
                try:
                    if isinstance(nested_subprompts, (list, tuple)):
                        # Convert from nested_subprompts format to order format
                        converted_order = []
                        for item in nested_subprompts:
                            if item == "[Self]":
                                converted_order.append("attached")
                            elif item and isinstance(item, str):
                                converted_order.append(str(item).strip())
                        if converted_order:
                            order = converted_order
                except Exception as e:
                    logger.warning(f"Error converting nested_subprompts to order for '{name_val}': {e}")
        
        if folder_path is None:
            folder_path = kwargs.pop("folder", None) or kwargs.pop("category", None)
        
        if folder_id is None:
            folder_id = kwargs.pop("folder_uuid", None)
        
        return cls(
            name=name_val,
            id=id_val,
            positive=positive,
            negative=negative,
            trigger_words=trigger_words,
            order=order,
            folder_path=folder_path,
            folder_id=folder_id,
            **kwargs
        )
    
    def combine_prompts(self, other_positive: str = "", other_negative: str = "", 
                       prepend: bool = False) -> ResolvedPrompts:
        """
        Combine this subprompt's prompts with other prompt text.
        
        Handles proper comma separation without creating double-commas.
        
        Args:
            other_positive: Additional positive prompt text to combine
            other_negative: Additional negative prompt text to combine
            prepend: If True, prepend other text; if False, append
            
        Returns:
            ResolvedPrompts containing combined positive and negative text
            
        Example:
            >>> subprompt = Subprompt("test", positive="red car")
            >>> result = subprompt.combine_prompts("blue sky", prepend=True)
            >>> print(result.positive)
            "blue sky, red car"
        """
        def clean_combine(text1: str, text2: str, prepend_first: bool = False) -> str:
            """Combine two text strings with proper comma handling"""
            # Clean whitespace and commas from ends
            text1 = text1.strip().strip(',').strip()
            text2 = text2.strip().strip(',').strip()
            
            if not text1 and not text2:
                return ""
            elif not text1:
                return text2
            elif not text2:
                return text1
            else:
                if prepend_first:
                    return f"{text1}, {text2}"
                else:
                    return f"{text2}, {text1}"
        
        if prepend:
            combined_positive = clean_combine(other_positive, self.positive, True)
            combined_negative = clean_combine(other_negative, self.negative, True)
        else:
            combined_positive = clean_combine(self.positive, other_positive, True)
            combined_negative = clean_combine(self.negative, other_negative, True)
            
        return ResolvedPrompts(
            positive=combined_positive,
            negative=combined_negative
        )
    
    def get_trigger_words(self) -> List[str]:
        """
        Get list of trigger words for this subprompt.
        
        Returns:
            List of trigger words (copy of internal list)
            
        Example:
            >>> subprompt = Subprompt("test", trigger_words=["mario", "nintendo"])
            >>> words = subprompt.get_trigger_words()
            >>> print(words)
            ["mario", "nintendo"]
        """
        return self.trigger_words.copy()
    
    def resolve_nested(self, collection: Dict[str, 'Subprompt'], 
                      visited: Optional[Set[str]] = None) -> ResolvedPrompts:
        """
        Resolve nested subprompt references recursively.
        
        Processes the order list to combine text from nested subprompts and
        attached content in the specified sequence.
        
        Args:
            collection: Dictionary mapping subprompt IDs to Subprompt instances
            visited: Set of already visited IDs for circular reference detection
            
        Returns:
            ResolvedPrompts containing fully resolved positive and negative text
            
        Raises:
            CircularReferenceError: If circular references are detected
            ValidationError: If referenced subprompts don't exist
            
        Example:
            >>> collection = {"bg": Subprompt("bg", positive="forest")}
            >>> main = Subprompt("main", positive="knight", order=["bg", "attached"])
            >>> result = main.resolve_nested(collection)
            >>> print(result.positive)
            "forest, knight"
        """
        if visited is None:
            visited = set()
            
        if self.name in visited:
            raise CircularReferenceError(
                f"Circular reference detected: {' -> '.join(visited)} -> {self.name}"
            )
            
        visited.add(self.name)
        
        try:
            positive_parts = []
            negative_parts = []
            
            for item in self.order:
                if item == "attached":
                    # Add the directly attached positive/negative content
                    if self.positive.strip():
                        positive_parts.append(self.positive.strip())
                    if self.negative.strip():
                        negative_parts.append(self.negative.strip())
                        
                elif item in collection:
                    # Recursively resolve nested subprompt
                    nested_subprompt = collection[item]
                    
                    # Check if nested subprompt has unconverted nested_subprompts field and convert it
                    nested_list = None
                    if hasattr(nested_subprompt, 'nested_subprompts') and nested_subprompt.nested_subprompts:
                        nested_list = nested_subprompt.nested_subprompts
                    elif hasattr(nested_subprompt, 'metadata') and nested_subprompt.metadata and 'nested_subprompts' in nested_subprompt.metadata:
                        nested_list = nested_subprompt.metadata['nested_subprompts']
                    
                    # Apply field conversion if needed
                    if nested_list and nested_list != []:
                        # Convert JavaScript nested_subprompts format to Python order format
                        converted_order = []
                        for nested_item in nested_list:
                            if nested_item == "[Self]":
                                converted_order.append("attached")
                            else:
                                converted_order.append(nested_item)
                        
                        # Temporarily update the order field for resolution
                        original_order = nested_subprompt.order
                        nested_subprompt.order = converted_order
                        
                        # Resolve with corrected order - pass the same visited set for circular reference detection
                        nested_result = nested_subprompt.resolve_nested(collection, visited)
                        
                        # Restore original order
                        nested_subprompt.order = original_order
                    else:
                        # No conversion needed, resolve normally - pass the same visited set
                        nested_result = nested_subprompt.resolve_nested(collection, visited)
                    
                    if nested_result.positive.strip():
                        positive_parts.append(nested_result.positive.strip())
                    if nested_result.negative.strip():
                        negative_parts.append(nested_result.negative.strip())
                        
                else:
                    pass
                    
            # Clean and combine parts with proper comma handling
            def join_parts(parts: List[str]) -> str:
                # Remove empty parts and clean each part
                clean_parts = []
                for part in parts:
                    cleaned = part.strip().strip(',').strip()
                    if cleaned:
                        clean_parts.append(cleaned)
                return ", ".join(clean_parts)
            
            return ResolvedPrompts(
                positive=join_parts(positive_parts),
                negative=join_parts(negative_parts)
            )
            
        finally:
            visited.discard(self.name)
    
    def validate(self) -> None:
        """
        Perform basic validation of subprompt structure.
        
        Raises:
            ValidationError: If validation fails
            
        Example:
            >>> subprompt = Subprompt("valid_id", positive="test")
            >>> subprompt.validate()  # Should not raise
        """
        # Validate name
        if not self.name or not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Name must be a non-empty string")
            
        # Validate trigger words
        if not isinstance(self.trigger_words, list):
            raise ValidationError("trigger_words must be a list")
            
        for word in self.trigger_words:
            if not isinstance(word, str):
                raise ValidationError("All trigger words must be strings")
                
        # Validate order
        if not isinstance(self.order, list):
            raise ValidationError("order must be a list")
            
        # Must contain at least "attached" or some references
        if not self.order:
            raise ValidationError("order list cannot be empty")
            
        # Check for duplicate "attached" markers
        attached_count = self.order.count("attached")
        if attached_count > 1:
            raise ValidationError("order list can only contain one 'attached' marker")
            
        # Validate folder path format (if provided)
        if self.folder_path and not isinstance(self.folder_path, str):
            raise ValidationError("folder_path must be a string")
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"Subprompt(name='{self.name}', positive='{self.positive[:30]}...', order={self.order})"
    
    def __eq__(self, other) -> bool:
        """Equality comparison based on ID"""
        if not isinstance(other, Subprompt):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on ID for use in sets/dicts"""
        return hash(self.id)


class SubpromptCollection:
    """
    Container and manager for collections of subprompts.
    
    Provides operations for managing groups of related subprompts with
    validation and dependency resolution capabilities.
    """
    
    def __init__(self):
        """Initialize empty collection"""
        self.subprompts: Dict[str, Subprompt] = {}
        self.folders: Dict[str, List[str]] = {}  # folder_path -> list of subprompt IDs
    
    def add_subprompt(self, subprompt: Subprompt) -> None:
        """
        Add a subprompt to the collection.
        
        Args:
            subprompt: Subprompt instance to add
            
        Example:
            >>> collection = SubpromptCollection()
            >>> subprompt = Subprompt("test", positive="hello")
            >>> collection.add_subprompt(subprompt)
        """
        self.subprompts[subprompt.name] = subprompt
        
        # Update folder organization
        if subprompt.folder_path:
            if subprompt.folder_path not in self.folders:
                self.folders[subprompt.folder_path] = []
            if subprompt.name not in self.folders[subprompt.folder_path]:
                self.folders[subprompt.folder_path].append(subprompt.name)
    
    def get_subprompt(self, name: str) -> Optional[Subprompt]:
        """
        Retrieve subprompt by name.
        
        Args:
            name: Subprompt name to retrieve
            
        Returns:
            Subprompt instance or None if not found
        """
        return self.subprompts.get(name)
    
    def resolve_all_references(self) -> Dict[str, ResolvedPrompts]:
        """
        Resolve all template references in the collection.
        
        Returns:
            Dictionary mapping subprompt IDs to their resolved prompts
            
        Raises:
            CircularReferenceError: If circular references are detected
        """
        results = {}
        for subprompt_name, subprompt in self.subprompts.items():
            results[subprompt_name] = subprompt.resolve_nested(self.subprompts)
        return results