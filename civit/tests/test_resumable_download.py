"""
# PURPOSE

  Test suite for resumable download functionality.
  Tests download resumption, progress tracking, and error handling.

## 1. INTERFACES

  TestResumableDownload: Test class for resumable download functionality

## 2. DEPENDENCIES

  unittest: Python's unit testing framework
  unittest.mock: Mocking functionality for API calls
  civit: Local module containing download functions
  requests: For mocking HTTP responses
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import logging

# Import from src layout
from civit.download_handler import (
    check_existing_download,
    calculate_file_hash,
    verify_download_integrity,
    download_file,
)

# Constants for tests
CONTENT_LENGTH = 1000

# Setup test parameters
TEST_URL = "https://civitai.com/api/download/models/12345"
TEST_FILE = "test.zip"
TEST_SIZE = 1000
TEST_HASH = "12345678"


@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests"""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def partial_file(temp_dir):
    """Create a partial file for testing resume functionality"""
    filepath = os.path.join(temp_dir, "partial_file.bin")
    with open(filepath, "wb") as f:
        f.write(b"x" * 100)  # Write 100 bytes as "partial download"
    return filepath


def test_check_existing_download(partial_file):
    """Test check_existing_download can correctly identify partial downloads"""
    exists, size = check_existing_download(partial_file)
    assert exists is True
    assert size == 100

    # Test non-existent file
    exists, size = check_existing_download(
        os.path.join(os.path.dirname(partial_file), "nonexistent.bin")
    )
    assert exists is False
    assert size == 0


def test_calculate_file_hash(partial_file):
    """Test file hash calculation"""
    # Calculate expected hash for the content
    import hashlib

    expected_hash = hashlib.sha256(b"x" * 100).hexdigest()

    # Test our function
    calculated_hash = calculate_file_hash(partial_file)
    assert calculated_hash == expected_hash

    # Test with different algorithm
    md5_hash = calculate_file_hash(partial_file, algorithm="md5")
    expected_md5 = hashlib.md5(b"x" * 100).hexdigest()
    assert md5_hash == expected_md5


def test_verify_download_integrity(partial_file):
    """Test verification of downloaded file integrity"""
    # Calculate the real hash
    import hashlib

    real_hash = hashlib.sha256(b"x" * 100).hexdigest()

    # Test with correct hash
    assert verify_download_integrity(partial_file, real_hash) is True

    # Test with incorrect hash
    assert verify_download_integrity(partial_file, "wronghash123") is False

    # Test with no hash (should pass)
    assert verify_download_integrity(partial_file) is True


@patch("civit.download_handler.requests.head")
@patch("civit.download_handler.requests.get")
@patch("civit.download_handler.is_valid_api_url")
@patch("civit.download_handler.normalize_url")
def test_resume_download_supported(mock_normalize, mock_valid_api, mock_get, mock_head):
    """Test resuming a download when the server supports it"""
    # Setup URL validation mocks
    mock_normalize.return_value = TEST_URL
    mock_valid_api.return_value = True

    # Setup mock responses
    mock_head.return_value.headers = {
        "Content-Length": str(TEST_SIZE),
        "Content-Disposition": f'attachment; filename="{TEST_FILE}"',
        "Accept-Ranges": "bytes",
    }
    mock_get.return_value.iter_content.return_value = [b"test data"]
    mock_get.return_value.headers = {
        "Content-Length": str(TEST_SIZE),
        "Content-Disposition": f'attachment; filename="{TEST_FILE}"',
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.url = TEST_URL

    # Test download with resume
    result = download_file(TEST_URL, "/tmp", resume=True)
    assert isinstance(result, str)  # Success returns a string (file path)
    assert result.endswith(TEST_FILE)

    # Verify head was called with the correct arguments
    mock_head.assert_called_once_with(
        TEST_URL, headers={}, timeout=(5, 30), allow_redirects=True
    )


@patch("civit.download_handler.requests.head")
@patch("civit.download_handler.requests.get")
@patch("civit.download_handler.is_valid_api_url")
@patch("civit.download_handler.normalize_url")
def test_resume_download_not_supported(
    mock_normalize, mock_valid_api, mock_get, mock_head
):
    """Test resuming a download when the server doesn't support it"""
    # Setup URL validation mocks
    mock_normalize.return_value = TEST_URL
    mock_valid_api.return_value = True

    # Setup mock responses
    mock_head.return_value.headers = {
        "Content-Length": str(TEST_SIZE),
        "Content-Disposition": f'attachment; filename="{TEST_FILE}"',
    }
    mock_get.return_value.iter_content.return_value = [b"test data"]
    mock_get.return_value.headers = {
        "Content-Length": str(TEST_SIZE),
        "Content-Disposition": f'attachment; filename="{TEST_FILE}"',
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.url = TEST_URL

    # Test download with resume
    result = download_file(TEST_URL, "/tmp", resume=True)
    assert isinstance(result, str)  # Success returns a string (file path)
    assert result.endswith(TEST_FILE)

    # Verify head was called with the correct arguments
    mock_head.assert_called_once_with(
        TEST_URL, headers={}, timeout=(5, 30), allow_redirects=True
    )


@patch("civit.download_handler.requests.head")
def test_download_failure_with_http_error(mock_head):
    """Test handling of download failure due to HTTP error"""
    # Create a response with error status
    error_response = MagicMock()
    error_response.status_code = 404

    # Create HTTPError with the response
    import requests

    mock_head.side_effect = requests.exceptions.HTTPError(
        "404 Client Error", response=error_response
    )

    # Test download
    result = download_file(TEST_URL, "/tmp")

    # Check that we get an error dictionary
    assert isinstance(result, dict)
    assert result["error"] == "http_error"
    assert result["status_code"] == 404
    assert "HTTP error occurred" in result["message"]
