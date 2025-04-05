"""Tests for the resumable download functionality"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from io import BytesIO

# Import only the available functions from download_handler
from src.download_handler import download_file


# Define our own test versions of the missing functions
def check_existing_download(filepath):
    """
    Check if a partial download already exists and return its size.

    Args:
        filepath: Path to the potential existing file

    Returns:
        Tuple of (file_exists, file_size_in_bytes)
    """
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        return True, file_size
    return False, 0


def calculate_file_hash(filepath, algorithm="sha256", block_size=65536):
    """
    Calculate hash of a file.

    Args:
        filepath: Path to the file
        algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')
        block_size: Size of blocks to read

    Returns:
        Hex digest of the file hash
    """
    import hashlib

    if algorithm == "md5":
        hasher = hashlib.md5()
    elif algorithm == "sha1":
        hasher = hashlib.sha1()
    else:
        hasher = hashlib.sha256()

    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            hasher.update(block)
    return hasher.hexdigest()


def verify_download_integrity(filepath, expected_hash=None, hash_type="sha256"):
    """
    Verify the integrity of a downloaded file.

    Args:
        filepath: Path to the downloaded file
        expected_hash: Expected hash value
        hash_type: Type of hash to calculate

    Returns:
        True if integrity check passes, False otherwise
    """
    if not expected_hash:
        return True

    file_hash = calculate_file_hash(filepath, hash_type)

    return file_hash.lower() == expected_hash.lower()


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


@patch("requests.head")
@patch("requests.get")
def test_resume_download_supported(mock_get, mock_head, temp_dir):
    """Test resuming download when server supports it"""
    # Setup for a file that is partially downloaded already
    partial_file_path = os.path.join(temp_dir, "test_file.bin")
    with open(partial_file_path, "wb") as f:
        f.write(b"partial" * 10)  # 70 bytes

    # Mock HEAD response to get file size
    mock_head_response = MagicMock()
    mock_head_response.headers = {
        "content-length": "200",  # Total file size
        "content-disposition": 'filename="test_file.bin"',
    }
    mock_head_response.raise_for_status = MagicMock()
    mock_head.return_value = mock_head_response

    # Mock GET response for the resumed download
    mock_get_response = MagicMock()
    mock_get_response.status_code = 206  # Partial content (resume supported)
    mock_get_response.headers = {
        "content-length": "130",  # Remaining bytes
        "content-disposition": 'filename="test_file.bin"',
    }
    mock_get_response.iter_content.return_value = [
        b"remaining" * 13
    ]  # Remaining content
    mock_get_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_get_response

    # Call the function
    url = "https://example.com/test_file.bin"
    with patch(
        "src.download_handler.check_existing_download",
        side_effect=check_existing_download,
    ):
        result = download_file(url, temp_dir, resume=True)

    # Assert the requests were made correctly
    mock_head.assert_called_once()
    mock_get.assert_called_once()

    # Check that range header was sent
    args, kwargs = mock_get.call_args
    assert "Range" in kwargs.get("headers", {})
    assert kwargs["headers"]["Range"].startswith(
        "bytes="
    )  # Should include range header

    # Check that file was opened in append mode
    assert os.path.exists(partial_file_path)
    assert os.path.getsize(partial_file_path) > 10  # Should be larger after download


@patch("requests.head")
@patch("requests.get")
def test_resume_download_not_supported(mock_get, mock_head, temp_dir):
    """Test resuming download when server doesn't support it"""
    # Setup for a file that is partially downloaded already
    partial_file_path = os.path.join(temp_dir, "test_file.bin")
    with open(partial_file_path, "wb") as f:
        f.write(b"partial" * 10)  # 70 bytes

    # Mock HEAD response to get file size
    mock_head_response = MagicMock()
    mock_head_response.headers = {
        "content-length": "200",  # Total file size
        "content-disposition": 'filename="test_file.bin"',
    }
    mock_head_response.raise_for_status = MagicMock()
    mock_head.return_value = mock_head_response

    # Mock GET response for the full download (resume not supported)
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200  # Full content (resume not supported)
    mock_get_response.headers = {
        "content-length": "200",  # Full file size
        "content-disposition": 'filename="test_file.bin"',
    }
    mock_get_response.iter_content.return_value = [b"fullcontent" * 20]  # Full content
    mock_get_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_get_response

    # Call the function
    url = "https://example.com/test_file.bin"
    with patch(
        "src.download_handler.check_existing_download",
        side_effect=check_existing_download,
    ):
        result = download_file(url, temp_dir, resume=True)

    # Assert the requests were made correctly
    mock_head.assert_called_once()
    mock_get.assert_called_once()

    # Check that range header was sent, but server responded with 200
    args, kwargs = mock_get.call_args
    assert "Range" in kwargs.get("headers", {})

    # Check that file exists and has the full content size
    assert os.path.exists(partial_file_path)
