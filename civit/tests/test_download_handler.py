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
from unittest import mock
from pathlib import Path

from src.civit.download_handler import download_file, extract_filename_from_response

@mock.patch('src.civit.download_handler.requests.get')
@mock.patch('src.civit.download_handler.download_with_progress')
def test_download_file_with_custom_filename_pattern(mock_download_progress, mock_get):
    """Test download_file with a custom filename pattern."""
    # Setup mocks
    mock_response = mock.MagicMock()
    mock_response.headers = {'content-length': '1024'}
    mock_get.return_value = mock_response
    mock_download_progress.return_value = True

    # Setup test data
    url = "https://example.com/file.zip"
    destination = "/tmp"
    filename_pattern = "{model_id}_{model_name}_{version}.{ext}"
    metadata = {
        "model_id": "123",
        "model_name": "example_model",
        "version": "1.0"
    }

    # Mock the extract_filename_from_response function to return a known value
    with mock.patch('src.civit.download_handler.extract_filename_from_response',
                   return_value='file.zip'):
        # Call the function
        filepath = download_file(url, destination, filename_pattern, metadata)

    # Assert
    expected_path = str(Path("/tmp") / "123_example_model_1.0.zip")
    assert filepath == expected_path
    mock_get.assert_called_once_with(url, headers={}, stream=True)
    mock_download_progress.assert_called_once()


@mock.patch('src.civit.download_handler.requests.get')
@mock.patch('src.civit.download_handler.download_with_progress')
def test_download_file_with_custom_filename_format(mock_download_progress, mock_get):
    """Test download_file with a complex filename pattern that includes CRC32."""
    # Setup mocks
    mock_response = mock.MagicMock()
    mock_response.headers = {'content-length': '1024'}
    mock_get.return_value = mock_response
    mock_download_progress.return_value = True

    # Setup test data
    url = "https://example.com/file.zip"
    destination = "/tmp"
    filename_pattern = "{model_type}-{base_model}-{civit_website_model_name}-{model_id}-{crc32}-{original_filename}"
    metadata = {
        "model_type": "LORA",
        "base_model": "Illustrious",
        "civit_website_model_name": "illustrious",
        "model_id": "1373674"
    }

    # Mock the extract_filename_from_response function to return a known value
    with mock.patch('src.civit.download_handler.extract_filename_from_response',
                   return_value='file.zip'):
        # Call the function
        filepath = download_file(url, destination, filename_pattern, metadata)

    # CRC32 of 'file.zip' calculated by the code is BEDDDC26
    expected_filename = "LORA-Illustrious-illustrious-1373674-BEDDDC26-file.zip"
    expected_path = str(Path("/tmp") / expected_filename)

    # Assert
    assert filepath == expected_path
    mock_get.assert_called_once_with(url, headers={}, stream=True)
    mock_download_progress.assert_called_once()


@mock.patch('src.civit.download_handler.requests.get')
@mock.patch('src.civit.download_handler.download_with_progress')
def test_download_file_with_api_key(mock_download_progress, mock_get):
    """Test download_file with an API key."""
    # Setup mocks
    mock_response = mock.MagicMock()
    mock_response.headers = {'content-length': '1024'}
    mock_get.return_value = mock_response
    mock_download_progress.return_value = True

    # Setup test data
    url = "https://example.com/file.zip"
    destination = "/tmp"
    api_key = "test_api_key"

    # Mock the extract_filename_from_response function to return a known value
    with mock.patch('src.civit.download_handler.extract_filename_from_response',
                   return_value='file.zip'):
        # Call the function
        filepath = download_file(url, destination, api_key=api_key)

    # Assert
    expected_path = str(Path("/tmp") / "file.zip")
    assert filepath == expected_path
    mock_get.assert_called_once_with(url, headers={'Authorization': 'Bearer test_api_key'}, stream=True)
    mock_download_progress.assert_called_once()


def test_extract_filename_from_response_content_disposition():
    """Test extract_filename_from_response with Content-Disposition header."""
    # Setup
    mock_response = mock.MagicMock()
    mock_response.headers = {'content-disposition': 'attachment; filename="test_file.zip"'}
    url = "https://example.com/file.zip"

    # Call the function
    result = extract_filename_from_response(mock_response, url)

    # Assert
    assert result == "test_file.zip"


def test_extract_filename_from_response_fallback_to_url():
    """Test extract_filename_from_response falling back to URL."""
    # Setup
    mock_response = mock.MagicMock()
    mock_response.headers = {}  # No Content-Disposition
    url = "https://example.com/test_file.zip?param=value"

    # Call the function
    result = extract_filename_from_response(mock_response, url)

    # Assert
    assert result == "test_file.zip"  # Should strip query parameters


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Proper mocking of HTTP requests to avoid actual network calls during tests
- Fixed imports to use the correct module path
- Added test for API key usage
- Added separate tests for extract_filename_from_response function

## FUTURE TODOs:
- Add tests for error handling scenarios
- Add tests for download resumption with custom filenames when implemented
"""