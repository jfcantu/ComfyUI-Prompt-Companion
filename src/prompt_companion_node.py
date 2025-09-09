"""
ComfyUI Node Implementation for Prompt Companion

This module contains the main PromptCompanion node class that handles
prompt combination logic for the ComfyUI interface.
"""

from typing import Tuple, Dict, Any, List, Optional

try:
    import folder_paths
    from extension_config import PROMPT_ADDITIONS
except ImportError:
    # Running outside ComfyUI - use mock values
    folder_paths = None
    PROMPT_ADDITIONS = None


class PromptAdditionInput:
    """Custom data type for prompt addition input with positive and negative fields."""
    
    def __init__(self, positive_prompt_addition: str = "", negative_prompt_addition: str = ""):
        self.positive_prompt_addition = positive_prompt_addition
        self.negative_prompt_addition = negative_prompt_addition
    
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "combine_mode": (
                    ["prepend", "append"], 
                    {
                        "default": "prepend",
                        "tooltip": "Whether to combine input addition before (prepend) or after (append) the current additions."
                    }
                ),
                "positive_prompt_addition": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Positive prompt addition text"
                }),
                "negative_prompt_addition": ("STRING", {
                    "multiline": True, 
                    "default": "",
                    "tooltip": "Negative prompt addition text"
                }),
            },
            "optional": {
                "prompt_addition": (
                    "PROMPT_ADDITION",
                    {
                        "tooltip": "Optional prompt addition input to combine with the current additions."
                    }
                ),
            }
        }
    
    RETURN_TYPES = ("PROMPT_ADDITION", "STRING", "STRING")
    RETURN_NAMES = ("prompt_addition", "positive_prompt", "negative_prompt")
    OUTPUT_TOOLTIPS = ("Prompt addition data that can be connected to other nodes", "Positive prompt text", "Negative prompt text")
    FUNCTION = "create_prompt_addition"
    CATEGORY = "jfc"
    
    def create_prompt_addition(self, combine_mode: str, positive_prompt_addition: str, negative_prompt_addition: str, prompt_addition: Optional['PromptAdditionInput'] = None) -> Tuple['PromptAdditionInput', str, str]:
        # Get the input values
        input_positive = ""
        input_negative = ""
        
        if prompt_addition:
            input_positive = prompt_addition.positive_prompt_addition or ""
            input_negative = prompt_addition.negative_prompt_addition or ""
        
        # Combine the values based on combine_mode
        final_positive = ""
        final_negative = ""
        
        if combine_mode == "prepend":
            # Input first, then current additions
            if input_positive and positive_prompt_addition:
                final_positive = f"{input_positive}, {positive_prompt_addition}"
            elif input_positive:
                final_positive = input_positive
            elif positive_prompt_addition:
                final_positive = positive_prompt_addition
                
            if input_negative and negative_prompt_addition:
                final_negative = f"{input_negative}, {negative_prompt_addition}"
            elif input_negative:
                final_negative = input_negative
            elif negative_prompt_addition:
                final_negative = negative_prompt_addition
        else:  # append
            # Current additions first, then input
            if positive_prompt_addition and input_positive:
                final_positive = f"{positive_prompt_addition}, {input_positive}"
            elif positive_prompt_addition:
                final_positive = positive_prompt_addition
            elif input_positive:
                final_positive = input_positive
                
            if negative_prompt_addition and input_negative:
                final_negative = f"{negative_prompt_addition}, {input_negative}"
            elif negative_prompt_addition:
                final_negative = negative_prompt_addition
            elif input_negative:
                final_negative = input_negative
        
        return (PromptAdditionInput(final_positive, final_negative), final_positive, final_negative)


