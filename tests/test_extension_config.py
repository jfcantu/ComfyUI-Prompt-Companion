"""
Unit tests for extension configuration in ComfyUI Prompt Companion.

This module tests the data models, configuration management, and persistence
functionality of the Prompt Companion extension.
"""

import json
import pytest
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.extension_config import (
    PromptAddition,
    PromptGroup,
    ExtensionConfig,
    CONFIG_PATH
)


class TestPromptAddition:
    """Test PromptAddition data class."""
    
    def test_creation_with_all_params(self):
        """Test creating PromptAddition with all parameters."""
        addition = PromptAddition(
            name="Test Addition",
            trigger_words="test, sample",
            positive_prompt_addition_text="positive text",
            negative_prompt_addition_text="negative text",
            id=123
        )
        
        assert addition.name == "Test Addition"
        assert addition.trigger_words == "test, sample"
        assert addition.positive_prompt_addition_text == "positive text"
        assert addition.negative_prompt_addition_text == "negative text"
        assert addition.id == 123
    
    def test_creation_with_minimal_params(self):
        """Test creating PromptAddition with minimal parameters."""
        addition = PromptAddition("Simple Addition")
        
        assert addition.name == "Simple Addition"
        assert addition.trigger_words == ""
        assert addition.positive_prompt_addition_text == ""
        assert addition.negative_prompt_addition_text == ""
        assert addition.id is None
    
    def test_id_is_none_by_default(self):
        """Test that ID is None when not provided."""
        addition1 = PromptAddition("Addition 1")
        addition2 = PromptAddition("Addition 2")
        
        assert addition1.id is None
        assert addition2.id is None
    
    def test_to_dict(self):
        """Test converting PromptAddition to dictionary."""
        addition = PromptAddition(
            name="Test Addition",
            trigger_words="test",
            positive_prompt_addition_text="positive",
            negative_prompt_addition_text="negative",
            id=456
        )
        
        expected = {
            "name": "Test Addition",
            "trigger_words": "test",
            "positive_prompt_addition_text": "positive",
            "negative_prompt_addition_text": "negative",
            "id": 456
        }
        
        assert addition.as_dict() == expected
    
    def test_as_dict_includes_all_fields(self):
        """Test that as_dict includes all expected fields."""
        addition = PromptAddition(
            name="Complete Addition",
            trigger_words="word1, word2",
            positive_prompt_addition_text="positive",
            negative_prompt_addition_text="negative",
            id=999
        )
        
        result = addition.as_dict()
        
        assert result["name"] == "Complete Addition"
        assert result["trigger_words"] == "word1, word2"
        assert result["positive_prompt_addition_text"] == "positive"
        assert result["negative_prompt_addition_text"] == "negative"
        assert result["id"] == 999


class TestPromptGroup:
    """Test PromptGroup data class."""
    
    def test_creation_with_all_params(self):
        """Test creating PromptGroup with all parameters."""
        additions = [{"addition_id": 1}, {"addition_id": 2}]
        group = PromptGroup(
            name="Test Group",
            trigger_words=["test", "sample"],
            additions=additions,
            id=123
        )
        
        assert group.name == "Test Group"
        assert group.trigger_words == ["test", "sample"]
        assert group.additions == additions
        assert group.id == 123
    
    def test_creation_with_minimal_params(self):
        """Test creating PromptGroup with minimal parameters."""
        group = PromptGroup("Simple Group")
        
        assert group.name == "Simple Group"
        assert group.trigger_words == []
        assert group.additions == []
        assert group.id is None
    
    def test_id_is_none_by_default(self):
        """Test that ID is None when not provided."""
        group1 = PromptGroup("Group 1")
        group2 = PromptGroup("Group 2")
        
        assert group1.id is None
        assert group2.id is None
    
    def test_to_dict(self):
        """Test converting PromptGroup to dictionary."""
        additions = [{"addition_id": 1}, {"addition_id": 2}]
        group = PromptGroup(
            name="Test Group",
            trigger_words=["test", "group"],
            additions=additions,
            id=456
        )
        
        expected = {
            "name": "Test Group",
            "trigger_words": ["test", "group"],
            "additions": additions,
            "id": 456
        }
        
        assert group.as_dict() == expected
    
    def test_as_dict_includes_all_fields(self):
        """Test that as_dict includes all expected fields."""
        additions = [{"addition_id": 3}, {"addition_id": 4}]
        group = PromptGroup(
            name="Complete Group",
            trigger_words=["word1", "word2"],
            additions=additions,
            id=777
        )
        
        result = group.as_dict()
        
        assert result["name"] == "Complete Group"
        assert result["trigger_words"] == ["word1", "word2"]
        assert result["additions"] == additions
        assert result["id"] == 777


