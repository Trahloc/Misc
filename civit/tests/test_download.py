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
class TestFileDownload:
    """Tests for download functionality"""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test environment"""
        self.test_dir = tmp_path / "test_downloads"
        self.test_dir.mkdir(parents=True, exist_ok=True)

    @patch("requests.get")
    def test_successful_download(self, mock_get):
        """Test successful file download"""
        # Mock the first response (API response with download URL)
        api_response = MagicMock()
        api_response.json.return_value = {"downloadUrl": "https://download.url/test.zip"}

        # Mock the second response (actual file download)
        download_response = MagicMock()
        download_response.headers = {
            "content-length": "1024",
            "content-disposition": 'filename="test.zip"'
        }
        download_response.iter_content.return_value = [b"test data"]

        # Set up the mock to return different responses based on URL
        def mock_get_side_effect(*args, **kwargs):
            if args[0] == "https://download.url/test.zip":
                return download_response
            return api_response

        mock_get.side_effect = mock_get_side_effect

        result = download_file("https://civitai.com/models/1234", str(self.test_dir))
        assert result == str(self.test_dir / "test.zip")
        assert (self.test_dir / "test.zip").exists()

    @patch("requests.get")
    def test_empty_url(self, mock_get):
        """Test download with empty URL"""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            download_file("", str(self.test_dir))
        mock_get.assert_not_called()

    @patch("requests.get")
    @patch("pathlib.Path.mkdir")
    def test_download_with_invalid_output_dir(self, mock_mkdir, mock_get):
        """Test download with invalid output directory"""
        mock_mkdir.side_effect = OSError("Permission denied")
        result = download_file("https://civitai.com/models/1234", "/nonexistent/dir")
        assert result is None

    @patch("requests.get")
    def test_resume_interrupted_download(self, mock_get):
        """Test resuming interrupted download"""
        # Mock the first response (API response with download URL)
        api_response = MagicMock()
        api_response.json.return_value = {"downloadUrl": "https://download.url/test.zip"}

        # Mock the download response with support for range requests
        download_response = MagicMock()
        download_response.status_code = 206  # Partial Content
        download_response.headers = {
            "content-length": "1024",
            "content-disposition": 'filename="test.zip"',
            "accept-ranges": "bytes",
            "content-range": "bytes 0-1023/1024"
        }
        download_response.iter_content.return_value = [b"x" * 1024]

        def mock_get_side_effect(*args, **kwargs):
            if args[0] == "https://download.url/test.zip":
                return download_response
            return api_response

        mock_get.side_effect = mock_get_side_effect

        # Create partial file
        partial_file = self.test_dir / "test.zip"
        partial_data = b"x" * 100
        with open(partial_file, "wb") as f:
            f.write(partial_data)

        result = download_file("https://civitai.com/models/1234", str(self.test_dir))
        assert result == str(self.test_dir / "test.zip")
        assert partial_file.exists()


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
