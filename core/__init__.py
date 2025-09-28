"""
Core System Components for ComfyUI-Prompt-Companion

This package contains the foundational data structures and operations that power
the prompt companion system:

- subprompt: Core data structures and operations for hierarchical prompt templates
- storage: Persistent JSON-based storage system for prompt templates and configurations  
- validation: Circular reference detection and prompt template validation

These core components are used by both the ComfyUI nodes and the web interface
to provide consistent prompt management functionality.
"""

# Import implemented core modules
from .subprompt import (
    Subprompt,
    SubpromptCollection,
    ResolvedPrompts,
    SubpromptError,
    CircularReferenceError,
    ValidationError
)

from .validation import (
    ValidationResult,
    detect_circular_references,
    validate_subprompt_structure,
    validate_order_references,
    validate_collection_integrity,
    validate_trigger_words,
    get_safe_resolution_order
)

from .storage import (
    SubpromptStorage,
    StorageError,
    create_storage,
    get_global_storage
)

__all__ = [
    # Core data structures
    "Subprompt",
    "SubpromptCollection",
    "ResolvedPrompts",
    
    # Exceptions
    "SubpromptError",
    "CircularReferenceError",
    "ValidationError",
    
    # Validation classes and functions
    "ValidationResult",
    "detect_circular_references",
    "validate_subprompt_structure",
    "validate_order_references",
    "validate_collection_integrity",
    "validate_trigger_words",
    "get_safe_resolution_order",
    
    # Storage classes and functions
    "SubpromptStorage",
    "StorageError",
    "create_storage",
    "get_global_storage"
]