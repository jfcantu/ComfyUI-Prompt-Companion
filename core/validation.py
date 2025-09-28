"""
Validation System for ComfyUI-Prompt-Companion

This module provides comprehensive validation functionality for prompt templates,
with particular focus on circular reference detection and data integrity validation.

Key Features:
- Circular reference detection in nested subprompt templates using DFS
- Template syntax and structure validation
- Reference integrity checking
- Comprehensive error reporting with detailed paths
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result container for validation operations.
    
    Provides structured feedback about validation success/failure
    with detailed error and warning messages.
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, message: str) -> None:
        """Add an error message and mark result as invalid"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message"""
        self.warnings.append(message)
    
    def merge(self, other: 'ValidationResult') -> None:
        """Merge another validation result into this one"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


def detect_circular_references(collection: Dict[str, Any], start_id: Optional[str] = None) -> ValidationResult:
    """
    Detect circular references in subprompt dependency chains using DFS.
    
    Uses depth-first search to detect cycles in the dependency graph formed
    by nested subprompt references in the order lists.
    
    Args:
        collection: Dictionary mapping subprompt IDs to subprompt objects/dicts
        start_id: Optional starting subprompt ID to check specifically
        
    Returns:
        ValidationResult with circular reference detection results
        
    Example:
        >>> # Setup circular reference: A -> B -> A
        >>> collection = {
        ...     "A": {"id": "A", "order": ["B", "attached"]},
        ...     "B": {"id": "B", "order": ["A", "attached"]}
        ... }
        >>> result = detect_circular_references(collection)
        >>> print(result.is_valid)
        False
    """
    result = ValidationResult(is_valid=True)
    
    if not collection:
        return result
    
    # Build dependency graph
    try:
        graph = _build_dependency_graph(collection)
    except Exception as e:
        result.add_error(f"Failed to build dependency graph: {str(e)}")
        return result
    
    # Check for cycles using DFS
    if start_id:
        # Check specific subprompt
        if start_id not in graph:
            result.add_error(f"Subprompt '{start_id}' not found in collection")
            return result
            
        cycle_result = _detect_cycle_dfs(graph, start_id)
        if cycle_result.cycle_path:
            result.add_error(f"Circular reference detected starting from '{start_id}': {' -> '.join(cycle_result.cycle_path)}")
    else:
        # Check entire collection
        visited_global = set()
        
        for node_id in graph:
            if node_id not in visited_global:
                cycle_result = _detect_cycle_dfs(graph, node_id)
                visited_global.update(cycle_result.visited)
                
                if cycle_result.cycle_path:
                    result.add_error(f"Circular reference detected: {' -> '.join(cycle_result.cycle_path)}")
    
    return result


def validate_subprompt_structure(subprompt_data: Union[Dict[str, Any], Any]) -> ValidationResult:
    """
    Validate individual subprompt data structure.
    
    Checks for required fields, proper data types, and structural integrity
    of a single subprompt object or dictionary.
    
    Args:
        subprompt_data: Subprompt object or dictionary to validate
        
    Returns:
        ValidationResult with structural validation results
        
    Example:
        >>> data = {"id": "test", "positive": "hello", "order": ["attached"]}
        >>> result = validate_subprompt_structure(data)
        >>> print(result.is_valid)
        True
    """
    result = ValidationResult(is_valid=True)
    
    # Handle both dictionary and object inputs
    if hasattr(subprompt_data, 'to_dict'):
        # It's a Subprompt object
        try:
            data = subprompt_data.to_dict()
            # If it has a validate method, call it
            if hasattr(subprompt_data, 'validate'):
                subprompt_data.validate()
        except Exception as e:
            result.add_error(f"Subprompt object validation failed: {str(e)}")
            return result
    elif isinstance(subprompt_data, dict):
        data = subprompt_data
    else:
        result.add_error(f"Invalid subprompt data type: {type(subprompt_data)}")
        return result
    
    # Validate required fields - handle both "name" and legacy "id"
    name_field = None
    if "name" in data:
        name_field = data["name"]
        field_name = "name"
    elif "id" in data:
        # Backwards compatibility - treat "id" as "name"
        name_field = data["id"]
        field_name = "id"
    else:
        result.add_error("Missing required field: 'name' (or legacy 'id')")
    
    if name_field is not None:
        # Validate name/id
        if not isinstance(name_field, str) or not name_field.strip():
            result.add_error(f"Field '{field_name}' must be a non-empty string")
    
    # Validate optional string fields
    for field_name in ["positive", "negative", "folder_path"]:
        if field_name in data and data[field_name] is not None:
            if not isinstance(data[field_name], str):
                result.add_error(f"Field '{field_name}' must be a string")
    
    # Validate trigger_words
    if "trigger_words" in data:
        trigger_words = data["trigger_words"]
        if not isinstance(trigger_words, list):
            result.add_error("Field 'trigger_words' must be a list")
        else:
            for i, word in enumerate(trigger_words):
                if not isinstance(word, str):
                    result.add_error(f"Trigger word at index {i} must be a string")
                elif not word.strip():
                    result.add_warning(f"Empty trigger word at index {i}")
    
    # Validate order list
    if "order" in data:
        order = data["order"]
        if not isinstance(order, list):
            result.add_error("Field 'order' must be a list")
        else:
            if not order:
                result.add_error("Field 'order' cannot be empty")
            else:
                attached_count = order.count("attached")
                if attached_count == 0:
                    result.add_warning("Order list does not contain 'attached' marker")
                elif attached_count > 1:
                    result.add_error("Order list can only contain one 'attached' marker")
                
                # Check for valid reference format
                for i, item in enumerate(order):
                    if not isinstance(item, str):
                        result.add_error(f"Order item at index {i} must be a string")
                    elif item != "attached" and not item.strip():
                        result.add_error(f"Order item at index {i} is empty (should be 'attached' or valid reference)")
    
    return result


def validate_order_references(collection: Dict[str, Any], subprompt_id: str) -> ValidationResult:
    """
    Ensure order references in a subprompt are valid and exist in collection.
    
    Validates that all non-"attached" items in a subprompt's order list
    refer to existing subprompts in the collection.
    
    Args:
        collection: Dictionary mapping subprompt IDs to subprompt data
        subprompt_id: ID of the subprompt to validate references for
        
    Returns:
        ValidationResult with reference validation results
        
    Example:
        >>> collection = {"A": {"order": ["B", "attached"]}, "B": {"order": ["attached"]}}
        >>> result = validate_order_references(collection, "A")
        >>> print(result.is_valid)
        True
    """
    result = ValidationResult(is_valid=True)
    
    if subprompt_id not in collection:
        result.add_error(f"Subprompt '{subprompt_id}' not found in collection")
        return result
    
    subprompt_data = collection[subprompt_id]
    
    # Extract order list
    if hasattr(subprompt_data, 'order'):
        order = subprompt_data.order
    elif isinstance(subprompt_data, dict) and "order" in subprompt_data:
        order = subprompt_data["order"]
    else:
        result.add_warning(f"Subprompt '{subprompt_id}' has no order list to validate")
        return result
    
    if not isinstance(order, list):
        result.add_error(f"Order field in subprompt '{subprompt_id}' must be a list")
        return result
    
    # Check each reference in order
    for i, item in enumerate(order):
        if isinstance(item, str) and item != "attached":
            if item not in collection:
                result.add_error(f"Referenced subprompt '{item}' in order[{i}] of '{subprompt_id}' does not exist in collection")
            # Check for self-reference
            elif item == subprompt_id:
                result.add_error(f"Subprompt '{subprompt_id}' contains self-reference in order[{i}]")
    
    return result


def validate_collection_integrity(collection: Dict[str, Any]) -> ValidationResult:
    """
    Perform comprehensive validation of an entire subprompt collection.
    
    Validates structure, references, and circular dependencies for all
    subprompts in the collection.
    
    Args:
        collection: Dictionary mapping subprompt IDs to subprompt data
        
    Returns:
        ValidationResult with comprehensive collection validation results
    """
    result = ValidationResult(is_valid=True)
    
    if not collection:
        result.add_warning("Empty collection provided")
        return result
    
    # Validate each individual subprompt structure
    for subprompt_id, subprompt_data in collection.items():
        structure_result = validate_subprompt_structure(subprompt_data)
        if not structure_result.is_valid:
            for error in structure_result.errors:
                result.add_error(f"Subprompt '{subprompt_id}': {error}")
        for warning in structure_result.warnings:
            result.add_warning(f"Subprompt '{subprompt_id}': {warning}")
    
    # Validate all order references
    for subprompt_id in collection:
        reference_result = validate_order_references(collection, subprompt_id)
        result.merge(reference_result)
    
    # Check for circular references
    circular_result = detect_circular_references(collection)
    result.merge(circular_result)
    
    return result


# Helper classes and functions

@dataclass
class CycleDetectionResult:
    """Result of cycle detection algorithm"""
    has_cycle: bool = False
    cycle_path: List[str] = field(default_factory=list)
    visited: Set[str] = field(default_factory=set)


def _build_dependency_graph(collection: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Build dependency graph from subprompt collection.
    
    Args:
        collection: Dictionary mapping subprompt IDs to subprompt data
        
    Returns:
        Dictionary mapping each subprompt ID to list of dependencies
        
    Raises:
        ValueError: If collection data is malformed
    """
    graph = defaultdict(list)
    
    for subprompt_id, subprompt_data in collection.items():
        # Extract order list depending on data type
        if hasattr(subprompt_data, 'order'):
            order = subprompt_data.order
        elif isinstance(subprompt_data, dict) and "order" in subprompt_data:
            order = subprompt_data["order"]
        else:
            # No order list, no dependencies
            graph[subprompt_id] = []
            continue
        
        if not isinstance(order, list):
            raise ValueError(f"Order field for subprompt '{subprompt_id}' must be a list")
        
        # Extract dependencies (non-"attached" items)
        dependencies = []
        for item in order:
            if isinstance(item, str) and item != "attached" and item.strip():
                dependencies.append(item.strip())
        
        graph[subprompt_id] = dependencies
    
    return dict(graph)


