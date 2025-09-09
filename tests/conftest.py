"""
Test configuration and fixtures for ComfyUI Prompt Companion tests.
"""
import sys
from unittest.mock import MagicMock
import pytest


# Mock ComfyUI modules that aren't available during testing
def mock_comfyui_modules():
    """Mock ComfyUI-specific modules for testing."""
    # Mock folder_paths module
    folder_paths_mock = MagicMock()
    folder_paths_mock.__file__ = "/fake/path/to/folder_paths.py"
    folder_paths_mock.get_user_directory.return_value = "/tmp/test_user"
    folder_paths_mock.get_filename_list.return_value = ["model1.safetensors", "model2.ckpt", "test_model.safetensors", "another_model.ckpt", "no_match_model.safetensors"]
    sys.modules['folder_paths'] = folder_paths_mock
    
    # Mock server module if needed
    server_mock = MagicMock()
    server_mock.PromptServer.instance.routes = MagicMock()
    sys.modules['server'] = server_mock


# Set up mocks before importing any modules that depend on ComfyUI
mock_comfyui_modules()


@pytest.fixture
def mock_folder_paths():
    """Fixture providing a mocked folder_paths module."""
    return sys.modules['folder_paths']


@pytest.fixture
def temp_config_dir(tmp_path):
    """Fixture providing a temporary directory for config testing."""
    return tmp_path / "config"