class TestExtensionConfig:
    """Test ExtensionConfig class."""
    
    @pytest.fixture
    def manager(self):
        """Create an ExtensionConfig instance."""
        return ExtensionConfig()
    
    @pytest.fixture
    def sample_additions(self):
        """Create sample PromptAddition objects."""
        return [
            PromptAddition("Addition 1", "trigger1", "pos1", "neg1", 1),
            PromptAddition("Addition 2", "trigger2", "pos2", "neg2", 2)
        ]
    
    @pytest.fixture
    def sample_groups(self):
        """Create sample PromptGroup objects."""
        return [
            PromptGroup("Group 1", ["trigger1"], [{"addition_id": 1}], 1),
            PromptGroup("Group 2", ["trigger2"], [{"addition_id": 2}], 2)
        ]
    
    def test_initialization(self, manager):
        """Test manager initialization."""
        assert isinstance(manager.prompt_additions, dict)
        assert isinstance(manager.prompt_groups, dict)
        assert len(manager.prompt_additions) == 0
        assert len(manager.prompt_groups) == 0
    
    def test_create_or_update_prompt_addition_new(self, manager):
        """Test creating a new prompt addition."""
        addition = PromptAddition("New Addition", "trigger", "pos", "neg")
        
        manager.create_or_update_prompt_addition(addition)
        
        assert "New Addition" in manager.prompt_additions
        assert manager.prompt_additions["New Addition"].name == "New Addition"
        assert manager.prompt_additions["New Addition"].trigger_words == "trigger"
    
    def test_create_or_update_prompt_addition_update(self, manager, sample_additions):
        """Test updating an existing prompt addition."""
        # Add initial addition
        manager.create_or_update_prompt_addition(sample_additions[0])
        original_id = sample_additions[0].id
        
        # Update with same name but different content
        updated_addition = PromptAddition("Addition 1", "new_trigger", "new_pos", "new_neg", original_id)
        manager.create_or_update_prompt_addition(updated_addition)
        
        assert len(manager.prompt_additions) == 1
        assert manager.prompt_additions["Addition 1"].trigger_words == "new_trigger"
        assert manager.prompt_additions["Addition 1"].positive_prompt_addition_text == "new_pos"
        assert manager.prompt_additions["Addition 1"].id == original_id
    
    def test_delete_prompt_addition_exists(self, manager, sample_additions):
        """Test deleting an existing prompt addition."""
        manager.create_or_update_prompt_addition(sample_additions[0])
        
        manager.delete_prompt_addition("Addition 1")
        
        assert "Addition 1" not in manager.prompt_additions
        assert len(manager.prompt_additions) == 0
    
    def test_delete_prompt_addition_not_exists(self, manager):
        """Test deleting a non-existent prompt addition raises KeyError."""
        with pytest.raises(KeyError):
            manager.delete_prompt_addition("NonExistent")
    
    def test_create_or_update_prompt_group_new(self, manager):
        """Test creating a new prompt group."""
        group = PromptGroup("New Group", ["trigger"], [{"addition_id": 1}])
        
        manager.create_or_update_prompt_group(group)
        
        assert group.id in manager.prompt_groups
        assert manager.prompt_groups[group.id].name == "New Group"
        assert manager.prompt_groups[group.id].trigger_words == ["trigger"]
    
    def test_create_or_update_prompt_group_update(self, manager, sample_groups):
        """Test updating an existing prompt group."""
        # Add initial group
        manager.create_or_update_prompt_group(sample_groups[0])
        original_id = sample_groups[0].id
        
        # Update with same ID but different content
        updated_group = PromptGroup("Updated Group", ["new_trigger"], [{"addition_id": 2}], original_id)
        manager.create_or_update_prompt_group(updated_group)
        
        assert len(manager.prompt_groups) == 1
        assert manager.prompt_groups[original_id].name == "Updated Group"
        assert manager.prompt_groups[original_id].trigger_words == ["new_trigger"]
    
    def test_delete_prompt_group_exists(self, manager, sample_groups):
        """Test deleting an existing prompt group."""
        manager.create_or_update_prompt_group(sample_groups[0])
        group_id = sample_groups[0].id
        
        manager.delete_prompt_group(group_id)
        
        assert group_id not in manager.prompt_groups
        assert len(manager.prompt_groups) == 0
    
    def test_delete_prompt_group_not_exists(self, manager):
        """Test deleting a non-existent prompt group raises KeyError."""
        with pytest.raises(KeyError):
            manager.delete_prompt_group(999)
    
    def test_prompt_additions_as_dict(self, manager, sample_additions, sample_groups):
        """Test converting manager data to dictionary format."""
        # Add sample data
        for addition in sample_additions:
            manager.create_or_update_prompt_addition(addition)
        
        for group in sample_groups:
            manager.create_or_update_prompt_group(group)
        
        result = manager.prompt_additions_as_dict()
        
        assert "prompt_additions" in result
        assert "prompt_groups" in result
        
        # Check additions
        assert len(result["prompt_additions"]) == 2
        addition_names = [item["name"] for item in result["prompt_additions"]]
        assert "Addition 1" in addition_names
        assert "Addition 2" in addition_names
        
        # Check groups
        assert len(result["prompt_groups"]) == 2
        group_names = [item["name"] for item in result["prompt_groups"]]
        assert "Group 1" in group_names
        assert "Group 2" in group_names
    