class PromptCompanion:
    """
    ComfyUI node for combining prompts with additions and groups.
    
    This node supports multiple operation modes:
    - Individual: Apply a single prompt addition
    - Group (Manual): Apply all prompts from a selected group
    - Group (Automatic): Apply groups based on trigger word matching
    """
    
    # ComfyUI node metadata - use same type as checkpoint input for compatibility
    RETURN_TYPES = (folder_paths.get_filename_list("checkpoints") if folder_paths else ["test_model.safetensors"], "STRING", "STRING", "STRING", "STRING", "PROMPT_ADDITION")
    RETURN_NAMES = ("ckpt_name", "positive_combined_prompt", "negative_combined_prompt", 
                   "positive_addition", "negative_addition", "prompt_addition")
    OUTPUT_TOOLTIPS = ("Checkpoint filename compatible with Load Checkpoint nodes",
                       "Combined positive prompt with additions applied", 
                       "Combined negative prompt with additions applied",
                       "The positive prompt addition text that was applied",
                       "The negative prompt addition text that was applied",
                       "Prompt addition data that can be connected to other nodes")
    FUNCTION = "combine_prompts"
    OUTPUT_NODE = True
    CATEGORY = "jfc"

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """
        Define the input parameters for the node.
        
        Returns:
            Dictionary containing input type definitions with tooltips
        """
        addition_type_options = ["Individual", "Group"]
        group_mode_options = ["Manual", "Automatic (Trigger Words)"]
        
        return {
            "required": {
                "ckpt_name": (
                    folder_paths.get_filename_list("checkpoints") if folder_paths else ["test_model.safetensors"],
                    {
                        "tooltip": "The checkpoint (model) to use. In Automatic mode, trigger words are matched against this name."
                    }
                ),
                "addition_type": (
                    addition_type_options, 
                    {
                        "default": "Individual",
                        "tooltip": "Choose 'Individual' to apply a single prompt addition, or 'Group' to apply multiple additions together."
                    }
                ),
                "prompt_group_mode": (
                    group_mode_options, 
                    {
                        "default": "Manual",
                        "tooltip": "Only used in Group mode. 'Manual' lets you select a specific group, 'Automatic' applies groups based on checkpoint name matching."
                    }
                ),
                "combine_mode": (
                    ["prepend", "append"], 
                    {
                        "default": "prepend",
                        "tooltip": "Whether to add prompt additions before (prepend) or after (append) your base prompts."
                    }
                ),
                "enable_addition": (
                    "BOOLEAN", 
                    {
                        "default": True,
                        "tooltip": "Toggle to enable or disable prompt additions without removing the node."
                    }
                ),
                "prompt_addition_name": (
                    [""] + (list(PROMPT_ADDITIONS.prompt_additions.keys()) 
                           if PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_additions else []),
                    {
                        "default": "",
                        "tooltip": "Select a prompt addition to apply (Individual mode only)."
                    }
                ),
                "prompt_addition_group": (
                    [""] + ([g.name for g in PROMPT_ADDITIONS.prompt_groups.values()] 
                           if PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_groups else []),
                    {
                        "default": "",
                        "tooltip": "Select a prompt group to apply (Group mode with Manual selection only)."
                    }
                ),
                "positive_addition": (
                    "STRING",
                    {
                        "multiline": True, 
                        "default": "",
                        "tooltip": "Positive prompt additions. Editable in Individual mode, read-only in Group mode."
                    }
                ),
                "negative_addition": (
                    "STRING",
                    {
                        "multiline": True, 
                        "default": "",
                        "tooltip": "Negative prompt additions. Editable in Individual mode, read-only in Group mode."
                    }
                ),
                "positive_prompt": (
                    "STRING",
                    {
                        "multiline": True, 
                        "default": "",
                        "tooltip": "Your base positive prompt. Can be connected from another node or entered directly."
                    }
                ),
                "negative_prompt": (
                    "STRING",
                    {
                        "multiline": True, 
                        "default": "",
                        "tooltip": "Your base negative prompt. Can be connected from another node or entered directly."
                    }
                ),
            },
            "optional": {
                "prompt_addition": (
                    "PROMPT_ADDITION",
                    {
                        "tooltip": "Optional prompt addition input that will be prepended to the final positive/negative additions."
                    }
                ),
            },
        }

    def combine_prompts(
        self,
        ckpt_name: str,
        addition_type: str,
        prompt_group_mode: str,
        combine_mode: str,
        enable_addition: bool,
        prompt_addition_name: str,
        prompt_addition_group: str,
        positive_addition: str,
        negative_addition: str,
        positive_prompt: str,
        negative_prompt: str,
        prompt_addition: Optional[PromptAdditionInput] = None,
    ) -> Tuple[str, str, str, str, str, PromptAdditionInput]:
        """
        Combine base prompts with additions based on the selected mode.
        
        Args:
            ckpt_name: Name of the checkpoint
            addition_type: Individual or Group mode
            prompt_group_mode: Manual or Automatic group selection
            combine_mode: prepend or append additions
            enable_addition: Whether additions are enabled
            prompt_addition_name: Selected individual addition name
            prompt_addition_group: Selected group name
            positive_addition: Positive addition text
            negative_addition: Negative addition text
            positive_prompt: Base positive prompt
            negative_prompt: Base negative prompt
            prompt_addition: Optional PromptAdditionInput to prepend to final additions
            
        Returns:
            Tuple of (ckpt_name, positive_combined, negative_combined, positive_addition, negative_addition, prompt_addition)
        """
        # Validate and ensure ckpt_name is compatible with Load Checkpoint
        validated_ckpt_name = self._validate_checkpoint_name(ckpt_name)
        
        # Always return ckpt_name first
        if not enable_addition:
            return (validated_ckpt_name, positive_prompt, negative_prompt, "", "", PromptAdditionInput("", ""))

        # Calculate addition values based on type
        calculated_positive_addition = ""
        calculated_negative_addition = ""

        if addition_type == "Individual":
            calculated_positive_addition, calculated_negative_addition = self._get_individual_additions(
                prompt_addition_name, positive_addition, negative_addition
            )
        elif addition_type == "Group":
            calculated_positive_addition, calculated_negative_addition = self._get_group_additions(
                prompt_group_mode, prompt_addition_group, ckpt_name
            )

        # Prepend prompt_addition input values to calculated additions if provided
        if prompt_addition:
            if prompt_addition.positive_prompt_addition:
                if calculated_positive_addition:
                    calculated_positive_addition = f"{prompt_addition.positive_prompt_addition}, {calculated_positive_addition}"
                else:
                    calculated_positive_addition = prompt_addition.positive_prompt_addition
                    
            if prompt_addition.negative_prompt_addition:
                if calculated_negative_addition:
                    calculated_negative_addition = f"{prompt_addition.negative_prompt_addition}, {calculated_negative_addition}"
                else:
                    calculated_negative_addition = prompt_addition.negative_prompt_addition

        # Combine additions with base prompts using combine_mode
        final_positive_combined, final_negative_combined = self._combine_prompts_with_additions(
            positive_prompt, negative_prompt,
            calculated_positive_addition, calculated_negative_addition,
            combine_mode
        )

        # Create PromptAdditionInput output with the calculated additions
        output_prompt_addition = PromptAdditionInput(
            calculated_positive_addition,
            calculated_negative_addition
        )
        
        return (
            validated_ckpt_name,
            final_positive_combined,
            final_negative_combined,
            calculated_positive_addition,
            calculated_negative_addition,
            output_prompt_addition
        )

    def _get_individual_additions(
        self, 
        prompt_addition_name: str, 
        positive_addition: str, 
        negative_addition: str
    ) -> Tuple[str, str]:
        """
        Get prompt additions for Individual mode.
        
        Args:
            prompt_addition_name: Name of the selected addition
            positive_addition: Direct positive addition text
            negative_addition: Direct negative addition text
            
        Returns:
            Tuple of (positive_addition, negative_addition)
        """
        if (prompt_addition_name and PROMPT_ADDITIONS and 
            PROMPT_ADDITIONS.prompt_additions and 
            prompt_addition_name in PROMPT_ADDITIONS.prompt_additions):
            # Use saved addition
            addition = PROMPT_ADDITIONS.prompt_additions[prompt_addition_name]
            return (
                addition.positive_prompt_addition_text or "",
                addition.negative_prompt_addition_text or ""
            )
        else:
            # Use direct input values
            return (positive_addition or "", negative_addition or "")

    def _get_group_additions(
        self, 
        prompt_group_mode: str, 
        prompt_addition_group: str, 
        ckpt_name: str
    ) -> Tuple[str, str]:
        """
        Get prompt additions for Group mode.
        
        Args:
            prompt_group_mode: Manual or Automatic mode
            prompt_addition_group: Selected group name (Manual mode)
            ckpt_name: Checkpoint name for trigger matching (Automatic mode)
            
        Returns:
            Tuple of (combined_positive, combined_negative)
        """
        positive_additions: List[str] = []
        negative_additions: List[str] = []

        if prompt_group_mode == "Manual":
            # Manual mode - use the selected group only
            if prompt_addition_group and PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_groups:
                selected_group = None
                for group in PROMPT_ADDITIONS.prompt_groups.values():
                    if group.name == prompt_addition_group:
                        selected_group = group
                        break
                
                if selected_group:
                    positive_additions, negative_additions = self._collect_group_additions([selected_group])
                    
        else:  # "Automatic (Trigger Words)"
            # Automatic mode - use trigger word matching
            if PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_groups:
                matching_groups = []
                for group in PROMPT_ADDITIONS.prompt_groups.values():
                    if self._group_matches_checkpoint(group, ckpt_name):
                        matching_groups.append(group)
                
                positive_additions, negative_additions = self._collect_group_additions(matching_groups)
            
        # Combine all matching group additions
        return (
            ", ".join(positive_additions),
            ", ".join(negative_additions)
        )

    def _group_matches_checkpoint(self, group, ckpt_name: str) -> bool:
        """
        Check if a group's trigger words match the checkpoint name.
        
        Args:
            group: PromptGroup object
            ckpt_name: Checkpoint name to match against
            
        Returns:
            True if any trigger word matches
        """
        if not hasattr(group, 'trigger_words') or not group.trigger_words:
            return False
            
        ckpt_lower = ckpt_name.lower()
        for trigger_word in group.trigger_words:
            if trigger_word and trigger_word.lower() in ckpt_lower:
                return True
        return False

    def _collect_group_additions(self, groups) -> Tuple[List[str], List[str]]:
        """
        Collect all prompt additions from the given groups.
        
        Args:
            groups: List of PromptGroup objects
            
        Returns:
            Tuple of (positive_additions_list, negative_additions_list)
        """
        positive_additions: List[str] = []
        negative_additions: List[str] = []
        
        for group in groups:
            if hasattr(group, 'additions') and group.additions:
                for addition_ref in group.additions:
                    addition_id = addition_ref.get('addition_id')
                    if addition_id and PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_additions:
                        for addition in PROMPT_ADDITIONS.prompt_additions.values():
                            if addition.id == addition_id:
                                if addition.positive_prompt_addition_text:
                                    positive_additions.append(addition.positive_prompt_addition_text)
                                if addition.negative_prompt_addition_text:
                                    negative_additions.append(addition.negative_prompt_addition_text)
                                break
        
        return positive_additions, negative_additions

    def _combine_prompts_with_additions(
        self,
        positive_prompt: str,
        negative_prompt: str,
        positive_addition: str,
        negative_addition: str,
        combine_mode: str
    ) -> Tuple[str, str]:
        """
        Combine base prompts with additions using the specified mode.
        
        Args:
            positive_prompt: Base positive prompt
            negative_prompt: Base negative prompt
            positive_addition: Positive addition text
            negative_addition: Negative addition text
            combine_mode: 'prepend' or 'append'
            
        Returns:
            Tuple of (combined_positive, combined_negative)
        """
        final_positive = positive_prompt
        final_negative = negative_prompt
        
        if positive_addition:
            if combine_mode == "prepend":
                final_positive = f"{positive_addition}, {positive_prompt}" if positive_prompt else positive_addition
            else:  # append
                final_positive = f"{positive_prompt}, {positive_addition}" if positive_prompt else positive_addition
        
        if negative_addition:
            if combine_mode == "prepend":
                final_negative = f"{negative_addition}, {negative_prompt}" if negative_prompt else negative_addition
            else:  # append
                final_negative = f"{negative_prompt}, {negative_addition}" if negative_prompt else negative_addition
        
        return final_positive, final_negative

    def _validate_checkpoint_name(self, ckpt_name: str) -> str:
        """
        Validate that the checkpoint name is in the available checkpoints list.
        This ensures compatibility with Load Checkpoint nodes.
        
        Args:
            ckpt_name: The checkpoint name to validate
            
        Returns:
            The validated checkpoint name, or the first available if invalid
        """
        if not folder_paths:
            # Fallback for testing environments
            return ckpt_name or "test_model.safetensors"
            
        available_checkpoints = folder_paths.get_filename_list("checkpoints")
        
        if not available_checkpoints:
            # No checkpoints available, return as-is
            return ckpt_name
            
        if ckpt_name in available_checkpoints:
            # Valid checkpoint name
            return ckpt_name
        else:
            # Invalid checkpoint name, return the first available one
            return available_checkpoints[0]


