"""
Unit tests for API handlers in ComfyUI Prompt Companion.

This module tests all API endpoint handlers for proper request handling,
validation, error responses, and data consistency.
"""

import json
import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from aiohttp import web
from aiohttp.test import AiohttpClient, make_mocked_request

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.api_handlers import (
    get_prompt_additions,
    write_prompt_addition,
    delete_prompt_addition,
    get_prompt_groups,
    write_prompt_group,
    delete_prompt_group,
    save_prompt_definitions,
    validate_request_json,
    validate_name_field,
    create_success_response,
    create_error_response
)


class TestValidationHelpers:
    """Test validation helper functions."""
    
    def test_validate_request_json_valid(self):
        """Test validation of valid JSON data."""
        data = {"name": "test", "value": "data"}
        is_valid, message, errors = validate_request_json(data)
        
        assert is_valid is True
        assert message is None
        assert errors is None
    
    def test_validate_request_json_invalid(self):
        """Test validation of invalid JSON data."""
        data = "not a dict"
        is_valid, message, errors = validate_request_json(data)
        
        assert is_valid is False
        assert message == "Request body must be a JSON object"
        assert errors == ["Invalid data format"]
    
    def test_validate_name_field_valid(self):
        """Test validation of valid name field."""
        data = {"name": "Valid Name"}
        is_valid, message, errors = validate_name_field(data)
        
        assert is_valid is True
        assert message is None
        assert errors is None
    
    def test_validate_name_field_missing(self):
        """Test validation when name field is missing."""
        data = {}
        is_valid, message, errors = validate_name_field(data)
        
        assert is_valid is False
        assert message == "Missing required field: name"
        assert errors == ["Field 'name' is required"]
    
    def test_validate_name_field_empty(self):
        """Test validation when name field is empty."""
        data = {"name": "   "}
        is_valid, message, errors = validate_name_field(data)
        
        assert is_valid is False
        assert message == "Invalid name"
        assert errors == ["Name must be between 1 and 255 characters"]
    
    def test_validate_name_field_too_long(self):
        """Test validation when name field is too long."""
        data = {"name": "x" * 256}
        is_valid, message, errors = validate_name_field(data)
        
        assert is_valid is False
        assert message == "Invalid name"
        assert errors == ["Name must be between 1 and 255 characters"]


class TestResponseHelpers:
    """Test response helper functions."""
    
    def test_create_success_response(self):
        """Test creation of success response."""
        response = create_success_response("Success", {"key": "value"})
        
        assert isinstance(response, web.Response)
        assert response.status == 200
        assert response.content_type == "application/json"
        
        # Parse the response body
        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert body["message"] == "Success"
        assert body["data"] == {"key": "value"}
        assert body["errors"] == []
    
    def test_create_error_response(self):
        """Test creation of error response."""
        response = create_error_response("Error occurred", ["Detail 1", "Detail 2"], status=400)
        
        assert isinstance(response, web.Response)
        assert response.status == 400
        assert response.content_type == "application/json"
        
        # Parse the response body
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert body["message"] == "Error occurred"
        assert body["errors"] == ["Detail 1", "Detail 2"]


