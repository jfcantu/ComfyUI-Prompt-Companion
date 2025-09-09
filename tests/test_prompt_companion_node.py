"""
Unit tests for PromptCompanion node in ComfyUI Prompt Companion.

This module tests the core node functionality including prompt combination logic,
input validation, and different operation modes (Individual, Group Manual, Group Automatic).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.prompt_companion_node import PromptCompanion
from src.extension_config import PromptAddition, PromptGroup


# Module-level fixtures that can be used by all test classes
@pytest.fixture
def mock_prompt_additions():
    """Mock PROMPT_ADDITIONS with test data."""
    with patch('src.prompt_companion_node.PROMPT_ADDITIONS') as mock:
        # Create mock prompt additions
        mock_addition1 = Mock()
        mock_addition1.id = 1
        mock_addition1.name = "Test Addition 1"
        mock_addition1.positive_prompt_addition_text = "positive1"
        mock_addition1.negative_prompt_addition_text = "negative1"
        
        mock_addition2 = Mock()
        mock_addition2.id = 2
        mock_addition2.name = "Test Addition 2"
        mock_addition2.positive_prompt_addition_text = "positive2"
        mock_addition2.negative_prompt_addition_text = "negative2"
        
        mock.prompt_additions = {
            "Test Addition 1": mock_addition1,
            "Test Addition 2": mock_addition2
        }
        
        # Create mock prompt groups
        mock_group1 = Mock()
        mock_group1.id = 1
        mock_group1.name = "Test Group 1"
        mock_group1.trigger_words = ["test", "model1"]
        mock_group1.additions = [{"addition_id": 1}, {"addition_id": 2}]
        
        mock_group2 = Mock()
        mock_group2.id = 2
        mock_group2.name = "Test Group 2"
        mock_group2.trigger_words = ["model2"]
        mock_group2.additions = [{"addition_id": 1}]
        
        mock.prompt_groups = {
            1: mock_group1,
            2: mock_group2
        }
        
        yield mock


class TestPromptCompanionNode:
    """Test the main PromptCompanion node class."""
    
    @pytest.fixture
    def node(self):
        """Create a PromptCompanion node instance."""
        return PromptCompanion()
    
    @pytest.fixture
    def mock_prompt_additions(self):
        """Mock PROMPT_ADDITIONS with test data."""
        with patch('src.prompt_companion_node.PROMPT_ADDITIONS') as mock:
            # Create mock prompt additions
            mock_addition1 = Mock()
            mock_addition1.id = 1
            mock_addition1.name = "Test Addition 1"
            mock_addition1.positive_prompt_addition_text = "positive1"
            mock_addition1.negative_prompt_addition_text = "negative1"
            
            mock_addition2 = Mock()
            mock_addition2.id = 2
            mock_addition2.name = "Test Addition 2"
            mock_addition2.positive_prompt_addition_text = "positive2"
            mock_addition2.negative_prompt_addition_text = "negative2"
            
            mock.prompt_additions = {
                "Test Addition 1": mock_addition1,
                "Test Addition 2": mock_addition2
            }
            
            # Create mock prompt groups
            mock_group1 = Mock()
            mock_group1.id = 1
            mock_group1.name = "Test Group 1"
            mock_group1.trigger_words = ["test", "model1"]
            mock_group1.additions = [{"addition_id": 1}, {"addition_id": 2}]
            
            mock_group2 = Mock()
            mock_group2.id = 2
            mock_group2.name = "Test Group 2"
            mock_group2.trigger_words = ["model2"]
            mock_group2.additions = [{"addition_id": 1}]
            
            mock.prompt_groups = {
                1: mock_group1,
                2: mock_group2
            }
            
            yield mock
    
    @pytest.fixture
    def mock_folder_paths(self):
        """Mock folder_paths module."""
        with patch('src.prompt_companion_node.folder_paths') as mock:
            mock.get_filename_list.return_value = ["model1.safetensors", "model2.ckpt", "test_model.safetensors"]
            yield mock


class TestNodeMetadata:
    """Test node metadata and input types."""
    
    def test_node_metadata(self):
        """Test node metadata is correctly defined."""
        # RETURN_TYPES includes checkpoint list + strings + PROMPT_ADDITION
        assert len(PromptCompanion.RETURN_TYPES) == 6
        assert isinstance(PromptCompanion.RETURN_TYPES[0], list)  # checkpoint list
        assert PromptCompanion.RETURN_TYPES[1:5] == ("STRING", "STRING", "STRING", "STRING")
        assert PromptCompanion.RETURN_TYPES[5] == "PROMPT_ADDITION"
        
        assert PromptCompanion.RETURN_NAMES == (
            "ckpt_name", "positive_combined_prompt", "negative_combined_prompt", 
            "positive_addition", "negative_addition", "prompt_addition"
        )
        assert PromptCompanion.FUNCTION == "combine_prompts"
        assert PromptCompanion.OUTPUT_NODE is True
        assert PromptCompanion.CATEGORY == "jfc"
    
    def test_input_types_structure(self, mock_folder_paths, mock_prompt_additions):
        """Test INPUT_TYPES returns correct structure."""
        input_types = PromptCompanion.INPUT_TYPES()
        
        assert "required" in input_types
        required = input_types["required"]
        
        # Check all required inputs exist
        expected_inputs = [
            "ckpt_name", "addition_type", "prompt_group_mode", "combine_mode",
            "enable_addition", "prompt_addition_name", "prompt_addition_group",
            "positive_addition", "negative_addition", "positive_prompt", "negative_prompt"
        ]
        
        for input_name in expected_inputs:
            assert input_name in required
        
        # Check tooltips are present
        for input_name, (_, options) in required.items():
            if isinstance(options, dict):
                assert "tooltip" in options, f"Missing tooltip for {input_name}"
    
    def test_input_types_dynamic_options(self, mock_folder_paths, mock_prompt_additions):
        """Test that dynamic options are populated correctly."""
        input_types = PromptCompanion.INPUT_TYPES()
        required = input_types["required"]
        
        # Check checkpoint list
        ckpt_options, _ = required["ckpt_name"]
        assert "model1.safetensors" in ckpt_options
        assert "model2.ckpt" in ckpt_options
        
        # Check addition names
        addition_options, _ = required["prompt_addition_name"]
        assert "" in addition_options  # Empty option should be first
        assert "Test Addition 1" in addition_options
        assert "Test Addition 2" in addition_options
        
        # Check group names
        group_options, _ = required["prompt_addition_group"]
        assert "" in group_options  # Empty option should be first
        assert "Test Group 1" in group_options
        assert "Test Group 2" in group_options


class TestPromptCombination:
    """Test prompt combination logic."""
    
    def test_combine_prompts_disabled(self, mock_prompt_additions):
        """Test that no combination occurs when enable_addition is False."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="test_model.safetensors",
            addition_type="Individual",
            prompt_group_mode="Manual",
            combine_mode="prepend",
            enable_addition=False,
            prompt_addition_name="",
            prompt_addition_group="",
            positive_addition="addition_pos",
            negative_addition="addition_neg",
            positive_prompt="base_pos",
            negative_prompt="base_neg"
        )
        
        assert result[:5] == ("test_model.safetensors", "base_pos", "base_neg", "", "")
    
    def test_individual_mode_with_direct_input(self, mock_prompt_additions):
        """Test Individual mode using direct text input."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="test_model.safetensors",
            addition_type="Individual",
            prompt_group_mode="Manual",
            combine_mode="prepend",
            enable_addition=True,
            prompt_addition_name="",  # No saved addition selected
            prompt_addition_group="",
            positive_addition="custom_positive",
            negative_addition="custom_negative",
            positive_prompt="base_positive",
            negative_prompt="base_negative"
        )
        
        expected = (
            "test_model.safetensors",
            "custom_positive, base_positive",
            "custom_negative, base_negative", 
            "custom_positive",
            "custom_negative"
        )
        assert result[:5] == expected
    
    def test_individual_mode_with_saved_addition(self, mock_prompt_additions):
        """Test Individual mode using saved prompt addition."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="test_model.safetensors",
            addition_type="Individual",
            prompt_group_mode="Manual",
            combine_mode="append",
            enable_addition=True,
            prompt_addition_name="Test Addition 1",
            prompt_addition_group="",
            positive_addition="ignored_text",  # Should be ignored when using saved addition
            negative_addition="ignored_text",
            positive_prompt="base_positive",
            negative_prompt="base_negative"
        )
        
        expected = (
            "test_model.safetensors",
            "base_positive, positive1",
            "base_negative, negative1",
            "positive1",
            "negative1"
        )
        assert result[:5] == expected
    
    def test_group_mode_manual(self, mock_prompt_additions):
        """Test Group mode with manual selection."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="test_model.safetensors",
            addition_type="Group",
            prompt_group_mode="Manual",
            combine_mode="prepend",
            enable_addition=True,
            prompt_addition_name="",
            prompt_addition_group="Test Group 1",
            positive_addition="",
            negative_addition="",
            positive_prompt="base_positive",
            negative_prompt="base_negative"
        )
        
        expected = (
            "test_model.safetensors",
            "positive1, positive2, base_positive",
            "negative1, negative2, base_negative",
            "positive1, positive2",
            "negative1, negative2"
        )
        assert result[:5] == expected
    
    def test_group_mode_automatic_with_trigger_match(self, mock_prompt_additions):
        """Test Group mode with automatic trigger word matching."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="test_model.safetensors",  # Should match "test" trigger word in Test Group 1
            addition_type="Group",
            prompt_group_mode="Automatic (Trigger Words)",
            combine_mode="append",
            enable_addition=True,
            prompt_addition_name="",
            prompt_addition_group="",  # Ignored in automatic mode
            positive_addition="",
            negative_addition="",
            positive_prompt="base_positive",
            negative_prompt="base_negative"
        )
        
        expected = (
            "test_model.safetensors",
            "base_positive, positive1, positive2",
            "base_negative, negative1, negative2",
            "positive1, positive2",
            "negative1, negative2"
        )
        assert result[:5] == expected
    
    def test_group_mode_automatic_no_match(self, mock_prompt_additions):
        """Test Group mode with automatic mode when no triggers match."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="no_match_model.safetensors",
            addition_type="Group",
            prompt_group_mode="Automatic (Trigger Words)",
            combine_mode="prepend",
            enable_addition=True,
            prompt_addition_name="",
            prompt_addition_group="",
            positive_addition="",
            negative_addition="",
            positive_prompt="base_positive",
            negative_prompt="base_negative"
        )
        
        # Should return base prompts unchanged when no triggers match
        expected = (
            "no_match_model.safetensors",
            "base_positive",
            "base_negative",
            "",
            ""
        )
        assert result[:5] == expected
    
    def test_combine_mode_prepend(self, mock_prompt_additions):
        """Test prepend combine mode."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="test_model.safetensors",
            addition_type="Individual",
            prompt_group_mode="Manual",
            combine_mode="prepend",
            enable_addition=True,
            prompt_addition_name="",
            prompt_addition_group="",
            positive_addition="addition_text",
            negative_addition="",
            positive_prompt="base_text",
            negative_prompt=""
        )
        
        assert result[1] == "addition_text, base_text"  # positive combined
        assert result[2] == ""  # negative combined (empty)
    
    def test_combine_mode_append(self, mock_prompt_additions):
        """Test append combine mode."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="test_model.safetensors",
            addition_type="Individual",
            prompt_group_mode="Manual",
            combine_mode="append",
            enable_addition=True,
            prompt_addition_name="",
            prompt_addition_group="",
            positive_addition="addition_text",
            negative_addition="",
            positive_prompt="base_text",
            negative_prompt=""
        )
        
        assert result[1] == "base_text, addition_text"  # positive combined
        assert result[2] == ""  # negative combined (empty)
    
    def test_empty_base_prompts_prepend(self, mock_prompt_additions):
        """Test combination with empty base prompts using prepend."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="test_model.safetensors",
            addition_type="Individual",
            prompt_group_mode="Manual",
            combine_mode="prepend",
            enable_addition=True,
            prompt_addition_name="",
            prompt_addition_group="",
            positive_addition="only_addition",
            negative_addition="neg_addition",
            positive_prompt="",
            negative_prompt=""
        )
        
        assert result[1] == "only_addition"  # No comma when base is empty
        assert result[2] == "neg_addition"
    
    def test_empty_base_prompts_append(self, mock_prompt_additions):
        """Test combination with empty base prompts using append."""
        node = PromptCompanion()
        
        result = node.combine_prompts(
            ckpt_name="test_model.safetensors",
            addition_type="Individual",
            prompt_group_mode="Manual",
            combine_mode="append",
            enable_addition=True,
            prompt_addition_name="",
            prompt_addition_group="",
            positive_addition="only_addition",
            negative_addition="neg_addition",
            positive_prompt="",
            negative_prompt=""
        )
        
        assert result[1] == "only_addition"  # No comma when base is empty
        assert result[2] == "neg_addition"


