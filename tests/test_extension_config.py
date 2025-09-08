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
    PromptAdditionManager,
    get_prompt_companion_config_path
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
            addition_id=123
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
        assert isinstance(addition.id, int)
        assert addition.id > 0
    
    def test_auto_generated_id(self):
        """Test that ID is auto-generated when not provided."""
        addition1 = PromptAddition("Addition 1")
        addition2 = PromptAddition("Addition 2")
        
        assert addition1.id != addition2.id
        assert isinstance(addition1.id, int)
        assert isinstance(addition2.id, int)
    
    def test_to_dict(self):
        """Test converting PromptAddition to dictionary."""
        addition = PromptAddition(
            name="Test Addition",
            trigger_words="test",
            positive_prompt_addition_text="positive",
            negative_prompt_addition_text="negative",
            addition_id=456
        )
        
        expected = {
            "name": "Test Addition",
            "trigger_words": "test",
            "positive_prompt_addition_text": "positive",
            "negative_prompt_addition_text": "negative",
            "id": 456
        }
        
        assert addition.to_dict() == expected
    
    def test_from_dict(self):
        """Test creating PromptAddition from dictionary."""
        data = {
            "name": "Dict Addition",
            "trigger_words": "dict",
            "positive_prompt_addition_text": "pos",
            "negative_prompt_addition_text": "neg",
            "id": 789
        }
        
        addition = PromptAddition.from_dict(data)
        
        assert addition.name == "Dict Addition"
        assert addition.trigger_words == "dict"
        assert addition.positive_prompt_addition_text == "pos"
        assert addition.negative_prompt_addition_text == "neg"
        assert addition.id == 789
    
    def test_from_dict_missing_fields(self):
        """Test creating PromptAddition from dictionary with missing fields."""
        data = {"name": "Minimal"}
        
        addition = PromptAddition.from_dict(data)
        
        assert addition.name == "Minimal"
        assert addition.trigger_words == ""
        assert addition.positive_prompt_addition_text == ""
        assert addition.negative_prompt_addition_text == ""
        assert isinstance(addition.id, int)


