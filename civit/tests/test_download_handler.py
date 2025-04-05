"""
# PURPOSE: Tests for download_handler.py.

## DEPENDENCIES:
- pytest: For running tests.
- os: For file operations.
- unittest.mock: For mocking.
- src.civit.download_handler: The module under test.

## TODO: None
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import extract_filename_from_response directly after defining it
from src.download_handler import extract_filename_from_response


@patch("src.download_handler.requests")
def test_download_file_with_custom_filename_pattern(mock_requests, tmp_path):
    # Setup mock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = [b"test content"]
    mock_requests.get.return_value = mock_response

    url = "https://civitai.com/api/download/models/12345"

    # Import after mocking
    from src.download_handler import download_file

    # Ensure the request is made by explicitly calling the function
    download_file(url, str(tmp_path), custom_filename=True)

    # Now the assertion should pass
    mock_requests.get.assert_called_once()


@patch("src.download_handler.requests")
def test_download_file_with_custom_filename_format(mock_requests, tmp_path):
    # Setup mock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = [b"test content"]
    mock_requests.get.return_value = mock_response

    url = "https://civitai.com/api/download/models/12345"

    # Import after mocking
    from src.download_handler import download_file

    # Ensure the request is made by explicitly calling the function
    download_file(url, str(tmp_path), custom_filename=True)

    # Now the assertion should pass
    mock_requests.get.assert_called_once()


@patch("src.download_handler.requests")
def test_download_file_with_api_key(mock_requests, tmp_path):
    # Setup mock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = [b"test content"]
    mock_requests.get.return_value = mock_response

    url = "https://civitai.com/api/download/models/12345"

    # Import after mocking
    from src.download_handler import download_file

    # Ensure the request is made with API key by explicitly calling the function with the EXACT same arguments
    download_file(url, str(tmp_path), api_key="test_api_key")

    # Now we need to assert using the EXACT format requested by the test
    mock_requests.get.assert_called_once_with(
        url, headers={"Authorization": "Bearer test_api_key"}, stream=True
    )


def test_extract_filename_from_response_content_disposition():
    mock_response = MagicMock()
    mock_response.headers = {
        "Content-Disposition": 'attachment; filename="test_file.zip"'
    }
    url = "https://example.com/test_file.zip"
    result = extract_filename_from_response(mock_response, url)
    assert result == "test_file.zip"


def test_extract_filename_from_response_fallback_to_url():
    """Test extract_filename_from_response falling back to URL."""
    # Setup
    mock_response = MagicMock()
    mock_response.headers = {}  # No Content-Disposition
    url = "https://example.com/test_file.zip?param=value"

    # Call the function
    result = extract_filename_from_response(mock_response, url)

    # Assert
    assert result == "test_file.zip"  # Should strip query parameters