class TestHelperMethods:
    """Test helper methods in PromptCompanion class."""
    
    def test_get_individual_additions_with_name(self, mock_prompt_additions):
        """Test _get_individual_additions with saved addition name."""
        node = PromptCompanion()
        
        pos, neg = node._get_individual_additions(
            "Test Addition 1", "ignored_pos", "ignored_neg"
        )
        
        assert pos == "positive1"
        assert neg == "negative1"
    
    def test_get_individual_additions_with_direct_input(self, mock_prompt_additions):
        """Test _get_individual_additions with direct text input."""
        node = PromptCompanion()
        
        pos, neg = node._get_individual_additions(
            "", "direct_positive", "direct_negative"
        )
        
        assert pos == "direct_positive"
        assert neg == "direct_negative"
    
    def test_get_individual_additions_nonexistent_name(self, mock_prompt_additions):
        """Test _get_individual_additions with non-existent addition name."""
        node = PromptCompanion()
        
        pos, neg = node._get_individual_additions(
            "NonExistent Addition", "fallback_pos", "fallback_neg"
        )
        
        assert pos == "fallback_pos"
        assert neg == "fallback_neg"
    
    def test_group_matches_checkpoint_positive(self, mock_prompt_additions):
        """Test _group_matches_checkpoint with matching trigger words."""
        node = PromptCompanion()
        
        # Create a mock group with trigger words
        mock_group = Mock()
        mock_group.trigger_words = ["test", "model"]
        
        assert node._group_matches_checkpoint(mock_group, "test_model.safetensors") is True
        assert node._group_matches_checkpoint(mock_group, "my_model_v2.ckpt") is True
        assert node._group_matches_checkpoint(mock_group, "TEST_CHECKPOINT.pt") is True  # Case insensitive
    
    def test_group_matches_checkpoint_negative(self, mock_prompt_additions):
        """Test _group_matches_checkpoint with non-matching trigger words."""
        node = PromptCompanion()
        
        mock_group = Mock()
        mock_group.trigger_words = ["anime", "portrait"]
        
        assert node._group_matches_checkpoint(mock_group, "landscape_model.safetensors") is False
        assert node._group_matches_checkpoint(mock_group, "realistic_v1.ckpt") is False
    
    def test_group_matches_checkpoint_empty_triggers(self, mock_prompt_additions):
        """Test _group_matches_checkpoint with empty trigger words."""
        node = PromptCompanion()
        
        mock_group = Mock()
        mock_group.trigger_words = []
        
        assert node._group_matches_checkpoint(mock_group, "any_model.safetensors") is False
    
    def test_group_matches_checkpoint_no_triggers_attr(self, mock_prompt_additions):
        """Test _group_matches_checkpoint with missing trigger_words attribute."""
        node = PromptCompanion()
        
        mock_group = Mock(spec=[])  # Mock without trigger_words attribute
        
        assert node._group_matches_checkpoint(mock_group, "any_model.safetensors") is False
    
    def test_collect_group_additions(self, mock_prompt_additions):
        """Test _collect_group_additions method."""
        node = PromptCompanion()
        
        # Use the mock groups from the fixture
        groups = [mock_prompt_additions.prompt_groups[1]]  # Test Group 1
        
        pos_list, neg_list = node._collect_group_additions(groups)
        
        assert pos_list == ["positive1", "positive2"]
        assert neg_list == ["negative1", "negative2"]
    
    def test_collect_group_additions_empty_groups(self, mock_prompt_additions):
        """Test _collect_group_additions with empty groups list."""
        node = PromptCompanion()
        
        pos_list, neg_list = node._collect_group_additions([])
        
        assert pos_list == []
        assert neg_list == []
    
    def test_combine_prompts_with_additions(self, mock_prompt_additions):
        """Test _combine_prompts_with_additions method."""
        node = PromptCompanion()
        
        # Test prepend mode
        pos, neg = node._combine_prompts_with_additions(
            "base_pos", "base_neg", "add_pos", "add_neg", "prepend"
        )
        assert pos == "add_pos, base_pos"
        assert neg == "add_neg, base_neg"
        
        # Test append mode
        pos, neg = node._combine_prompts_with_additions(
            "base_pos", "base_neg", "add_pos", "add_neg", "append"
        )
        assert pos == "base_pos, add_pos"
        assert neg == "base_neg, add_neg"
        
        # Test with empty additions
        pos, neg = node._combine_prompts_with_additions(
            "base_pos", "base_neg", "", "", "prepend"
        )
        assert pos == "base_pos"
        assert neg == "base_neg"
        
        # Test with empty base prompts
        pos, neg = node._combine_prompts_with_additions(
            "", "", "add_pos", "add_neg", "prepend"
        )
        assert pos == "add_pos"
        assert neg == "add_neg"


if __name__ == "__main__":
    pytest.main([__file__])