class TestPromptGroup:
    """Test PromptGroup data class."""
    
    def test_creation_with_all_params(self):
        """Test creating PromptGroup with all parameters."""
        additions = [{"addition_id": 1}, {"addition_id": 2}]
        group = PromptGroup(
            name="Test Group",
            trigger_words=["test", "sample"],
            additions=additions,
            group_id=123
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
        assert isinstance(group.id, int)
        assert group.id > 0
    
    def test_auto_generated_id(self):
        """Test that ID is auto-generated when not provided."""
        group1 = PromptGroup("Group 1")
        group2 = PromptGroup("Group 2")
        
        assert group1.id != group2.id
        assert isinstance(group1.id, int)
        assert isinstance(group2.id, int)
    
    def test_to_dict(self):
        """Test converting PromptGroup to dictionary."""
        additions = [{"addition_id": 1}, {"addition_id": 2}]
        group = PromptGroup(
            name="Test Group",
            trigger_words=["test", "group"],
            additions=additions,
            group_id=456
        )
        
        expected = {
            "name": "Test Group",
            "trigger_words": ["test", "group"],
            "additions": additions,
            "id": 456
        }
        
        assert group.to_dict() == expected
    
    def test_from_dict(self):
        """Test creating PromptGroup from dictionary."""
        additions = [{"addition_id": 3}, {"addition_id": 4}]
        data = {
            "name": "Dict Group",
            "trigger_words": ["dict", "test"],
            "additions": additions,
            "id": 789
        }
        
        group = PromptGroup.from_dict(data)
        
        assert group.name == "Dict Group"
        assert group.trigger_words == ["dict", "test"]
        assert group.additions == additions
        assert group.id == 789
    
    def test_from_dict_missing_fields(self):
        """Test creating PromptGroup from dictionary with missing fields."""
        data = {"name": "Minimal Group"}
        
        group = PromptGroup.from_dict(data)
        
        assert group.name == "Minimal Group"
        assert group.trigger_words == []
        assert group.additions == []
        assert isinstance(group.id, int)


class TestPromptAdditionManager:
    """Test PromptAdditionManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a PromptAdditionManager instance."""
        return PromptAdditionManager()
    
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
        
        assert "additions" in result
        assert "groups" in result
        
        # Check additions
        assert len(result["additions"]) == 2
        assert "Addition 1" in result["additions"]
        assert "Addition 2" in result["additions"]
        
        # Check groups
        assert len(result["groups"]) == 2
        assert str(sample_groups[0].id) in result["groups"]
        assert str(sample_groups[1].id) in result["groups"]
    
    def test_load_from_dict_valid_data(self, manager):
        """Test loading manager from valid dictionary data."""
        data = {
            "additions": {
                "Test Addition": {
                    "name": "Test Addition",
                    "trigger_words": "test",
                    "positive_prompt_addition_text": "positive",
                    "negative_prompt_addition_text": "negative",
                    "id": 1
                }
            },
            "groups": {
                "1": {
                    "name": "Test Group",
                    "trigger_words": ["test"],
                    "additions": [{"addition_id": 1}],
                    "id": 1
                }
            }
        }
        
        manager.load_from_dict(data)
        
        assert len(manager.prompt_additions) == 1
        assert len(manager.prompt_groups) == 1
        assert "Test Addition" in manager.prompt_additions
        assert 1 in manager.prompt_groups
    
    def test_load_from_dict_empty_data(self, manager):
        """Test loading manager from empty dictionary data."""
        data = {"additions": {}, "groups": {}}
        
        manager.load_from_dict(data)
        
        assert len(manager.prompt_additions) == 0
        assert len(manager.prompt_groups) == 0
    
    def test_load_from_dict_missing_sections(self, manager):
        """Test loading manager from dictionary with missing sections."""
        data = {}  # Empty dict
        
        manager.load_from_dict(data)
        
        assert len(manager.prompt_additions) == 0
        assert len(manager.prompt_groups) == 0
    
    def test_load_from_dict_invalid_data_structure(self, manager):
        """Test loading manager handles invalid data gracefully."""
        data = {
            "additions": {
                "Bad Addition": "not a dict"  # Should be a dict
            },
            "groups": {
                "1": {
                    "name": "Good Group",
                    "trigger_words": ["test"],
                    "additions": [],
                    "id": 1
                }
            }
        }
        
        # Should not raise an exception and should load valid data
        manager.load_from_dict(data)
        
        assert len(manager.prompt_additions) == 0  # Bad data skipped
        assert len(manager.prompt_groups) == 1     # Good data loaded


class TestConfigPath:
    """Test configuration path utilities."""
    
    @patch('src.extension_config.folder_paths')
    def test_get_prompt_companion_config_path(self, mock_folder_paths):
        """Test getting configuration file path."""
        mock_folder_paths.get_user_directory.return_value = "/mock/user/dir"
        
        config_path = get_prompt_companion_config_path()
        
        expected_path = os.path.join("/mock/user/dir", "prompt_companion_config.json")
        assert config_path == expected_path
        mock_folder_paths.get_user_directory.assert_called_once()


class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_workflow_additions(self):
        """Test complete workflow with prompt additions."""
        manager = PromptAdditionManager()
        
        # Create addition
        addition = PromptAddition("Workflow Addition", "test", "positive", "negative")
        manager.create_or_update_prompt_addition(addition)
        
        # Verify it exists
        assert "Workflow Addition" in manager.prompt_additions
        
        # Export to dict
        data = manager.prompt_additions_as_dict()
        assert "Workflow Addition" in data["additions"]
        
        # Create new manager and load from dict
        new_manager = PromptAdditionManager()
        new_manager.load_from_dict(data)
        
        # Verify data persisted
        assert "Workflow Addition" in new_manager.prompt_additions
        assert new_manager.prompt_additions["Workflow Addition"].trigger_words == "test"
        
        # Update addition
        updated_addition = PromptAddition(
            "Workflow Addition", "updated_test", "updated_pos", "updated_neg", 
            new_manager.prompt_additions["Workflow Addition"].id
        )
        new_manager.create_or_update_prompt_addition(updated_addition)
        
        # Verify update
        assert new_manager.prompt_additions["Workflow Addition"].trigger_words == "updated_test"
        
        # Delete addition
        new_manager.delete_prompt_addition("Workflow Addition")
        assert "Workflow Addition" not in new_manager.prompt_additions
    
    def test_full_workflow_groups(self):
        """Test complete workflow with prompt groups."""
        manager = PromptAdditionManager()
        
        # Create group
        group = PromptGroup("Workflow Group", ["test"], [{"addition_id": 1}])
        manager.create_or_update_prompt_group(group)
        group_id = group.id
        
        # Verify it exists
        assert group_id in manager.prompt_groups
        
        # Export to dict
        data = manager.prompt_additions_as_dict()
        assert str(group_id) in data["groups"]
        
        # Create new manager and load from dict
        new_manager = PromptAdditionManager()
        new_manager.load_from_dict(data)
        
        # Verify data persisted
        assert group_id in new_manager.prompt_groups
        assert new_manager.prompt_groups[group_id].name == "Workflow Group"
        
        # Update group
        updated_group = PromptGroup("Updated Group", ["updated_test"], [{"addition_id": 2}], group_id)
        new_manager.create_or_update_prompt_group(updated_group)
        
        # Verify update
        assert new_manager.prompt_groups[group_id].trigger_words == ["updated_test"]
        
        # Delete group
        new_manager.delete_prompt_group(group_id)
        assert group_id not in new_manager.prompt_groups


if __name__ == "__main__":
    pytest.main([__file__])