class TestConfigPath:
    """Test configuration path utilities."""
    
    def test_config_path_is_set(self):
        """Test that CONFIG_PATH is properly set."""
        # Test that CONFIG_PATH exists and contains expected filename
        assert CONFIG_PATH is not None
        assert "prompt-companion-config.json" in CONFIG_PATH


class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_workflow_additions(self):
        """Test complete workflow with prompt additions."""
        manager = ExtensionConfig()
        
        # Create addition
        addition = PromptAddition("Workflow Addition", "test", "positive", "negative")
        manager.create_or_update_prompt_addition(addition)
        
        # Verify it exists
        assert "Workflow Addition" in manager.prompt_additions
        
        # Export to dict
        data = manager.prompt_additions_as_dict()
        addition_names = [item["name"] for item in data["prompt_additions"]]
        assert "Workflow Addition" in addition_names
        
        # Verify addition details
        workflow_addition = manager.prompt_additions["Workflow Addition"]
        assert workflow_addition.trigger_words == "test"
        assert workflow_addition.positive_prompt_addition_text == "positive"
        
        # Update addition
        updated_addition = PromptAddition(
            "Workflow Addition", "updated_test", "updated_pos", "updated_neg", 
            workflow_addition.id
        )
        manager.create_or_update_prompt_addition(updated_addition)
        
        # Verify update
        assert manager.prompt_additions["Workflow Addition"].trigger_words == "updated_test"
        
        # Delete addition
        manager.delete_prompt_addition("Workflow Addition")
        assert "Workflow Addition" not in manager.prompt_additions
    
    def test_full_workflow_groups(self):
        """Test complete workflow with prompt groups."""
        manager = ExtensionConfig()
        
        # Create group
        group = PromptGroup("Workflow Group", ["test"], [{"addition_id": 1}])
        manager.create_or_update_prompt_group(group)
        group_id = group.id
        
        # Verify it exists
        assert group_id in manager.prompt_groups
        
        # Export to dict
        data = manager.prompt_additions_as_dict()
        group_names = [item["name"] for item in data["prompt_groups"]]
        assert "Workflow Group" in group_names
        
        # Verify group details
        assert manager.prompt_groups[group_id].name == "Workflow Group"
        
        # Update group
        updated_group = PromptGroup("Updated Group", ["updated_test"], [{"addition_id": 2}], group_id)
        manager.create_or_update_prompt_group(updated_group)
        
        # Verify update
        assert manager.prompt_groups[group_id].trigger_words == ["updated_test"]
        
        # Delete group
        manager.delete_prompt_group(group_id)
        assert group_id not in manager.prompt_groups


if __name__ == "__main__":
    pytest.main([__file__])