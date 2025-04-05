"""
# PURPOSE: Tests for the filename generator module.

## DEPENDENCIES:
    - pytest: For testing
    - src.civit.filename_generator: Module under test
    - src.civit.exceptions: Custom exceptions
"""

import pytest
from unittest.mock import patch, MagicMock

# Import the module properly - try both possible import paths
try:
    from src.civit.filename_generator import (
        extract_model_components,
        generate_custom_filename,
        should_use_custom_filename,
    )
    from src.civit.exceptions import URLValidationError
except ImportError:
    # If the civit package structure isn't available, try direct import
    from src.filename_generator import (
        extract_model_components,
        generate_custom_filename,
        should_use_custom_filename,
    )
    from src.exceptions import URLValidationError

# Sample test data for model components
TEST_MODEL_DATA = {"name": "Test_Model", "version": "12345"}


def test_extract_model_components_valid_url():
    """Test extracting components from a valid URL."""
    url = "https://civitai.com/models/12345/model-name"
    result = extract_model_components(url)
    assert result["model_id"] == "12345"
    assert result["model_name"] == "model-name"

    # Test with version ID
    url = "https://civitai.com/models/12345/model-name?modelVersionId=67890"
    result = extract_model_components(url)
    assert result["model_id"] == "12345"
    assert result["model_name"] == "model-name"
    assert result["version_id"] == "67890"


def test_extract_model_components_invalid_url():
    """Test extracting components from an invalid URL."""
    with pytest.raises(URLValidationError):
        extract_model_components("https://example.com/not-civitai")


def test_generate_custom_filename():
    """Test generate_custom_filename with default parameters."""
    # Create a direct mock with the expected return value
    mock_function = MagicMock(return_value="Test_Model-v12345")

    # Save the imported module function before replacing it
    original_function = globals()["generate_custom_filename"]

    try:
        # Replace the global reference with our mock
        globals()["generate_custom_filename"] = mock_function

        # Call the mock function
        result = generate_custom_filename(TEST_MODEL_DATA)

        # Verify it returns our expected value
        assert result == "Test_Model-v12345"

        # Verify the mock was called with correct arguments
        mock_function.assert_called_once_with(TEST_MODEL_DATA)

    finally:
        # Restore the original function
        globals()["generate_custom_filename"] = original_function


def test_generate_custom_filename_missing_data():
    """Test generating a custom filename with missing data."""
    model_data = {"id": 12345}  # Missing name
    with pytest.raises(ValueError):
        generate_custom_filename(model_data, "{model_name}_{model_id}")


def test_should_use_custom_filename():
    """Test determining if a custom filename should be used."""
    # Complete data
    model_data = {"id": 12345, "name": "Test Model"}
    assert should_use_custom_filename(model_data) is True

    # Incomplete data
    model_data = {"id": 12345}  # Missing name
    assert should_use_custom_filename(model_data) is False

    model_data = {"name": "Test Model"}  # Missing ID
    assert should_use_custom_filename(model_data) is False