class TestPromptAdditionHandlers:
    """Test prompt addition API handlers."""
    
    @pytest.fixture
    def mock_prompt_additions(self):
        """Mock PROMPT_ADDITIONS global."""
        with patch('src.api_handlers.PROMPT_ADDITIONS') as mock:
            mock.prompt_additions_as_dict.return_value = {
                "additions": {"test": {"name": "test", "positive": "pos", "negative": "neg"}},
                "groups": {}
            }
            yield mock
    
    @pytest.fixture
    def mock_save_definitions(self):
        """Mock save_prompt_definitions function."""
        with patch('src.api_handlers.save_prompt_definitions') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_get_prompt_additions_success(self, mock_prompt_additions):
        """Test successful retrieval of prompt additions."""
        request = Mock()
        
        response = await get_prompt_additions(request)
        
        assert response.status == 200
        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert body["message"] == "Prompt additions retrieved successfully"
        assert "additions" in body["data"]
        mock_prompt_additions.prompt_additions_as_dict.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_prompt_additions_error(self):
        """Test error handling in get_prompt_additions."""
        with patch('src.api_handlers.PROMPT_ADDITIONS') as mock:
            mock.prompt_additions_as_dict.side_effect = Exception("Database error")
            
            request = Mock()
            response = await get_prompt_additions(request)
            
            assert response.status == 500
            body = json.loads(response.body.decode())
            assert body["success"] is False
            assert body["message"] == "Failed to retrieve prompt additions"
    
    @pytest.mark.asyncio
    async def test_write_prompt_addition_success(self, mock_prompt_additions, mock_save_definitions):
        """Test successful creation of prompt addition."""
        request_data = {
            "name": "Test Addition",
            "trigger_words": "test",
            "positive_prompt_addition_text": "positive text",
            "negative_prompt_addition_text": "negative text",
            "id": None
        }
        
        request = Mock()
        request.json = Mock(return_value=request_data)
        
        response = await write_prompt_addition(request)
        
        assert response.status == 200
        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert body["message"] == "Prompt addition saved successfully"
        mock_prompt_additions.create_or_update_prompt_addition.assert_called_once()
        mock_save_definitions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_prompt_addition_invalid_json(self):
        """Test handling of invalid JSON in request."""
        request = Mock()
        request.json = Mock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
        
        response = await write_prompt_addition(request)
        
        assert response.status == 400
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert body["message"] == "Invalid JSON format"
    
    @pytest.mark.asyncio
    async def test_write_prompt_addition_missing_name(self):
        """Test validation when name is missing."""
        request_data = {"positive_prompt_addition_text": "positive text"}
        
        request = Mock()
        request.json = Mock(return_value=request_data)
        
        response = await write_prompt_addition(request)
        
        assert response.status == 400
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert "Missing required field: name" in body["message"]
    
    @pytest.mark.asyncio
    async def test_delete_prompt_addition_success(self, mock_prompt_additions, mock_save_definitions):
        """Test successful deletion of prompt addition."""
        request = Mock()
        request.match_info = {"prompt_addition_name": "test_addition"}
        
        response = await delete_prompt_addition(request)
        
        assert response.status == 200
        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert "deleted successfully" in body["message"]
        mock_prompt_additions.delete_prompt_addition.assert_called_once_with("test_addition")
        mock_save_definitions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_prompt_addition_not_found(self, mock_prompt_additions):
        """Test deletion of non-existent prompt addition."""
        mock_prompt_additions.delete_prompt_addition.side_effect = KeyError("Not found")
        
        request = Mock()
        request.match_info = {"prompt_addition_name": "nonexistent"}
        
        response = await delete_prompt_addition(request)
        
        assert response.status == 404
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert "not found" in body["message"]
    
    @pytest.mark.asyncio
    async def test_delete_prompt_addition_missing_name(self):
        """Test deletion without providing name."""
        request = Mock()
        request.match_info = {}
        
        response = await delete_prompt_addition(request)
        
        assert response.status == 400
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert "required" in body["message"]


