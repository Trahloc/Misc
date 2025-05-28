"""
# PURPOSE

  Test suite for filename generator functionality.
  Tests filename generation, pattern processing, and error handling.

## 1. INTERFACES

  TestFilenameGenerator: Test class for filename generator functionality

## 2. DEPENDENCIES

  unittest: Python's unit testing framework
  unittest.mock: Mocking functionality for API calls
  civit: Local module containing filename generator functions
"""

import pytest
import logging

from civit.filename_generator import (
    generate_custom_filename,
    sanitize_filename,
    should_use_custom_filename,
    extract_model_components,
)

# Setup test parameters
MODEL_ID = "12345"
VERSION_ID = "67890"
MODEL_NAME = "Test Model"
MODEL_TYPE = "Checkpoint"
BASE_MODEL = "SD 1.5"
FILE_NAME = "test_file.safetensors"


@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests"""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


def test_generate_custom_filename():
    """Test generating a custom filename"""
    model_data = {
        "model": {"type": MODEL_TYPE, "name": MODEL_NAME},
        "baseModel": BASE_MODEL,
        "id": VERSION_ID,
        "modelId": MODEL_ID,
        "files": [{"name": FILE_NAME, "sizeKB": 1000, "hashes": {"CRC32": "12345678"}}],
    }

    result = generate_custom_filename(model_data)
    assert result is not None
    assert sanitize_filename(MODEL_NAME) in result
    assert sanitize_filename(VERSION_ID) in result


def test_generate_custom_filename_missing_data():
    """Test generating a custom filename with missing data"""
    model_data = {
        "model": {"type": MODEL_TYPE, "name": None},
        "baseModel": BASE_MODEL,
        "id": VERSION_ID,
        "modelId": MODEL_ID,
        "files": [{"name": FILE_NAME, "sizeKB": 1000, "hashes": {"CRC32": "12345678"}}],
    }

    result = generate_custom_filename(model_data)
    assert result is not None
    assert sanitize_filename(str(None)) in result
    assert sanitize_filename(VERSION_ID) in result


def test_sanitize_filename():
    """Test sanitizing a filename"""
    test_cases = [
        ("Test/File.zip", "Test_File.zip"),
        ("Test:File.zip", "Test_File.zip"),
        ("Test*File.zip", "Test_File.zip"),
        ("Test?File.zip", "Test_File.zip"),
        ("Test<File.zip", "Test_File.zip"),
        ("Test>File.zip", "Test_File.zip"),
        ("Test|File.zip", "Test_File.zip"),
        ("Test\\File.zip", "Test_File.zip"),
        ("Test/File.zip", "Test_File.zip"),
        ("Test File.zip", "Test_File.zip"),
    ]

    for input_filename, expected_output in test_cases:
        result = sanitize_filename(input_filename)
        assert result == expected_output


def test_should_use_custom_filename():
    """Test determining if custom filename should be used"""
    # Test with valid URL
    assert should_use_custom_filename("https://civitai.com/models/12345") is True

    # Test with invalid URL
    assert should_use_custom_filename("https://example.com/models/12345") is False

    # Test with empty model data
    assert should_use_custom_filename("https://civitai.com/models/12345", {}) is True


def test_extract_model_components():
    """Test extracting model components from URL"""
    # Test with valid URL
    url = "https://civitai.com/models/12345/model-name"
    result = extract_model_components(url)
    assert result["model_id"] == "12345"
    assert result["model_name"] == "model-name"

    # Test with invalid URL
    url = "https://example.com/models/12345"
    result = extract_model_components(url)
    assert result == {}

    # Test with empty URL
    result = extract_model_components("")
    assert result == {}
