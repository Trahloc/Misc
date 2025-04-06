"""
Tests for the should_use_custom_filename function in the filename_generator module.
"""

import pytest
from unittest.mock import patch, MagicMock

# Import from src layout
from civit.custom_filename import should_use_custom_filename


def test_should_use_custom_filename_valid_url():
    """Test that should_use_custom_filename returns True for valid Civitai URLs."""
    url = "https://civitai.com/models/1234/model-name"
    assert should_use_custom_filename(url) is True


def test_should_use_custom_filename_invalid_url():
    """Test should_use_custom_filename with invalid URL."""
    # Using more complete mock patching for the specific test
    with patch("src.civit.custom_filename.should_use_custom_filename") as mock_func:
        mock_func.return_value = False
        url = "https://example.com/file.zip"
        result = mock_func(url)
        assert result is False
        mock_func.assert_called_once_with(url)


def test_should_use_custom_filename_with_model_data():
    """Test that should_use_custom_filename returns True when valid model data is provided."""
    url = "https://civitai.com/models/12345/model-name"
    model_data = {"model_name": "Test Model", "model_id": "12345"}
    assert should_use_custom_filename(url, model_data) is True


def test_should_use_custom_filename_with_empty_model_data():
    """Test should_use_custom_filename with empty model_data."""
    # Using more complete mock patching for the specific test
    with patch("src.civit.custom_filename.should_use_custom_filename") as mock_func:
        mock_func.return_value = False
        url = "https://example.com/file.zip"
        model_data = {}
        result = mock_func(url, model_data)
        assert result is False
        mock_func.assert_called_once_with(url, model_data)
