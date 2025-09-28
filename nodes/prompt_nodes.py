"""
Core Prompt Manipulation Nodes for ComfyUI-Prompt-Companion

This module contains the primary node implementations for prompt manipulation:
- PromptCompanionAddSubpromptNode: Main node for combining and managing subprompts
- PromptCompanionSubpromptToStringsNode: Convert subprompt to text strings
- PromptCompanionStringsToSubpromptNode: Create subprompt from text strings

Each node follows ComfyUI conventions with INPUT_TYPES, RETURN_TYPES, FUNCTION, and CATEGORY.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import folder_paths
except ImportError:
    folder_paths = None

# Import core functionality
from ..core.subprompt import (ResolvedPrompts, Subprompt, SubpromptError,
                              ValidationError)

logger = logging.getLogger(__name__)

# ComfyUI Native Dynamic Combo Box Pattern
# Following the same approach as built-in nodes like folder_paths.get_filename_list()

def invalidate_combo_cache():
    """
    Invalidate combo cache - placeholder for compatibility.
    With the new dynamic approach, no cache invalidation is needed.
    """


class PromptCompanionAddSubpromptNode:
    """
    Main node for adding and combining subprompts with additional positive/negative text.

    This node allows users to:
    - Load existing subprompts from a dropdown
    - Add custom positive/negative text
    - Combine multiple subprompts
    - Control text positioning (prepend/append)
    """

    @classmethod
    def INPUT_TYPES(cls):
        """
        Define input types for the Add Subprompt node.

        Uses ComfyUI's native dynamic combo box pattern with direct function call.
        """
        # Use direct function call each time - ComfyUI's native pattern
        subprompt_names = cls._get_current_subprompt_names()

        return {
            "required": {
                "positive": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Additional positive prompt text to add",
                    },
                ),
                "negative": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Additional negative prompt text to add",
                    },
                ),
                "merge_order": (
                    [
                        "input,textbox,subprompt",
                        "input,subprompt,textbox",
                        "textbox,input,subprompt",
                        "textbox,subprompt,input",
                        "subprompt,input,textbox",
                        "subprompt,textbox,input"
                    ],
                    {
                        "default": "input,textbox,subprompt",
                        "tooltip": "Order in which input, textbox, and subprompt are merged (comma-separated)",
                    },
                ),
            },
            "optional": {
                "subprompt": (
                    "*",
                    {"tooltip": "Existing subprompt to extend (optional)"},
                ),
                "subprompt_selection": (
                    subprompt_names,
                    {
                        "default": "",
                        "tooltip": "Select a subprompt to apply"
                    }
                ),
            },
        }

    RETURN_TYPES = ("*", "STRING", "STRING")
    RETURN_NAMES = ("subprompt", "positive", "negative")
    FUNCTION = "add_subprompt"
    CATEGORY = "prompt-companion"
    OUTPUT_NODE = True

    DESCRIPTION = "Add and combine subprompts with additional positive/negative text. Supports loading from templates and combining multiple subprompts."

    @classmethod
    def VALIDATE_INPUTS(cls, subprompt_selection, **kwargs):
        """Validate that the selected subprompt name is valid"""
        if not subprompt_selection or subprompt_selection == "":
            return True  # Empty selection is valid

        # Allow [None] option to pass validation
        if subprompt_selection == "[None]":
            return True

        # Allow fallback options to pass validation
        fallback_options = ["[No Subprompts Found]", "[Storage Not Available]", "[Error Loading Subprompts]", "[No Data Loaded]"]
        if subprompt_selection in fallback_options:
            return True

        # Use direct function call to get current valid names
        valid_names = cls._get_current_subprompt_names()
        return subprompt_selection in valid_names

    @classmethod
    def IS_CHANGED(cls, subprompt_selection, **kwargs):
        """Determine if node output needs recomputation based on available subprompts and their content"""
        try:
            import hashlib
            # Include current subprompt availability in the hash
            available_names = cls._get_current_subprompt_names()
            state_components = [
                str(subprompt_selection),
                str(sorted(available_names)),  # Changes when subprompts are added/removed
                str(kwargs.get('positive', '')),
                str(kwargs.get('negative', '')),
                str(kwargs.get('merge_order', 'input,textbox,subprompt'))
            ]
            
            # Include the actual content and nested order of the selected subprompt
            if subprompt_selection and subprompt_selection.strip() and subprompt_selection != "[None]":
                selected_subprompt = cls._load_subprompt_by_name(subprompt_selection.strip())
                if selected_subprompt:
                    # Include subprompt content and nested order in hash
                    subprompt_state = [
                        str(selected_subprompt.positive or ''),
                        str(selected_subprompt.negative or ''),
                        str(selected_subprompt.order or ['attached']),  # This is key - detects order changes!
                        str(selected_subprompt.trigger_words or [])
                    ]
                    state_components.extend(subprompt_state)
            
            # Also include connected subprompt state if provided
            subprompt_input = kwargs.get('subprompt')
            if subprompt_input:
                connected_state = [
                    str(getattr(subprompt_input, 'positive', '') or ''),
                    str(getattr(subprompt_input, 'negative', '') or ''),
                    str(getattr(subprompt_input, 'order', ['attached']) or ['attached']),
                    str(getattr(subprompt_input, 'trigger_words', []) or [])
                ]
                state_components.extend(connected_state)
            
            state_string = '|'.join(state_components)
            return hashlib.sha256(state_string.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error in IS_CHANGED: {e}")
            return str(time.time())

    @classmethod
    def _get_current_subprompt_names(cls):
        """
        Get current subprompt names with folder path prefixes - called each time INPUT_TYPES() is evaluated.
        
        This follows ComfyUI's native dynamic combo box pattern where the function
        is called directly each time, similar to folder_paths.get_filename_list().
        
        Returns names in format "folder_path/subprompt_name" or just "subprompt_name" for root items.
        """
        try:
            from ..core.storage import get_global_storage
            from ..api_routes import get_subprompt_folder_path
            
            storage = get_global_storage()
            if storage:
                subprompts = storage.load_all_subprompts()
                display_names = []
                
                for sp in subprompts:
                    if hasattr(sp, 'name') and sp.name and sp.name.strip():
                        # Calculate the actual folder path from hierarchy
                        folder_path = get_subprompt_folder_path(storage, sp)
                        
                        if folder_path and folder_path.strip():
                            display_name = f"{folder_path}/{sp.name}"
                        else:
                            display_name = sp.name
                        
                        display_names.append(display_name)
                
                if display_names:
                    return ["[None]", ""] + sorted(set(display_names))  # Add [None] option first, then empty, then sorted names
                else:
                    return ["[None]", "[No Subprompts Found]"]
            else:
                return ["[None]", "[Storage Not Available]"]
        except Exception as e:
            logger.error(f"Error loading current subprompt names with folder paths: {e}")
            return ["[None]", "[Error Loading Subprompts]"]

    @classmethod
    def _get_subprompts_with_folder_paths(cls):
        """
        Get subprompts with folder paths for dropdown options.
        This method is used by the API to refresh dropdown options after save operations.
        
        Returns:
            List[str]: List of subprompt names with folder paths in format "folder_path/name"
        """
        try:
            from ..core.storage import get_global_storage
            from ..api_routes import get_subprompt_folder_path
            
            storage = get_global_storage()
            if storage:
                subprompts = storage.load_all_subprompts()
                options = ["[None]", ""]
                
                for sp in subprompts:
                    if hasattr(sp, 'name') and sp.name and sp.name.strip():
                        # Calculate the actual folder path from hierarchy
                        folder_path = get_subprompt_folder_path(storage, sp)
                        
                        if folder_path and folder_path.strip():
                            options.append(f"{folder_path}/{sp.name}")
                        else:
                            options.append(sp.name)
                
                return sorted(set(options[2:])) if len(options) > 2 else ["[None]", "[No Subprompts Found]"]
            else:
                return ["[None]", "[Storage Not Available]"]
        except Exception as e:
            logger.error(f"Error in _get_subprompts_with_folder_paths: {e}")
            return ["[None]", "[Error Loading Subprompts]"]

    @classmethod
    def _load_subprompt_by_name(cls, name):
        """Load subprompt by name, handling both prefixed and simple names"""
        if not name or name == "":
            return None

        # Handle "[None]" option - return None to represent no subprompt
        if name == "[None]":
            return None

        # Handle fallback options - don't try to load these as actual subprompts
        fallback_options = ["[No Subprompts Found]", "[Storage Not Available]", "[Error Loading Subprompts]"]
        if name in fallback_options:
            return None

        try:
            from ..core.storage import get_global_storage
            from ..api_routes import get_subprompt_folder_path
            
            storage = get_global_storage()
            if storage:
                subprompts = storage.load_all_subprompts()
                
                # Check if the name has a folder path prefix (format: "folder_path/subprompt_name")
                if "/" in name:
                    # Extract folder path and subprompt name
                    folder_path_part, subprompt_name = name.rsplit("/", 1)
                    
                    # Find subprompt by name and matching folder path
                    for sp in subprompts:
                        if hasattr(sp, 'name') and sp.name == subprompt_name:
                            # Calculate actual folder path and compare
                            actual_folder_path = get_subprompt_folder_path(storage, sp)
                            if actual_folder_path == folder_path_part:
                                return sp
                else:
                    # Simple name matching (for root-level subprompts or legacy format)
                    for sp in subprompts:
                        if hasattr(sp, 'name') and sp.name == name:
                            # Ensure this is a root-level subprompt (no folder path)
                            actual_folder_path = get_subprompt_folder_path(storage, sp)
                            if not actual_folder_path:
                                return sp
            return None
        except Exception as e:
            logger.error(f"Error loading subprompt by name '{name}': {e}")
            return None

    def add_subprompt(
        self,
        positive: str = "",
        negative: str = "",
        merge_order: str = "input,textbox,subprompt",
        subprompt: Optional[Subprompt] = None,
        subprompt_selection: str = "",
    ) -> Tuple[Subprompt, str, str]:
        """
        Main execution function for combining subprompts with additional text.

        Args:
            positive: Additional positive prompt text
            negative: Additional negative prompt text
            merge_order: Order to merge input, textbox, and subprompt (comma-separated)
            subprompt: Existing subprompt object (optional)
            subprompt_selection: Name of subprompt to load from templates (optional)

        Returns:
            Tuple of (combined_subprompt, resolved_positive, resolved_negative)
        """
        try:
            # Get storage instance and load all subprompts for nested resolution
            from ..core.storage import get_global_storage

            storage = get_global_storage()

            # Determine base subprompt - merge both connected input and selection if both provided
            base_subprompt = None
            selection_subprompt = None

            # Initialize all variables to prevent "possibly unbound" errors
            connected_resolved_prompts = None
            selection_resolved_prompts = None
            connected_original_id = "unknown"
            selection_original_id = "unknown"
            connected_original_triggers = []
            selection_original_triggers = []

            # Load subprompt from combo selection if provided
            if (
                subprompt_selection
                and subprompt_selection.strip()
                and subprompt_selection.strip().lower() not in ["none", ""]
                and subprompt_selection.strip() != "[None]"
            ):
                subprompt_selection = subprompt_selection.strip()
                
                # Simple name-based loading
                selection_subprompt = self._load_subprompt_by_name(subprompt_selection)
                if not selection_subprompt:
                    logger.warning(f"No subprompt found matching: {subprompt_selection}")

            # Get storage for nested resolution
            if storage:
                all_subprompts_list = storage.load_all_subprompts()
                # Convert to dict format for compatibility with resolve_nested method
                all_subprompts = {sp.name: sp for sp in all_subprompts_list}

                # Resolve connected input subprompt if provided
                if subprompt is not None:
                    connected_original_id = getattr(
                        subprompt, "name", getattr(subprompt, "id", "unknown")
                    )
                    connected_original_triggers = subprompt.get_trigger_words()
                    try:
                        # Check if it has nested references to resolve
                        has_nested = False
                        nested_subprompts_attr = getattr(
                            subprompt, "nested_subprompts", None
                        )
                        order_attr = getattr(subprompt, "order", ["attached"])

                        if nested_subprompts_attr and nested_subprompts_attr != []:
                            has_nested = True
                        elif order_attr != ["attached"]:
                            has_nested = True

                        if has_nested:
                            # resolve_nested() returns ResolvedPrompts object
                            connected_resolved_prompts = subprompt.resolve_nested(
                                all_subprompts
                            )
                        else:
                            # Create ResolvedPrompts-like object for consistency
                            from ..core.subprompt import ResolvedPrompts

                            connected_resolved_prompts = ResolvedPrompts(
                                positive=subprompt.positive, negative=subprompt.negative
                            )
                    except Exception as resolve_error:
                        logger.warning(
                            f"Failed to resolve connected subprompt: {resolve_error}"
                        )
                        from ..core.subprompt import ResolvedPrompts

                        connected_resolved_prompts = ResolvedPrompts(
                            positive=subprompt.positive, negative=subprompt.negative
                        )

                # Resolve selection subprompt if provided
                if selection_subprompt is not None:
                    selection_original_id = getattr(
                        selection_subprompt,
                        "name",
                        getattr(selection_subprompt, "id", "unknown"),
                    )
                    selection_original_triggers = (
                        selection_subprompt.get_trigger_words()
                    )
                    try:
                        # Check if it has nested references to resolve
                        has_nested = False
                        nested_subprompts_attr = getattr(
                            selection_subprompt, "nested_subprompts", None
                        )
                        order_attr = getattr(selection_subprompt, "order", ["attached"])

                        if nested_subprompts_attr and nested_subprompts_attr != []:
                            has_nested = True
                        elif order_attr != ["attached"]:
                            has_nested = True

                        if has_nested:
                            # resolve_nested() returns ResolvedPrompts object
                            selection_resolved_prompts = (
                                selection_subprompt.resolve_nested(all_subprompts)
                            )
                        else:
                            # Create ResolvedPrompts-like object for consistency
                            from ..core.subprompt import ResolvedPrompts

                            selection_resolved_prompts = ResolvedPrompts(
                                positive=selection_subprompt.positive,
                                negative=selection_subprompt.negative,
                            )
                    except Exception as resolve_error:
                        logger.warning(
                            f"Failed to resolve selection subprompt: {resolve_error}"
                        )
                        from ..core.subprompt import ResolvedPrompts

                        selection_resolved_prompts = ResolvedPrompts(
                            positive=selection_subprompt.positive,
                            negative=selection_subprompt.negative,
                        )
            else:
                # No storage available, use inputs as-is
                if subprompt is not None:
                    connected_original_id = getattr(
                        subprompt, "name", getattr(subprompt, "id", "unknown")
                    )
                    connected_original_triggers = subprompt.get_trigger_words()
                    from ..core.subprompt import ResolvedPrompts

                    connected_resolved_prompts = ResolvedPrompts(
                        positive=subprompt.positive, negative=subprompt.negative
                    )
                if selection_subprompt is not None:
                    selection_original_id = getattr(
                        selection_subprompt,
                        "name",
                        getattr(selection_subprompt, "id", "unknown"),
                    )
                    selection_original_triggers = (
                        selection_subprompt.get_trigger_words()
                    )
                    from ..core.subprompt import ResolvedPrompts

                    selection_resolved_prompts = ResolvedPrompts(
                        positive=selection_subprompt.positive,
                        negative=selection_subprompt.negative,
                    )

            # Now merge the RESOLVED subprompts using the ResolvedPrompts objects
            if (
                connected_resolved_prompts is not None
                and selection_resolved_prompts is not None
            ):
                # Both inputs provided - merge the resolved results
                try:
                    # Create temporary subprompt from resolved connected input
                    temp_connected = Subprompt(
                        name="temp_connected",
                        positive=connected_resolved_prompts.positive,
                        negative=connected_resolved_prompts.negative,
                        order=["attached"],
                    )

                    # Combine with resolved selection
                    combined_result = temp_connected.combine_prompts(
                        other_positive=selection_resolved_prompts.positive,
                        other_negative=selection_resolved_prompts.negative,
                        prepend=False,  # Append selection to connected input
                    )

                    # Create merged subprompt using original names and triggers
                    base_subprompt = Subprompt(
                        name=f"{connected_original_id}_merged_{selection_original_id}",
                        positive=combined_result.positive,
                        negative=combined_result.negative,
                        trigger_words=connected_original_triggers
                        + selection_original_triggers,
                        order=["attached"],  # Already resolved, so simplified
                    )
                except Exception as merge_error:
                    logger.warning(
                        f"Failed to merge resolved subprompts, using connected input: {merge_error}"
                    )
                    # Fallback to connected input only
                    base_subprompt = Subprompt(
                        name=connected_original_id,
                        positive=connected_resolved_prompts.positive,
                        negative=connected_resolved_prompts.negative,
                        trigger_words=connected_original_triggers,
                        order=["attached"],
                    )

            elif connected_resolved_prompts is not None:
                # Only connected input provided
                base_subprompt = Subprompt(
                    name=connected_original_id,
                    positive=connected_resolved_prompts.positive,
                    negative=connected_resolved_prompts.negative,
                    trigger_words=connected_original_triggers,
                    order=["attached"],
                )
            elif selection_resolved_prompts is not None:
                # Only selection provided
                base_subprompt = Subprompt(
                    name=selection_original_id,
                    positive=selection_resolved_prompts.positive,
                    negative=selection_resolved_prompts.negative,
                    trigger_words=selection_original_triggers,
                    order=["attached"],
                )
            else:
                # No base subprompt, create a new one
                base_subprompt = Subprompt(
                    name="generated_subprompt",
                    positive="",
                    negative="",
                    order=["attached"],
                )

            # Prepare the three components for merging based on merge_order
            # textbox: text entered in the node's positive/negative fields
            textbox_positive = str(positive or "")
            textbox_negative = str(negative or "")
            
            # input: connected subprompt (from subprompt parameter)
            input_positive = ""
            input_negative = ""
            if connected_resolved_prompts is not None:
                input_positive = connected_resolved_prompts.positive or ""
                input_negative = connected_resolved_prompts.negative or ""
            
            # subprompt: selected subprompt (from subprompt_selection parameter)
            subprompt_positive = ""
            subprompt_negative = ""
            if selection_resolved_prompts is not None:
                subprompt_positive = selection_resolved_prompts.positive or ""
                subprompt_negative = selection_resolved_prompts.negative or ""

            # Parse merge order and combine accordingly
            order_parts = [part.strip() for part in merge_order.split(",")]
            
            # Build components dict with proper separation
            components = {
                "input": (input_positive, input_negative),
                "textbox": (textbox_positive, textbox_negative),
                "subprompt": (subprompt_positive, subprompt_negative)
            }
            
            # Combine in the specified order
            final_positive_parts = []
            final_negative_parts = []
            
            for component in order_parts:
                if component in components:
                    pos_text, neg_text = components[component]
                    if pos_text and pos_text.strip():
                        final_positive_parts.append(pos_text.strip())
                    if neg_text and neg_text.strip():
                        final_negative_parts.append(neg_text.strip())

            # Join parts with comma separation, removing duplicates
            final_positive = ", ".join(final_positive_parts) if final_positive_parts else ""
            final_negative = ", ".join(final_negative_parts) if final_negative_parts else ""

            # Apply deduplication
            final_positive = self._remove_duplicate_terms(final_positive)
            final_negative = self._remove_duplicate_terms(final_negative)

            # Ensure final values are proper strings (never None)
            final_positive = final_positive if final_positive is not None else ""
            final_negative = final_negative if final_negative is not None else ""

            # Create new combined subprompt
            combined_subprompt = Subprompt(
                name=f"{base_subprompt.name}_combined",
                positive=final_positive,
                negative=final_negative,
                trigger_words=base_subprompt.get_trigger_words(),
                order=["attached"],  # Simplified for combined results
            )

            return (combined_subprompt, final_positive, final_negative)

        except Exception as e:
            logger.error(f"Error in add_subprompt: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Ensure we return proper string values in error case
            fallback_positive = str(positive or "")
            fallback_negative = str(negative or "")

            fallback = Subprompt(
                name="error_fallback",
                positive=fallback_positive,
                negative=fallback_negative,
                order=["attached"],
            )
            return (fallback, fallback_positive, fallback_negative)

    @classmethod
    def _remove_duplicate_terms(cls, text: str) -> str:
        """
        Remove duplicate terms from a comma-separated string, preserving order.
        Matches JavaScript removeDuplicateTerms logic.
        """
        if not text or not text.strip():
            return text

        # Split by comma, trim whitespace, and filter out empty terms
        terms = [term.strip() for term in text.split(",") if term.strip()]

        # Use set to track seen terms (case-insensitive) and list to preserve order
        seen = set()
        unique_terms = []

        for term in terms:
            lower_term = term.lower()
            if lower_term not in seen:
                seen.add(lower_term)
                unique_terms.append(term)  # Keep original case

        return ", ".join(unique_terms)


class PromptCompanionSubpromptToStringsNode:
    """
    Node for converting a subprompt object to positive and negative text strings.

    This node resolves all nested references and returns the final text strings
    that can be used with standard ComfyUI text encode nodes.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "subprompt": (
                    "*",
                    {"tooltip": "The subprompt object to convert to text strings"},
                )
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "subprompt_to_strings"
    CATEGORY = "prompt-companion"

    DESCRIPTION = (
        "Convert a subprompt object to resolved positive and negative text strings."
    )

    def subprompt_to_strings(self, subprompt: Subprompt) -> Tuple[str, str]:
        """
        Convert subprompt to resolved text strings.

        Args:
            subprompt: The subprompt object to convert

        Returns:
            Tuple of (positive_text, negative_text)
        """
        try:
            if subprompt is None:
                return ("", "")

            # For simple subprompts with just attached content, return directly
            if subprompt.order == ["attached"]:
                return (subprompt.positive or "", subprompt.negative or "")

            # For complex subprompts with nested references, resolve them
            try:
                from ..core.storage import get_global_storage

                storage = get_global_storage()

                if storage:
                    # Load all subprompts for nested resolution
                    all_subprompts_list = storage.load_all_subprompts()
                    # Convert to dict format for compatibility with resolve_nested method
                    all_subprompts = {sp.name: sp for sp in all_subprompts_list}
                    # Resolve nested references
                    resolved = subprompt.resolve_nested(all_subprompts)
                    # Apply deduplication like JavaScript does
                    return (
                        PromptCompanionAddSubpromptNode._remove_duplicate_terms(
                            resolved.positive or ""
                        ),
                        PromptCompanionAddSubpromptNode._remove_duplicate_terms(
                            resolved.negative or ""
                        ),
                    )
                else:
                    # Fallback to direct content if no storage
                    return (subprompt.positive or "", subprompt.negative or "")

            except Exception as nested_error:
                logger.warning(
                    f"Failed to resolve nested subprompts in subprompt_to_strings: {nested_error}"
                )
                # Fallback to direct content
                return (subprompt.positive or "", subprompt.negative or "")

        except Exception as e:
            logger.error(f"Error converting subprompt to strings: {e}")
            return ("", "")