class PromptCompanionSingleAddition:
    """
    ComfyUI node for applying a single prompt addition with optional chaining.
    
    Allows selection of a single prompt addition and optional input chaining.
    """
    
    # ComfyUI node metadata
    RETURN_TYPES = ("PROMPT_ADDITION", "STRING", "STRING")
    RETURN_NAMES = ("prompt_addition", "positive_prompt", "negative_prompt")
    OUTPUT_TOOLTIPS = ("Prompt addition data that can be connected to other nodes", "Positive prompt text", "Negative prompt text")
    FUNCTION = "apply_single_addition"
    CATEGORY = "jfc"

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define the input parameters for the single addition node."""
        return {
            "required": {
                "combine_mode": (
                    ["prepend", "append"], 
                    {
                        "default": "prepend",
                        "tooltip": "Whether to combine input addition before (prepend) or after (append) the selected addition."
                    }
                ),
                "prompt_addition_name": (
                    [""] + (list(PROMPT_ADDITIONS.prompt_additions.keys()) 
                           if PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_additions else []),
                    {
                        "default": "",
                        "tooltip": "Select a prompt addition to apply."
                    }
                ),
            },
            "optional": {
                "prompt_addition": (
                    "PROMPT_ADDITION",
                    {
                        "tooltip": "Optional prompt addition input to combine with the selected addition."
                    }
                ),
            },
        }

    def apply_single_addition(
        self,
        combine_mode: str,
        prompt_addition_name: str,
        prompt_addition: Optional[PromptAdditionInput] = None,
    ) -> Tuple['PromptAdditionInput', str, str]:
        """Apply the selected prompt addition with optional input combination."""
        
        # Get the selected addition
        selected_positive = ""
        selected_negative = ""
        
        if (prompt_addition_name and PROMPT_ADDITIONS and 
            PROMPT_ADDITIONS.prompt_additions and 
            prompt_addition_name in PROMPT_ADDITIONS.prompt_additions):
            addition = PROMPT_ADDITIONS.prompt_additions[prompt_addition_name]
            selected_positive = addition.positive_prompt_addition_text or ""
            selected_negative = addition.negative_prompt_addition_text or ""
        
        # Get input values
        input_positive = ""
        input_negative = ""
        
        if prompt_addition:
            input_positive = prompt_addition.positive_prompt_addition or ""
            input_negative = prompt_addition.negative_prompt_addition or ""
        
        # Combine based on combine_mode
        final_positive = ""
        final_negative = ""
        
        if combine_mode == "prepend":
            # Input first, then selected addition
            if input_positive and selected_positive:
                final_positive = f"{input_positive}, {selected_positive}"
            elif input_positive:
                final_positive = input_positive
            elif selected_positive:
                final_positive = selected_positive
                
            if input_negative and selected_negative:
                final_negative = f"{input_negative}, {selected_negative}"
            elif input_negative:
                final_negative = input_negative
            elif selected_negative:
                final_negative = selected_negative
        else:  # append
            # Selected addition first, then input
            if selected_positive and input_positive:
                final_positive = f"{selected_positive}, {input_positive}"
            elif selected_positive:
                final_positive = selected_positive
            elif input_positive:
                final_positive = input_positive
                
            if selected_negative and input_negative:
                final_negative = f"{selected_negative}, {input_negative}"
            elif selected_negative:
                final_negative = selected_negative
            elif input_negative:
                final_negative = input_negative
        
        return (PromptAdditionInput(final_positive, final_negative), final_positive, final_negative)


class PromptCompanionPromptGroup:
    """
    ComfyUI node for applying a single prompt group with optional chaining.
    
    Allows selection of a single prompt group and optional input chaining.
    """
    
    # ComfyUI node metadata
    RETURN_TYPES = ("PROMPT_ADDITION", "STRING", "STRING")
    RETURN_NAMES = ("prompt_addition", "positive_prompt", "negative_prompt")
    OUTPUT_TOOLTIPS = ("Prompt addition data that can be connected to other nodes", "Positive prompt text", "Negative prompt text")
    FUNCTION = "apply_prompt_group"
    CATEGORY = "jfc"

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define the input parameters for the prompt group node."""
        return {
            "required": {
                "combine_mode": (
                    ["prepend", "append"], 
                    {
                        "default": "prepend",
                        "tooltip": "Whether to combine input addition before (prepend) or after (append) the group additions."
                    }
                ),
                "prompt_addition_group": (
                    [""] + ([g.name for g in PROMPT_ADDITIONS.prompt_groups.values()] 
                           if PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_groups else []),
                    {
                        "default": "",
                        "tooltip": "Select a prompt group to apply."
                    }
                ),
            },
            "optional": {
                "prompt_addition": (
                    "PROMPT_ADDITION",
                    {
                        "tooltip": "Optional prompt addition input to combine with the group additions."
                    }
                ),
            },
        }

    def apply_prompt_group(
        self,
        combine_mode: str,
        prompt_addition_group: str,
        prompt_addition: Optional[PromptAdditionInput] = None,
    ) -> Tuple['PromptAdditionInput', str, str]:
        """Apply the selected prompt group with optional input combination."""
        
        # Get the group additions
        group_positive = ""
        group_negative = ""
        
        if prompt_addition_group and PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_groups:
            selected_group = None
            for group in PROMPT_ADDITIONS.prompt_groups.values():
                if group.name == prompt_addition_group:
                    selected_group = group
                    break
            
            if selected_group:
                positive_additions, negative_additions = self._collect_group_additions([selected_group])
                group_positive = ", ".join(positive_additions)
                group_negative = ", ".join(negative_additions)
        
        # Get input values
        input_positive = ""
        input_negative = ""
        
        if prompt_addition:
            input_positive = prompt_addition.positive_prompt_addition or ""
            input_negative = prompt_addition.negative_prompt_addition or ""
        
        # Combine based on combine_mode
        final_positive = ""
        final_negative = ""
        
        if combine_mode == "prepend":
            # Input first, then group additions
            if input_positive and group_positive:
                final_positive = f"{input_positive}, {group_positive}"
            elif input_positive:
                final_positive = input_positive
            elif group_positive:
                final_positive = group_positive
                
            if input_negative and group_negative:
                final_negative = f"{input_negative}, {group_negative}"
            elif input_negative:
                final_negative = input_negative
            elif group_negative:
                final_negative = group_negative
        else:  # append
            # Group additions first, then input
            if group_positive and input_positive:
                final_positive = f"{group_positive}, {input_positive}"
            elif group_positive:
                final_positive = group_positive
            elif input_positive:
                final_positive = input_positive
                
            if group_negative and input_negative:
                final_negative = f"{group_negative}, {input_negative}"
            elif group_negative:
                final_negative = group_negative
            elif input_negative:
                final_negative = input_negative
        
        return (PromptAdditionInput(final_positive, final_negative), final_positive, final_negative)

    def _collect_group_additions(self, groups) -> Tuple[List[str], List[str]]:
        """Collect all prompt additions from the given groups."""
        positive_additions: List[str] = []
        negative_additions: List[str] = []
        
        for group in groups:
            if hasattr(group, 'additions') and group.additions:
                for addition_ref in group.additions:
                    addition_id = addition_ref.get('addition_id')
                    if addition_id and PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_additions:
                        for addition in PROMPT_ADDITIONS.prompt_additions.values():
                            if addition.id == addition_id:
                                if addition.positive_prompt_addition_text:
                                    positive_additions.append(addition.positive_prompt_addition_text)
                                if addition.negative_prompt_addition_text:
                                    negative_additions.append(addition.negative_prompt_addition_text)
                                break
        
        return positive_additions, negative_additions


