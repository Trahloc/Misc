"""Tests for the main civit.py module"""

from unittest.mock import patch, MagicMock
import pytest
import requests
import logging
import os
import shutil
import tempfile
from pathlib import Path


@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests"""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)  # Fixed the missing closing parenthesis


@pytest.fixture
def setup_test_dir(tmp_path):
    """Create a temporary directory for test downloads"""
    test_dir = tmp_path / "test_downloads"
    test_dir.mkdir()
    return test_dir


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@patch("requests.get")
def test_successful_download(mock_get, setup_test_dir):
    """Test successful file download"""
    # Import function after patching
    from src.download_handler import download_file

    # Mock the response
    mock_response = MagicMock()
    mock_response.headers = {
        "content-length": "1024",
        "content-disposition": 'filename="test.zip"',
    }
    mock_response.iter_content.return_value = [b"test data"]
    mock_get.return_value = mock_response

    # Call function
    result = download_file("https://civitai.com/models/1234", str(setup_test_dir))

    # Assert it would create the file
    assert mock_get.called
    assert result is not None


def test_failed_download():
    """Test that download_file returns None when download fails."""
    # Use patch as context manager for more explicit control
    with patch("requests.get") as mock_get:
        # Set up the mock to raise an exception
        mock_get.side_effect = Exception("Mock download failure")

        # Import the function after patching
        from src.download_handler import download_file

        # Call the function
        result = download_file("https://example.com/file.zip", "output_dir")

        # Assert that None is returned on failure
        assert result is None


@patch("requests.get")
def test_resume_interrupted_download(mock_get, setup_test_dir):
    """Test resuming interrupted download"""
    # Import after patching
    from src.download_handler import download_file

    # Create a partial file to simulate an interrupted download
    partial_file = setup_test_dir / "test.zip"
    partial_data = b"x" * 100  # 100 bytes of initial data
    with open(partial_file, "wb") as f:
        f.write(partial_data)

    # Mock response for resumed download
    mock_response = MagicMock()
    mock_response.status_code = 206  # Partial Content
    mock_response.headers = {
        "content-length": "412",
        "content-disposition": 'filename="test.zip"',
        "Content-Range": f"bytes 100-511/512",  # Total size is 512
    }
    mock_response.iter_content.return_value = [b"y" * 412]  # remaining data
    mock_get.return_value = mock_response

    # Call function
    result = download_file("https://civitai.com/models/1234", str(setup_test_dir))

    # Verify mock was called
    assert mock_get.called
    # Verify function returned something
    assert result is not None
