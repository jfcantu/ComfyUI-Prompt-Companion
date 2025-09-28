"""
Node modules for ComfyUI-Prompt-Companion

This package contains all the ComfyUI node implementations for the prompt companion system:
- prompt_nodes: Core prompt manipulation and template nodes
- checkpoint_loader: Integration nodes for checkpoint loading with prompt companions

All node classes are imported and registered with ComfyUI through this module.
"""

import logging

logger = logging.getLogger(__name__)

# Import all node classes from the individual modules
try:
    from .prompt_nodes import (
        PromptCompanionAddSubpromptNode,
        PromptCompanionSubpromptToStringsNode,
        PromptCompanionStringsToSubpromptNode,
        NODE_CLASS_MAPPINGS as PROMPT_NODE_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS as PROMPT_DISPLAY_MAPPINGS,
    )
except Exception as e:
    logger.error(f"Failed to import prompt nodes: {e}")
    raise

try:
    from .checkpoint_loader import (
        PromptCompanionLoadCheckpointWithSubpromptNode,
        NODE_CLASS_MAPPINGS as CHECKPOINT_NODE_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS as CHECKPOINT_DISPLAY_MAPPINGS,
    )
except Exception as e:
    logger.error(f"Failed to import checkpoint loader nodes: {e}")
    raise

# Combine all node class mappings for ComfyUI registration
NODE_CLASS_MAPPINGS = {
    **PROMPT_NODE_MAPPINGS,
    **CHECKPOINT_NODE_MAPPINGS,
}

# Combine all display name mappings for ComfyUI interface
NODE_DISPLAY_NAME_MAPPINGS = {
    **PROMPT_DISPLAY_MAPPINGS,
    **CHECKPOINT_DISPLAY_MAPPINGS,
}

# Validate that all expected nodes are present
EXPECTED_NODES = [
    "PromptCompanion_AddSubprompt",
    "PromptCompanion_SubpromptToStrings",
    "PromptCompanion_StringsToSubprompt",
    "PromptCompanion_LoadCheckpointWithSubprompt"
]

missing_nodes = []
for node_id in EXPECTED_NODES:
    if node_id not in NODE_CLASS_MAPPINGS:
        missing_nodes.append(node_id)

if missing_nodes:
    logger.error(f"Missing expected node mappings: {missing_nodes}")
    raise ImportError(f"Missing expected node mappings: {missing_nodes}")

# Export all node classes for direct import if needed
__all__ = [
    # Individual node classes
    "PromptCompanionAddSubpromptNode",
    "PromptCompanionSubpromptToStringsNode",
    "PromptCompanionStringsToSubpromptNode",
    "PromptCompanionLoadCheckpointWithSubpromptNode",
    
    # Registration mappings
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
]