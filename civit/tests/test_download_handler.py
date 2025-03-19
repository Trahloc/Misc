"""
# PURPOSE: Tests for download_handler.py.

## DEPENDENCIES:
- pytest: For running tests.
- os: For file operations.
- download_handler: The module under test.

## TODO:
- Add unit tests for custom filename functionality.
"""

import os
import pytest
from download_handler import download_file

def test_download_file_with_custom_filename_pattern():
    url = "http://example.com/file.zip"
    destination = "/tmp"
    filename_pattern = "{model_id}_{model_name}_{version}.{ext}"
    metadata = {
        "model_id": "123",
        "model_name": "example_model",
        "version": "1.0",
        "ext": "zip"
    }

    filepath = download_file(url, destination, filename_pattern, metadata)
    expected_filename = "123_example_model_1.0.zip"
    assert os.path.basename(filepath) == expected_filename

def test_download_file_with_custom_filename_format():
    url = "http://example.com/file.zip"
    destination = "/tmp"
    filename_pattern = "{model_type}-{base_model}-{civit_website_model_name}-{model_id}-{crc32}-{original_filename}"
    metadata = {
        "model_type": "LORA",
        "base_model": "Illustrious",
        "civit_website_model_name": "illustrious",
        "model_id": "1373674"
    }

    filepath = download_file(url, destination, filename_pattern, metadata)
    expected_filename = "LORA-Illustrious-illustrious-1373674-5D110398-file.zip"
    assert os.path.basename(filepath) == expected_filename

"""
## KNOWN ERRORS: None

## IMPROVEMENTS: Added test for custom filename patterns.

## FUTURE TODOs: Add more test cases for different filename patterns.
"""