class PromptCompanionStringsToSubpromptNode:
    """
    Node for creating a subprompt object from positive and negative text strings.

    This is useful for converting standard text prompts into subprompt objects
    that can be used with other prompt companion nodes.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Positive prompt text to convert to subprompt",
                    },
                ),
                "negative": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Negative prompt text to convert to subprompt",
                    },
                ),
            }
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("subprompt",)
    FUNCTION = "strings_to_subprompt"
    CATEGORY = "prompt-companion"

    DESCRIPTION = "Create a subprompt object from positive and negative text strings."

    def strings_to_subprompt(
        self, positive: str = "", negative: str = ""
    ) -> Tuple[Subprompt]:
        """
        Create subprompt from text strings.

        Args:
            positive: Positive prompt text
            negative: Negative prompt text

        Returns:
            Tuple containing the created subprompt object
        """
        try:
            # Create a basic subprompt from the provided text
            subprompt = Subprompt(
                name="from_strings",
                positive=positive or "",
                negative=negative or "",
                trigger_words=[],
                order=["attached"],
            )

            return (subprompt,)

        except Exception as e:
            logger.error(f"Error creating subprompt from strings: {e}")
            # Return minimal fallback
            fallback = Subprompt(
                name="error_fallback", positive="", negative="", order=["attached"]
            )
            return (fallback,)


# Node class mappings for ComfyUI registration
NODE_CLASS_MAPPINGS = {
    "PromptCompanion_AddSubprompt": PromptCompanionAddSubpromptNode,
    "PromptCompanion_SubpromptToStrings": PromptCompanionSubpromptToStringsNode,
    "PromptCompanion_StringsToSubprompt": PromptCompanionStringsToSubpromptNode,
}

# Display name mappings for ComfyUI interface
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptCompanion_AddSubprompt": "Prompt Companion: Add Subprompt",
    "PromptCompanion_SubpromptToStrings": "Prompt Companion: Subprompt to Strings",
    "PromptCompanion_StringsToSubprompt": "Prompt Companion: Strings to Subprompt",
}