"""
# PURPOSE

  Test suite for download handler functionality.
  Tests file download, resumption, and error handling.

## 1. INTERFACES

  TestDownloadHandler: Test class for download handler functionality

## 2. DEPENDENCIES

  unittest: Python's unit testing framework
  unittest.mock: Mocking functionality for API calls
  civit: Local module containing download functions
  requests: For mocking HTTP responses
"""

import pytest
from unittest.mock import patch, MagicMock
import os

from civit.download_handler import download_file

# Setup test parameters
MODEL_ID = "12345"
TEST_URL = "https://example.com/test.zip"
TEST_FILE = "test.zip"


@pytest.fixture
def mock_response():
    """Mock response fixture."""
    mock = MagicMock()
    mock.headers = {"content-length": "1000"}
    mock.iter_content.return_value = [b"test data"]
    mock.raise_for_status.return_value = None
    return mock


@pytest.fixture
def mock_head_response():
    """Mock head response fixture."""
    mock = MagicMock()
    mock.headers = {"Accept-Ranges": "bytes"}
    return mock


def test_download_file_success(tmp_path, mock_response):
    """Test successful file download."""
    with patch("requests.get", return_value=mock_response), patch(
        "requests.head",
        return_value=MagicMock(
            headers={"Content-Disposition": f'attachment; filename="{TEST_FILE}"'}
        ),
    ):
        result = download_file(TEST_URL, str(tmp_path))
        assert isinstance(result, str)  # Success returns a string (file path)
        assert result.endswith(TEST_FILE)


def test_download_file_with_custom_name(tmp_path, mock_response):
    """Test downloading file with custom name."""
    custom_name = "custom.zip"
    with patch("requests.get", return_value=mock_response), patch(
        "requests.head",
        return_value=MagicMock(
            headers={"Content-Disposition": f'attachment; filename="{TEST_FILE}"'}
        ),
    ):
        result = download_file(TEST_URL, str(tmp_path), custom_name=custom_name)
        assert isinstance(result, str)  # Success returns a string (file path)
        assert result.endswith(custom_name)


def test_download_file_with_api_key(tmp_path, mock_response):
    """Test downloading file with API key."""
    api_key = "test_key"
    with patch("requests.get", return_value=mock_response) as mock_get, patch(
        "requests.head",
        return_value=MagicMock(
            headers={"Content-Disposition": f'attachment; filename="{TEST_FILE}"'}
        ),
    ):
        result = download_file(TEST_URL, str(tmp_path), api_key=api_key)
        assert isinstance(result, str)  # Success returns a string (file path)
        mock_get.assert_called_with(
            TEST_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            stream=True,
            timeout=(5, 30),
        )


def test_download_file_resume_supported(tmp_path, mock_response, mock_head_response):
    """Test resuming download when supported."""
    # Create partial file
    file_path = os.path.join(tmp_path, TEST_FILE)
    with open(file_path, "wb") as f:
        f.write(b"partial")

    with patch("requests.head", return_value=mock_head_response) as mock_head, patch(
        "requests.get", return_value=mock_response
    ) as mock_get:
        result = download_file(TEST_URL, str(tmp_path), resume=True)
        assert isinstance(result, str)  # Success returns a string (file path)
        mock_head.assert_called_once()
        mock_get.assert_called_with(
            TEST_URL, headers={"Range": "bytes=7-"}, stream=True, timeout=(5, 30)
        )


def test_download_file_resume_not_supported(tmp_path, mock_response):
    """Test resuming download when not supported."""
    # Create partial file
    file_path = os.path.join(tmp_path, TEST_FILE)
    with open(file_path, "wb") as f:
        f.write(b"partial")

    head_response = MagicMock()
    head_response.headers = {}

    with patch("requests.head", return_value=head_response) as mock_head, patch(
        "requests.get", return_value=mock_response
    ) as mock_get:
        result = download_file(TEST_URL, str(tmp_path), resume=True)
        assert isinstance(result, str)  # Success returns a string (file path)
        mock_head.assert_called_once()
        mock_get.assert_called_with(TEST_URL, headers={}, stream=True, timeout=(5, 30))


def test_download_file_failure(tmp_path):
    """Test download failure with connection error."""
    # Mock the HEAD request to raise an exception
    with patch("requests.head", side_effect=Exception("Mock connection failure")):
        result = download_file(TEST_URL, str(tmp_path))
        # Check that we get an error dictionary on failure
        assert isinstance(result, dict)
        assert "error" in result
        assert "message" in result
        assert "status_code" in result