def _detect_cycle_dfs(graph: Dict[str, List[str]], start_node: str) -> CycleDetectionResult:
    """
    Use DFS to detect cycles in dependency graph starting from a specific node.
    
    Args:
        graph: Dependency graph (node_id -> list of dependency IDs)
        start_node: Starting node for cycle detection
        
    Returns:
        CycleDetectionResult with cycle information
    """
    result = CycleDetectionResult()
    
    visited = set()
    recursion_stack = set()
    path = []
    
    def dfs(node: str) -> bool:
        """DFS helper function"""
        if node in recursion_stack:
            # Found a cycle - build the cycle path
            cycle_start_index = path.index(node)
            cycle_path = path[cycle_start_index:] + [node]
            result.cycle_path = cycle_path
            return True
            
        if node in visited:
            return False
        
        visited.add(node)
        recursion_stack.add(node)
        path.append(node)
        
        # Visit all dependencies
        for neighbor in graph.get(node, []):
            if dfs(neighbor):
                return True
        
        recursion_stack.remove(node)
        path.pop()
        return False
    
    result.has_cycle = dfs(start_node)
    result.visited = visited
    
    return result


def validate_trigger_words(trigger_words: List[str], content: str = "") -> ValidationResult:
    """
    Validate trigger words format and optionally check against content.
    
    Args:
        trigger_words: List of trigger words to validate
        content: Optional content to check trigger words against
        
    Returns:
        ValidationResult with trigger word validation results
    """
    result = ValidationResult(is_valid=True)
    
    if not isinstance(trigger_words, list):
        result.add_error("Trigger words must be a list")
        return result
    
    for i, word in enumerate(trigger_words):
        if not isinstance(word, str):
            result.add_error(f"Trigger word at index {i} must be a string")
        elif not word.strip():
            result.add_error(f"Trigger word at index {i} is empty")
        elif len(word.strip()) < 2:
            result.add_warning(f"Trigger word '{word.strip()}' at index {i} is very short")
        
        # Optional content checking
        if content and word.strip():
            word_clean = word.strip().lower()
            content_clean = content.lower()
            if word_clean not in content_clean:
                result.add_warning(f"Trigger word '{word.strip()}' not found in content")
    
    return result