class PromptCompanionAutoselectGroups:
    """
    ComfyUI node for auto-selecting prompt groups based on checkpoint trigger words.
    
    Automatically selects prompt groups whose trigger words match the checkpoint name.
    """
    
    # ComfyUI node metadata
    RETURN_TYPES = (folder_paths.get_filename_list("checkpoints") if folder_paths else ["test_model.safetensors"], "PROMPT_ADDITION")
    RETURN_NAMES = ("ckpt_name", "prompt_addition")
    OUTPUT_TOOLTIPS = ("Validated checkpoint name", "Prompt addition data that can be connected to other nodes")
    FUNCTION = "autoselect_groups"
    CATEGORY = "jfc"

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define the input parameters for the autoselect groups node."""
        return {
            "required": {
                "combine_mode": (
                    ["prepend", "append"], 
                    {
                        "default": "prepend",
                        "tooltip": "Whether to combine input addition before (prepend) or after (append) the auto-selected group additions."
                    }
                ),
                "ckpt_name": (
                    folder_paths.get_filename_list("checkpoints") if folder_paths else ["test_model.safetensors"],
                    {
                        "tooltip": "The checkpoint (model) to use for trigger word matching."
                    }
                ),
            },
            "optional": {
                "prompt_addition": (
                    "PROMPT_ADDITION",
                    {
                        "tooltip": "Optional prompt addition input to combine with the auto-selected group additions."
                    }
                ),
            },
        }

    def autoselect_groups(
        self,
        combine_mode: str,
        ckpt_name: str,
        prompt_addition: Optional[PromptAdditionInput] = None,
    ) -> Tuple[str, 'PromptAdditionInput']:
        """Auto-select prompt groups based on checkpoint trigger words."""
        
        # Find matching groups based on trigger words
        matching_groups = []
        if PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_groups:
            for group in PROMPT_ADDITIONS.prompt_groups.values():
                if self._group_matches_checkpoint(group, ckpt_name):
                    matching_groups.append(group)
        
        # Collect additions from matching groups
        group_positive = ""
        group_negative = ""
        
        if matching_groups:
            positive_additions, negative_additions = self._collect_group_additions(matching_groups)
            group_positive = ", ".join(positive_additions)
            group_negative = ", ".join(negative_additions)
        
        # Get input values
        input_positive = ""
        input_negative = ""
        
        if prompt_addition:
            input_positive = prompt_addition.positive_prompt_addition or ""
            input_negative = prompt_addition.negative_prompt_addition or ""
        
        # Combine based on combine_mode
        final_positive = ""
        final_negative = ""
        
        if combine_mode == "prepend":
            # Input first, then group additions
            if input_positive and group_positive:
                final_positive = f"{input_positive}, {group_positive}"
            elif input_positive:
                final_positive = input_positive
            elif group_positive:
                final_positive = group_positive
                
            if input_negative and group_negative:
                final_negative = f"{input_negative}, {group_negative}"
            elif input_negative:
                final_negative = input_negative
            elif group_negative:
                final_negative = group_negative
        else:  # append
            # Group additions first, then input
            if group_positive and input_positive:
                final_positive = f"{group_positive}, {input_positive}"
            elif group_positive:
                final_positive = group_positive
            elif input_positive:
                final_positive = input_positive
                
            if group_negative and input_negative:
                final_negative = f"{group_negative}, {input_negative}"
            elif group_negative:
                final_negative = group_negative
            elif input_negative:
                final_negative = input_negative
        
        # Validate and ensure ckpt_name is compatible with Load Checkpoint
        validated_ckpt_name = self._validate_checkpoint_name(ckpt_name)
        
        return (validated_ckpt_name, PromptAdditionInput(final_positive, final_negative))

    def _validate_checkpoint_name(self, ckpt_name: str) -> str:
        """
        Validate that the checkpoint name is in the available checkpoints list.
        This ensures compatibility with Load Checkpoint nodes.
        
        Args:
            ckpt_name: The checkpoint name to validate
            
        Returns:
            The validated checkpoint name, or the first available if invalid
        """
        if not folder_paths:
            # Fallback for testing environments
            return ckpt_name or "test_model.safetensors"
            
        available_checkpoints = folder_paths.get_filename_list("checkpoints")
        
        if not available_checkpoints:
            # No checkpoints available, return as-is
            return ckpt_name
            
        if ckpt_name in available_checkpoints:
            # Valid checkpoint name
            return ckpt_name
        else:
            # Invalid checkpoint name, return the first available one
            return available_checkpoints[0]

    def _group_matches_checkpoint(self, group, ckpt_name: str) -> bool:
        """Check if a group's trigger words match the checkpoint name."""
        if not hasattr(group, 'trigger_words') or not group.trigger_words:
            return False
            
        ckpt_lower = ckpt_name.lower()
        for trigger_word in group.trigger_words:
            if trigger_word and trigger_word.lower() in ckpt_lower:
                return True
        return False

    def _collect_group_additions(self, groups) -> Tuple[List[str], List[str]]:
        """Collect all prompt additions from the given groups."""
        positive_additions: List[str] = []
        negative_additions: List[str] = []
        
        for group in groups:
            if hasattr(group, 'additions') and group.additions:
                for addition_ref in group.additions:
                    addition_id = addition_ref.get('addition_id')
                    if addition_id and PROMPT_ADDITIONS and PROMPT_ADDITIONS.prompt_additions:
                        for addition in PROMPT_ADDITIONS.prompt_additions.values():
                            if addition.id == addition_id:
                                if addition.positive_prompt_addition_text:
                                    positive_additions.append(addition.positive_prompt_addition_text)
                                if addition.negative_prompt_addition_text:
                                    negative_additions.append(addition.negative_prompt_addition_text)
                                break
        
        return positive_additions, negative_additions


