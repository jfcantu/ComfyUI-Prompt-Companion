"""
Checkpoint Loading Integration Nodes for ComfyUI-Prompt-Companion

This module contains nodes that integrate checkpoint loading with prompt companion functionality:
- PromptCompanionLoadCheckpointWithSubpromptNode: Enhanced checkpoint loader with explicit trigger word matching

Features:
- Subprompt matching based on explicitly configured trigger words
- Integration with ComfyUI's existing checkpoint loading system
- Support for checkpoint-prompt associations via mapping files
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any

# Import ComfyUI functionality
import folder_paths
import comfy.sd
from comfy.comfy_types import IO

# Import core functionality
from ..core.subprompt import Subprompt, ResolvedPrompts, SubpromptError, ValidationError

logger = logging.getLogger(__name__)


class PromptCompanionLoadCheckpointWithSubpromptNode:
    """
    Enhanced checkpoint loader that finds matching subprompts based on explicit trigger words.
    
    This node:
    - Loads a checkpoint like the standard CheckpointLoaderSimple
    - Finds and combines subprompts whose explicitly configured trigger words match the checkpoint
    - Returns the standard model/clip/vae outputs plus a combined subprompt
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ckpt_name": (folder_paths.get_filename_list("checkpoints"), {
                    "tooltip": "The name of the checkpoint (model) to load."
                }),
            }
        }
    
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "*")
    RETURN_NAMES = ("model", "clip", "vae", "subprompt")
    OUTPUT_TOOLTIPS = (
        "The model used for denoising latents.",
        "The CLIP model used for encoding text prompts.", 
        "The VAE model used for encoding and decoding images to and from latent space.",
        "Combined subprompt from explicitly matching trigger words for this checkpoint."
    )
    FUNCTION = "load_checkpoint_with_subprompt"
    CATEGORY = "prompt-companion/loaders"
    
    DESCRIPTION = "Loads a diffusion model checkpoint and finds matching subprompts based on explicitly configured trigger word associations."
    
    @classmethod
    def _get_checkpoint_trigger_words(cls, ckpt_name: str) -> List[str]:
        """
        Get trigger words from checkpoint-specific mappings file.
        
        This method looks for explicitly configured trigger word mappings
        for the checkpoint. No automatic extraction or fallback logic.
        
        Args:
            ckpt_name: Name of the checkpoint file
            
        Returns:
            List of explicitly configured trigger words for this checkpoint
        """
        trigger_words = []
        
        try:
            # Extract base name without extension
            base_name = os.path.splitext(ckpt_name)[0].lower()
            
            # Look for trigger word mappings file
            mappings_path = os.path.join(os.path.dirname(__file__), '..', 'checkpoint_mappings.json')
            
            if os.path.exists(mappings_path):
                with open(mappings_path, 'r', encoding='utf-8') as f:
                    mappings = json.load(f)
                    
                # Check for exact match first
                if base_name in mappings:
                    trigger_words.extend(mappings[base_name])
                else:
                    # Check for partial matches in the filename
                    for mapping_key, words in mappings.items():
                        if mapping_key in base_name or base_name in mapping_key:
                            trigger_words.extend(words)
                
        except Exception as e:
            logger.warning(f"Failed to get trigger words for checkpoint '{ckpt_name}': {e}")
        
        return list(set(trigger_words))  # Remove duplicates
    
    
    @classmethod
    def _find_matching_subprompts(cls, ckpt_name: str) -> List[Subprompt]:
        """
        Find subprompts whose explicitly configured trigger words appear in the checkpoint name.
        Only matches on trigger words that are explicitly set in subprompts.
        
        Args:
            ckpt_name: The checkpoint filename to check against
            
        Returns:
            List of matching subprompt objects
        """
        matching_subprompts = []
        
        try:
            # Import storage system using correct function
            from ..core.storage import get_global_storage
            storage = get_global_storage()
            
            # Load all available subprompts from storage (returns Subprompt objects, not dictionaries)
            all_subprompts = storage.load_all_subprompts()
            
            # Convert checkpoint name to lowercase for case-insensitive matching
            ckpt_name_lower = ckpt_name.lower()
            
            # Remove common file extensions and separators for better matching
            ckpt_base_name = ckpt_name_lower.replace('.safetensors', '').replace('.ckpt', '').replace('.pt', '')
            ckpt_base_name = ckpt_base_name.replace('_', ' ').replace('-', ' ')
            
            # Iterate through Subprompt objects directly (storage returns List[Subprompt], not dict)
            for subprompt in all_subprompts:
                try:
                    match_found = False
                    match_reason = ""
                    
                    # Get trigger words directly from the Subprompt object
                    trigger_words = subprompt.trigger_words or []
                    subprompt_name = getattr(subprompt, 'name', getattr(subprompt, 'id', 'unknown'))
                    
                    # Skip subprompts with no trigger words
                    if not trigger_words or not any(tw.strip() for tw in trigger_words):
                        continue
                    
                    # Only match on explicit trigger words
                    for trigger_word in trigger_words:
                        trigger_word_lower = trigger_word.lower().strip()
                        
                        if trigger_word_lower and trigger_word_lower in ckpt_name_lower:
                            match_found = True
                            match_reason = f"trigger word '{trigger_word}'"
                            break
                    
                    if match_found:
                        # Clone the subprompt with safe defaults for any missing data
                        matching_subprompt = Subprompt(
                            name=getattr(subprompt, 'name', getattr(subprompt, 'id', 'unknown')),  # Use name, fallback to legacy id
                            positive=getattr(subprompt, 'positive', ''),  # Empty string if missing
                            negative=getattr(subprompt, 'negative', ''),  # Empty string if missing
                            trigger_words=getattr(subprompt, 'trigger_words', []),  # Empty list if missing
                            order=getattr(subprompt, 'order', ['attached']),  # Default order if missing
                            folder_path=getattr(subprompt, 'folder_path', '')  # Empty string if missing
                        )
                        
                        # Copy nested subprompts if they exist, with safe default
                        if hasattr(subprompt, 'nested_subprompts'):
                            matching_subprompt.nested_subprompts = getattr(subprompt, 'nested_subprompts', [])
                        else:
                            matching_subprompt.nested_subprompts = []
                        
                        matching_subprompts.append(matching_subprompt)
                        folder_display = getattr(subprompt, 'folder_path', '') or 'root'
                        subprompt_name = getattr(subprompt, 'name', getattr(subprompt, 'id', 'unknown'))
                    
                except Exception as e:
                    logger.warning(f"Failed to process subprompt '{getattr(subprompt, 'name', 'unknown')}': {e}")
                    continue
            
            if not matching_subprompts:
                pass
        
        except Exception as e:
            logger.error(f"Failed to find matching subprompts: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        return matching_subprompts
    
    @classmethod
    def _combine_matching_subprompts(cls, subprompts: List[Subprompt], checkpoint_name: str) -> Subprompt:
        """
        Combine multiple matching subprompts into a single result.
        
        Args:
            subprompts: List of subprompts to combine
            checkpoint_name: Name of the checkpoint for the combined subprompt ID
            
        Returns:
            Combined subprompt object, or empty subprompt if no matches
        """
        if not subprompts:
            # Return empty subprompt - no automatic extraction
            return Subprompt(
                name=f"auto_{os.path.splitext(checkpoint_name)[0]}",
                positive="",
                negative="",
                trigger_words=[],
                order=["attached"]
            )
        
        if len(subprompts) == 1:
            # Single subprompt, just return it with updated name
            subprompt = subprompts[0]
            return Subprompt(
                name=f"auto_{os.path.splitext(checkpoint_name)[0]}_{subprompt.name}",
                positive=subprompt.positive,
                negative=subprompt.negative,
                trigger_words=subprompt.get_trigger_words(),
                order=subprompt.order
            )
        
        # Multiple subprompts - combine them
        combined_positive_parts = []
        combined_negative_parts = []
        all_trigger_words = []
        
        for subprompt in subprompts:
            if subprompt.positive.strip():
                combined_positive_parts.append(subprompt.positive.strip())
            if subprompt.negative.strip():
                combined_negative_parts.append(subprompt.negative.strip())
            all_trigger_words.extend(subprompt.get_trigger_words())
        
        # Clean and join parts
        combined_positive = ", ".join(combined_positive_parts)
        combined_negative = ", ".join(combined_negative_parts)
        unique_trigger_words = list(set(all_trigger_words))  # Remove duplicates
        
        return Subprompt(
            name=f"auto_{os.path.splitext(checkpoint_name)[0]}_combined",
            positive=combined_positive,
            negative=combined_negative,
            trigger_words=unique_trigger_words,
            order=["attached"]
        )
    
    def load_checkpoint_with_subprompt(self, ckpt_name: str) -> Tuple[Any, Any, Any, Subprompt]:
        """
        Load checkpoint and find matching subprompt based on explicit trigger words.
        
        Args:
            ckpt_name: Name of the checkpoint file to load
            
        Returns:
            Tuple of (model, clip, vae, combined_subprompt)
        """
        try:
            # Load the checkpoint using ComfyUI's standard method
            ckpt_path = folder_paths.get_full_path_or_raise("checkpoints", ckpt_name)
            checkpoint_result = comfy.sd.load_checkpoint_guess_config(
                ckpt_path,
                output_vae=True,
                output_clip=True,
                embedding_directory=folder_paths.get_folder_paths("embeddings")
            )
            # Handle variable number of return values (ComfyUI API compatibility)
            model, clip, vae = checkpoint_result[:3]
            
            # Find matching subprompts by checking explicit trigger words against checkpoint name
            matching_subprompts = self._find_matching_subprompts(ckpt_name)

            for i, subprompt in enumerate(matching_subprompts):
                pass
            
            combined_subprompt = self._combine_matching_subprompts(matching_subprompts, ckpt_name)
            
            
            return (model, clip, vae, combined_subprompt)
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint with subprompt: {e}")
            
            # Try to load just the checkpoint without subprompt generation
            try:
                ckpt_path = folder_paths.get_full_path_or_raise("checkpoints", ckpt_name)
                checkpoint_result = comfy.sd.load_checkpoint_guess_config(
                    ckpt_path, output_vae=True, output_clip=True,
                    embedding_directory=folder_paths.get_folder_paths("embeddings")
                )
                # Handle variable number of return values (ComfyUI API compatibility)
                model, clip, vae = checkpoint_result[:3]
                
                # Fallback subprompt
                fallback_subprompt = Subprompt(
                    name=f"fallback_{os.path.splitext(ckpt_name)[0]}",
                    positive="",
                    negative="",
                    trigger_words=[],
                    order=["attached"]
                )
                
                return (model, clip, vae, fallback_subprompt)
                
            except Exception as e2:
                logger.error(f"Failed to load checkpoint at all: {e2}")
                raise e2


# Node class mappings for ComfyUI registration
NODE_CLASS_MAPPINGS = {
    "PromptCompanion_LoadCheckpointWithSubprompt": PromptCompanionLoadCheckpointWithSubpromptNode,
}

# Display name mappings for ComfyUI interface
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptCompanion_LoadCheckpointWithSubprompt": "Prompt Companion: Load Checkpoint with Subprompt",
}