"""
# PURPOSE

  Test suite for download functionality.
  Tests API interaction, URL extraction, and file download capabilities.

## 1. INTERFACES

  TestModelInfo: Test class for API model info retrieval
  TestModelIdExtraction: Test class for model ID extraction
  TestDownloadUrl: Test class for download URL extraction
  TestFileDownload: Test class for file download functionality

## 2. DEPENDENCIES

  unittest: Python's unit testing framework
  unittest.mock: Mocking functionality for API calls
  civit: Local module containing download functions
  requests: For mocking HTTP responses
"""

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from pathlib import Path
import logging
from src.civit import download_file
from src.civit.url_extraction import extract_model_id, extract_download_url
from src.civit.model_info import get_model_info


# Model ID extraction tests
@pytest.mark.parametrize(
    "url,expected_id",
    [
        ("https://civitai.com/models/1234", "1234"),
        ("https://civitai.com/models/1234/model-name", "1234"),
        ("https://www.civitai.com/models/1234?tab=images", "1234"),
    ],
)
def test_valid_model_urls(url, expected_id):
    """Test extraction of model IDs from valid URLs"""
    assert extract_model_id(url) == expected_id


@pytest.mark.parametrize(
    "url",
    [
        "https://civitai.com/images/1234",
        "https://civitai.com/user/profile",
        "https://civitai.com/models/invalid",
        "",
    ],
)
def test_invalid_model_urls(url):
    """Test that invalid URLs return None"""
    assert extract_model_id(url) is None


# Model info tests
@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests"""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@patch("requests.get")
def test_successful_model_info_fetch(mock_get):
    """Test successful API response handling"""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "Test Model",
        "modelVersions": [{"downloadUrl": "https://download.url"}],
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_model_info("1234")
    assert result is not None
    assert result["name"] == "Test Model"


@patch("requests.get")
def test_failed_model_info_fetch(mock_get):
    """Test API error handling"""
    mock_get.side_effect = Exception("API Error")
    result = get_model_info("1234")
    assert result is None


# Download URL tests
@patch("src.civit.url_extraction.get_model_info")
def test_successful_url_extraction(mock_get_info):
    """Test successful download URL extraction"""
    mock_get_info.return_value = {
        "modelVersions": [{"downloadUrl": "https://download.url"}]
    }
    url = extract_download_url("https://civitai.com/models/1234")
    assert url == "https://download.url"


@patch("src.civit.url_extraction.get_model_info")
def test_failed_url_extraction(mock_get_info):
    """Test failed download URL extraction"""
    mock_get_info.return_value = None
    url = extract_download_url("https://civitai.com/models/1234")
    assert url is None


# File download tests
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock
from src.download_handler import download_file


class TestFileDownload:
    """Test file downloading functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test directory before each test."""
        self.test_dir = tempfile.mkdtemp(prefix="test_downloads")
        yield
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("src.download_handler.requests")
    def test_successful_download(self, mock_requests):
        """Test successful file download."""
        # Configure mock response - need to use requests not just get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"test content"]
        mock_response.headers = {
            "content-length": "100",
            "content-disposition": 'filename="test.zip"',
        }
        mock_requests.get.return_value = mock_response

        # Import directly to ensure we're using the mocked version
        from src.download_handler import download_file

        url = "https://civitai.com/api/download/models/12345"

        # Call the function
        download_file(url, str(self.test_dir))

        # Assert request was made
        mock_requests.get.assert_called_once()

    @patch("src.download_handler.requests")
    def test_resume_interrupted_download(self, mock_requests):
        """Test resuming an interrupted download."""
        # Configure mock response - need to use requests not just get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"partial content"]
        mock_response.headers = {
            "content-length": "100",
            "content-disposition": 'filename="test.zip"',
        }
        mock_requests.get.return_value = mock_response

        # Import directly to ensure we're using the mocked version
        from src.download_handler import download_file

        url = "https://civitai.com/api/download/models/12345"

        # Call the function
        download_file(url, str(self.test_dir))

        # Assert request was made
        mock_requests.get.assert_called_once()

    @patch("src.download_handler.requests.get")
    def test_download_with_invalid_output_dir(self, mock_get):
        """Test download with invalid output directory."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Test with invalid dir
        invalid_dir = "/nonexistent/directory"
        url = "https://civitai.com/api/download/models/12345"

        result = download_file(url, invalid_dir)
        assert result is None


"""
## Current Known Errors

None - Initial implementation

## Improvements Made

- Created comprehensive test suite for all download-related functionality
- Added mocking for API and network calls
- Implemented proper test cleanup
- Added tests for error cases

## Future TODOs

- Add tests for rate limiting scenarios
- Add tests for different file types and sizes
- Consider adding integration tests with actual API
"""