def get_safe_resolution_order(collection: Dict[str, Any]) -> Tuple[List[str], ValidationResult]:
    """
    Get topologically sorted order for safe reference resolution.
    
    Uses Kahn's algorithm to find a safe order for resolving nested
    subprompt references without circular dependencies.
    
    Args:
        collection: Dictionary mapping subprompt IDs to subprompt data
        
    Returns:
        Tuple of (safe_order_list, validation_result)
        
    Example:
        >>> collection = {
        ...     "A": {"order": ["B", "attached"]},
        ...     "B": {"order": ["attached"]}
        ... }
        >>> order, result = get_safe_resolution_order(collection)
        >>> print(order)
        ['B', 'A']
    """
    result = ValidationResult(is_valid=True)
    
    if not collection:
        return [], result
    
    try:
        # Build dependency graph (who depends on what)
        dependency_graph = _build_dependency_graph(collection)
        
        # Build forward graph (who can be processed after this node)
        forward_graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize all nodes
        for node in collection:
            in_degree[node] = 0
            forward_graph[node] = []
        
        # Build forward edges and count in-degrees
        for node, dependencies in dependency_graph.items():
            for dep in dependencies:
                if dep in collection:  # Only count valid references
                    forward_graph[dep].append(node)  # dep -> node
                    in_degree[node] += 1
                else:
                    result.add_warning(f"Reference to non-existent subprompt '{dep}' in '{node}'")
        
        # Kahn's algorithm for topological sorting
        queue = deque()
        safe_order = []
        
        # Find nodes with no incoming edges (no dependencies)
        for node in collection:
            if in_degree[node] == 0:
                queue.append(node)
        
        while queue:
            current = queue.popleft()
            safe_order.append(current)
            
            # Remove edges from current node to its dependents
            for neighbor in forward_graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check if all nodes were processed (no cycles)
        if len(safe_order) != len(collection):
            result.add_error("Cannot determine safe resolution order - circular dependencies detected")
            # Find remaining nodes with dependencies
            remaining = [node for node in graph if node not in safe_order]
            result.add_error(f"Nodes with unresolved dependencies: {remaining}")
        
        return safe_order, result
        
    except Exception as e:
        result.add_error(f"Failed to calculate safe resolution order: {str(e)}")
        return [], result