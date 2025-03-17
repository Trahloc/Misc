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
from civit import download_file
from url_extraction import extract_model_id, extract_download_url
from model_info import get_model_info


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
@patch("url_extraction.get_model_info")
def test_successful_url_extraction(mock_get_info):
    """Test successful download URL extraction"""
    mock_get_info.return_value = {
        "modelVersions": [{"downloadUrl": "https://download.url"}]
    }
    url = extract_download_url("https://civitai.com/models/1234")
    assert url == "https://download.url"


@patch("url_extraction.get_model_info")
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
    @patch("civit.extract_download_url")
    def test_successful_download(self, mock_extract_url, mock_get):
        """Test successful file download"""
        # Mock the download URL extraction
        download_url = "https://download.url/file.zip"
        mock_extract_url.return_value = download_url

        # Mock the download response
        mock_response = MagicMock()
        mock_response.url = download_url  # Set the URL directly
        mock_response.headers = {
            "content-length": "1024",
            "content-disposition": "filename=test.zip",
        }
        mock_response.iter_content.return_value = [b"test data"]
        mock_get.return_value = mock_response

        result = download_file("https://civitai.com/models/1234", str(self.test_dir))
        assert result is True
        downloaded_file = self.test_dir / "test.zip"
        assert downloaded_file.exists()

    @patch("requests.get")
    @patch("civit.extract_download_url")
    @patch("builtins.open", create=True)
    def test_resume_download_with_validations(
        self, mock_open, mock_extract_url, mock_get
    ):
        """Test resuming a download with server response validations"""
        # Mock the download URL extraction
        download_url = "https://download.url/file.zip"
        mock_extract_url.return_value = download_url

        # Create a file-like object to track written content
        file_content = BytesIO()
        mock_file = MagicMock()

        def mock_write(data):
            nonlocal file_content
            size = file_content.write(data)
            return size

        mock_file.write = mock_write
        mock_file.tell = lambda: file_content.tell()
        mock_context = MagicMock()
        mock_context.__enter__ = lambda x: mock_file
        mock_open.return_value = mock_context

        # Mock the initial download response
        mock_response_initial = MagicMock()
        mock_response_initial.url = download_url  # Set the URL directly
        mock_response_initial.headers = {
            "content-length": "1024",
            "content-disposition": "filename=test.zip",
            "Accept-Ranges": "bytes",
        }
        # Generate 500 bytes of data
        initial_data = b"x" * 500
        mock_response_initial.iter_content.return_value = [initial_data]
        mock_response_initial.status_code = 200

        # Calculate the size of our initial data
        initial_data_size = len(initial_data)

        # Mock the resumed download response
        mock_response_resume = MagicMock()
        mock_response_resume.url = download_url  # Set the URL directly
        mock_response_resume.headers = {
            "content-length": "512",
            "content-disposition": "filename=test.zip",
            "Content-Range": f"bytes {initial_data_size}-1023/1024",
        }
        # Generate remaining data
        remaining_data = b"y" * (1024 - initial_data_size)
        mock_response_resume.iter_content.return_value = [remaining_data]
        mock_response_resume.status_code = 206

        # Set up the side effects for the mock get
        def mock_get_side_effect(*args, **kwargs):
            if "headers" in kwargs and "Range" in kwargs["headers"]:
                range_header = kwargs["headers"]["Range"]
                if range_header == f"bytes={initial_data_size}-":
                    return mock_response_resume
            return mock_response_initial

        mock_get.side_effect = mock_get_side_effect

        # Mock Path.exists and stat methods for file size checking
        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.stat"
        ) as mock_stat:

            # First download: file doesn't exist yet
            mock_stat.return_value.st_size = 0
            result_initial = download_file(
                "https://civitai.com/models/1234", str(self.test_dir)
            )
            assert result_initial is True
            assert file_content.tell() == 500  # Initial data size

            # Second download: file exists with partial content
            mock_stat.return_value.st_size = initial_data_size
            result_resume = download_file(
                "https://civitai.com/models/1234", str(self.test_dir)
            )
            assert result_resume is True
            assert file_content.tell() == 1024  # Total size after resume

    def test_download_with_empty_url(self):
        """Test download with empty URL"""
        result = download_file("", str(self.test_dir))
        assert result is False

    @patch("os.mkdir")
    @patch("pathlib.PurePath")
    @patch("pathlib.Path")
    def test_download_with_invalid_output_dir(
        self, mock_path_class, mock_pure_path, mock_mkdir
    ):
        """Test download with invalid output directory"""
        # Mock os.mkdir to raise PermissionError
        mock_mkdir.side_effect = PermissionError("Permission denied")

        # Create a mock Path instance
        mock_path_instance = MagicMock()
        mock_path_instance.parent = mock_path_instance  # Handle recursive parent access
        mock_path_instance.exists.return_value = False  # Directory doesn't exist

        # Make both Path and PurePath return our mock instance
        mock_path_class.return_value = mock_path_instance
        mock_pure_path.return_value = mock_path_instance

        # Mock path division operations
        mock_path_instance.__truediv__ = lambda self, other: mock_path_instance
        mock_path_class.__truediv__ = lambda self, other: mock_path_instance
        mock_pure_path.__truediv__ = lambda self, other: mock_path_instance

        result = download_file("https://civitai.com/models/1234", "/nonexistent/dir")
        assert result is False
        # Verify mkdir was called
        mock_mkdir.assert_called()


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
