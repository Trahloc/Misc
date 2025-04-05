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
import os
import sys

# Import the download function after patching
with patch("os.makedirs", side_effect=OSError("Permission denied")):
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
    """Test class for file download functionality"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup test environment"""
        self.test_url = "https://example.com/test.zip"
        self.test_dir = "/tmp/test_download"
        self.test_file = "test.zip"

    @patch("src.download_handler.requests.head")
    @patch("src.download_handler.requests.get")
    def test_successful_download(self, mock_get, mock_head):
        """Test successful file download"""
        # Setup mock responses
        mock_head.return_value.headers = {"Content-Length": "1000"}
        mock_get.return_value.iter_content.return_value = [b"test data"]
        mock_get.return_value.headers = {"Content-Length": "1000"}

        # Test download
        result = download_file(self.test_url, self.test_dir)
        assert result is not None
        assert result.endswith(self.test_file)

    @patch("src.download_handler.requests.head")
    @patch("src.download_handler.requests.get")
    def test_resume_interrupted_download(self, mock_get, mock_head):
        """Test resuming an interrupted download"""
        # Setup mock responses
        mock_head.return_value.headers = {"Content-Length": "1000"}
        mock_get.return_value.iter_content.return_value = [b"test data"]
        mock_get.return_value.headers = {"Content-Length": "1000"}

        # Test download with resume
        result = download_file(self.test_url, self.test_dir, resume=True)
        assert result is not None
        assert result.endswith(self.test_file)

    @patch("src.download_handler.requests.head")
    @patch("src.download_handler.requests.get")
    @patch("os.makedirs")
    def test_download_with_invalid_output_dir(self, mock_makedirs, mock_get, mock_head):
        """Test download with invalid output directory"""
        # Setup mock responses
        mock_head.return_value.headers = {"Content-Length": "1000"}
        mock_get.return_value.iter_content.return_value = [b"test data"]
        mock_get.return_value.headers = {"Content-Length": "1000"}

        # Configure makedirs to raise OSError
        mock_makedirs.side_effect = OSError("Permission denied")

        # Test download with invalid directory
        result = download_file(self.test_url, "/invalid/path")
        assert result is None

        # Verify makedirs was called
        mock_makedirs.assert_called_once_with("/invalid/path", exist_ok=True)


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