class TestPromptGroupHandlers:
    """Test prompt group API handlers."""
    
    @pytest.fixture
    def mock_prompt_additions(self):
        """Mock PROMPT_ADDITIONS global."""
        with patch('src.api_handlers.PROMPT_ADDITIONS') as mock:
            mock.prompt_additions_as_dict.return_value = {
                "additions": {},
                "groups": {"1": {"name": "test_group", "trigger_words": ["test"], "additions": []}}
            }
            yield mock
    
    @pytest.fixture
    def mock_save_definitions(self):
        """Mock save_prompt_definitions function."""
        with patch('src.api_handlers.save_prompt_definitions') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_get_prompt_groups_success(self, mock_prompt_additions):
        """Test successful retrieval of prompt groups."""
        request = Mock()
        
        response = await get_prompt_groups(request)
        
        assert response.status == 200
        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert body["message"] == "Prompt groups retrieved successfully"
        assert "groups" in body["data"]
    
    @pytest.mark.asyncio
    async def test_write_prompt_group_success(self, mock_prompt_additions, mock_save_definitions):
        """Test successful creation of prompt group."""
        request_data = {
            "name": "Test Group",
            "trigger_words": ["trigger1", "trigger2"],
            "additions": [],
            "id": None
        }
        
        request = Mock()
        request.json = Mock(return_value=request_data)
        
        response = await write_prompt_group(request)
        
        assert response.status == 200
        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert body["message"] == "Prompt group saved successfully"
        mock_prompt_additions.create_or_update_prompt_group.assert_called_once()
        mock_save_definitions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_prompt_group_invalid_trigger_words(self):
        """Test validation of invalid trigger_words format."""
        request_data = {
            "name": "Test Group",
            "trigger_words": "not a list",  # Should be a list
            "additions": []
        }
        
        request = Mock()
        request.json = Mock(return_value=request_data)
        
        response = await write_prompt_group(request)
        
        assert response.status == 400
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert "trigger_words must be an array" in body["message"]
    
    @pytest.mark.asyncio
    async def test_delete_prompt_group_success(self, mock_prompt_additions, mock_save_definitions):
        """Test successful deletion of prompt group."""
        request = Mock()
        request.match_info = {"prompt_group_id": "1"}
        
        response = await delete_prompt_group(request)
        
        assert response.status == 200
        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert "deleted successfully" in body["message"]
        mock_prompt_additions.delete_prompt_group.assert_called_once_with(1)
        mock_save_definitions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_prompt_group_invalid_id(self):
        """Test deletion with invalid group ID."""
        request = Mock()
        request.match_info = {"prompt_group_id": "not_a_number"}
        
        response = await delete_prompt_group(request)
        
        assert response.status == 400
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert "Invalid group ID format" in body["message"]
    
    @pytest.mark.asyncio
    async def test_delete_prompt_group_not_found(self, mock_prompt_additions):
        """Test deletion of non-existent prompt group."""
        mock_prompt_additions.delete_prompt_group.side_effect = KeyError("Not found")
        
        request = Mock()
        request.match_info = {"prompt_group_id": "999"}
        
        response = await delete_prompt_group(request)
        
        assert response.status == 404
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert "not found" in body["message"]


class TestSavePromptDefinitions:
    """Test save_prompt_definitions function."""
    
    @patch('src.api_handlers.PromptServer')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.api_handlers.json.dump')
    def test_save_prompt_definitions_success(self, mock_json_dump, mock_file, mock_server):
        """Test successful saving of prompt definitions."""
        # Mock the PROMPT_ADDITIONS global
        with patch('src.api_handlers.PROMPT_ADDITIONS') as mock_additions:
            mock_additions.prompt_additions_as_dict.return_value = {"test": "data"}
            mock_server.instance.send_sync = Mock()
            
            save_prompt_definitions()
            
            # Verify file operations
            mock_file.assert_called_once()
            mock_json_dump.assert_called_once_with({"test": "data"}, mock_file.return_value, indent=2)
            
            # Verify server notification
            mock_server.instance.send_sync.assert_called_once_with(
                "prompt-companion.addition-list", {"test": "data"}
            )
    
    @patch('src.api_handlers.PromptServer')
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_save_prompt_definitions_io_error(self, mock_file, mock_server):
        """Test handling of file I/O errors."""
        with patch('src.api_handlers.PROMPT_ADDITIONS') as mock_additions:
            mock_additions.prompt_additions_as_dict.return_value = {"test": "data"}
            
            with pytest.raises(IOError):
                save_prompt_definitions()


if __name__ == "__main__":
    pytest.main([__file__])