class PromptCompanionStringsToAddition:
    """
    Simple utility node to convert two strings into a prompt addition.
    
    Takes positive and negative prompt strings and creates a PROMPT_ADDITION output.
    """
    
    # ComfyUI node metadata
    RETURN_TYPES = ("PROMPT_ADDITION", "STRING", "STRING")
    RETURN_NAMES = ("prompt_addition", "positive_prompt", "negative_prompt")
    OUTPUT_TOOLTIPS = ("Prompt addition created from the input strings", "Positive prompt text", "Negative prompt text")
    FUNCTION = "strings_to_addition"
    CATEGORY = "jfc"

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define the input parameters for string to addition conversion."""
        return {
            "required": {
                "positive_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Positive prompt text to convert to prompt addition format"
                    }
                ),
                "negative_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Negative prompt text to convert to prompt addition format"
                    }
                ),
            },
        }

    def strings_to_addition(
        self,
        positive_prompt: str,
        negative_prompt: str,
    ) -> Tuple['PromptAdditionInput', str, str]:
        """Convert positive and negative strings to a prompt addition."""
        return (PromptAdditionInput(positive_prompt, negative_prompt), positive_prompt, negative_prompt)


class PromptCompanionAdditionToStrings:
    """
    Simple utility node to convert a prompt addition back to two strings.
    
    Takes a PROMPT_ADDITION input and outputs positive and negative prompt strings.
    """
    
    # ComfyUI node metadata
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt")
    OUTPUT_TOOLTIPS = ("Positive prompt text extracted from the prompt addition",
                       "Negative prompt text extracted from the prompt addition")
    FUNCTION = "addition_to_strings"
    CATEGORY = "jfc"

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define the input parameters for addition to string conversion."""
        return {
            "required": {
                "prompt_addition": (
                    "PROMPT_ADDITION",
                    {
                        "tooltip": "Prompt addition to convert back to separate strings"
                    }
                ),
            },
        }

    def addition_to_strings(
        self,
        prompt_addition: PromptAdditionInput,
    ) -> Tuple[str, str]:
        """Convert a prompt addition to positive and negative strings."""
        positive = prompt_addition.positive_prompt_addition if prompt_addition else ""
        negative = prompt_addition.negative_prompt_addition if prompt_addition else ""
        return (positive, negative)


# Node registration mapping
NODE_CLASS_MAPPINGS = {
    "PromptCompanion": PromptCompanion,
    "PromptAdditionInput": PromptAdditionInput,
    "PromptCompanionSingleAddition": PromptCompanionSingleAddition,
    "PromptCompanionPromptGroup": PromptCompanionPromptGroup,
    "PromptCompanionAutoselectGroups": PromptCompanionAutoselectGroups,
    "PromptCompanionStringsToAddition": PromptCompanionStringsToAddition,
    "PromptCompanionAdditionToStrings": PromptCompanionAdditionToStrings
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptCompanion": "Prompt Companion: All-In-One",
    "PromptAdditionInput": "Prompt Companion: Create Prompt Addition",
    "PromptCompanionSingleAddition": "Prompt Companion: Single Prompt Addition",
    "PromptCompanionPromptGroup": "Prompt Companion: Prompt Group",
    "PromptCompanionAutoselectGroups": "Prompt Companion: Autoselect Prompt Groups",
    "PromptCompanionStringsToAddition": "Prompt Companion: Prompt Strings to Prompt Addition",
    "PromptCompanionAdditionToStrings": "Prompt Companion: Prompt Addition to Prompt Strings"
}
