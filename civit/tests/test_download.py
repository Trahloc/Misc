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
from pathlib import Path

from civit.download_handler import download_file
from civit.url_extraction import extract_model_id, extract_download_url
from civit.model_info import get_model_info

# Setup test parameters
MODEL_ID = "12345"


# Model ID extraction tests
@pytest.mark.parametrize(
    "url",
    [
        "https://civitai.com/models/1234",
        "https://civitai.com/models/1234/model-name",
        "https://www.civitai.com/models/1234?tab=images",
    ],
)
def test_valid_model_urls(url):
    """Ensure URLs considered valid pass."""
    assert extract_model_id(url) is not None


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
@patch("civit.url_extraction.get_model_info")
def test_successful_url_extraction(mock_get_info):
    """Test successful download URL extraction"""
    mock_get_info.return_value = {
        "modelVersions": [{"downloadUrl": "https://download.url"}]
    }
    url = extract_download_url("https://civitai.com/models/1234")
    assert url == "https://download.url"


@patch("civit.url_extraction.get_model_info")
def test_failed_url_extraction(mock_get_info):
    """Test failed download URL extraction"""
    mock_get_info.return_value = None
    url = extract_download_url("https://civitai.com/models/1234")
    assert url is None


# File download tests
class TestFileDownload:
    """Test class for file download functionality"""

    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        """Setup test environment"""
        self.test_url = "https://civitai.com/api/download/models/12345"
        self.test_dir = str(tmp_path / "test_download")
        self.test_file = "test.zip"

    @patch("civit.download_handler.requests.head")
    @patch("civit.download_handler.requests.get")
    @patch("civit.download_handler.is_valid_api_url")
    @patch("civit.download_handler.normalize_url")
    def test_successful_download(
        self, mock_normalize, mock_valid_api, mock_get, mock_head
    ):
        """Test successful file download"""
        # Setup URL validation mocks
        mock_normalize.return_value = self.test_url
        mock_valid_api.return_value = True

        # Setup mock responses
        mock_head.return_value.headers = {
            "Content-Length": "1000",
            "Content-Disposition": 'attachment; filename="test.zip"',
        }
        mock_get.return_value.iter_content.return_value = [b"test data"]
        mock_get.return_value.headers = {
            "Content-Length": "1000",
            "Content-Disposition": 'attachment; filename="test.zip"',
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.url = self.test_url

        # Test download
        result = download_file(self.test_url, self.test_dir)
        assert isinstance(result, str)  # Success returns a string (file path)
        assert result.endswith(self.test_file)

    @patch("civit.download_handler.requests.head")
    @patch("civit.download_handler.requests.get")
    @patch("civit.download_handler.is_valid_api_url")
    @patch("civit.download_handler.normalize_url")
    def test_resume_interrupted_download(
        self, mock_normalize, mock_valid_api, mock_get, mock_head
    ):
        """Test resuming an interrupted download"""
        # Setup URL validation mocks
        mock_normalize.return_value = self.test_url
        mock_valid_api.return_value = True

        # Setup mock responses
        mock_head.return_value.headers = {
            "Content-Length": "1000",
            "Content-Disposition": 'attachment; filename="test.zip"',
        }
        mock_get.return_value.iter_content.return_value = [b"test data"]
        mock_get.return_value.headers = {
            "Content-Length": "1000",
            "Content-Disposition": 'attachment; filename="test.zip"',
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.url = self.test_url

        # Test download with resume
        result = download_file(self.test_url, self.test_dir, resume=True)
        assert isinstance(result, str)  # Success returns a string (file path)
        assert result.endswith(self.test_file)

    @patch("civit.download_handler.requests.head")
    @patch("civit.download_handler.requests.get")
    @patch("civit.download_handler.is_valid_api_url")
    @patch("civit.download_handler.normalize_url")
    @patch("os.makedirs")
    def test_download_with_invalid_output_dir(
        self, mock_makedirs, mock_normalize, mock_valid_api, mock_get, mock_head
    ):
        """Test download with invalid output directory"""
        # Setup URL validation mocks
        mock_normalize.return_value = self.test_url
        mock_valid_api.return_value = True

        # Setup mock responses
        mock_head.return_value.headers = {
            "Content-Length": "1000",
            "Content-Disposition": 'attachment; filename="test.zip"',
        }
        mock_get.return_value.iter_content.return_value = [b"test data"]
        mock_get.return_value.headers = {
            "Content-Length": "1000",
            "Content-Disposition": 'attachment; filename="test.zip"',
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.url = self.test_url

        # Configure makedirs to raise OSError
        mock_makedirs.side_effect = OSError("Permission denied")

        # Test download with invalid directory
        result = download_file(self.test_url, "/invalid/path")

        # Check that we got an error dictionary instead of None
        assert isinstance(result, dict)
        assert "error" in result
        assert "message" in result
        assert "status_code" in result
        assert "unexpected_error" == result["error"]

        # Verify makedirs was called with the correct arguments
        mock_makedirs.assert_called_once_with(Path("/invalid/path"), exist_ok=True)


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
