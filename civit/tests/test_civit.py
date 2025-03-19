"""Tests for the main civit.py module"""
from unittest.mock import patch, MagicMock
import pytest
import requests
import logging
from pathlib import Path
from src.civit import download_file

@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests"""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)

@pytest.fixture
def setup_test_dir(tmp_path):
    """Create a temporary directory for test downloads"""
    test_dir = tmp_path / "test_downloads"
    test_dir.mkdir()
    return test_dir

@patch("requests.get")
def test_successful_download(mock_get, setup_test_dir):
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

    result = download_file("https://civitai.com/models/1234", str(setup_test_dir))
    assert result == str(setup_test_dir / "test.zip")
    assert (setup_test_dir / "test.zip").exists()

@patch("requests.get")
def test_failed_download(mock_get, setup_test_dir):
    """Test download failure handling"""
    mock_get.side_effect = requests.RequestException("Download failed")
    result = download_file("https://civitai.com/models/1234", str(setup_test_dir))
    assert result is None  # Implementation returns None on failure

@patch("requests.get")
def test_resume_interrupted_download(mock_get, setup_test_dir):
    """Test resuming interrupted download"""
    # Create a partial file to simulate an interrupted download
    partial_file = setup_test_dir / "test.zip"
    partial_data = b"x" * 100  # 100 bytes of initial data
    with open(partial_file, "wb") as f:
        f.write(partial_data)

    # Mock the first response (API response with download URL)
    api_response = MagicMock()
    api_response.json.return_value = {"downloadUrl": "https://download.url/test.zip"}

    # Mock the second response (actual file download)
    download_response = MagicMock()
    download_response.status_code = 206  # Partial Content
    remaining_data = b"y" * (512 - len(partial_data))  # 412 bytes to reach 512 total
    download_response.iter_content.return_value = [remaining_data]
    download_response.headers = {
        "content-length": str(len(remaining_data)),
        "content-disposition": 'filename="test.zip"',
        "Content-Range": f"bytes {len(partial_data)}-511/512",  # Total size is 512
    }

    # Set up the mock to return different responses based on URL
    def mock_get_side_effect(*args, **kwargs):
        if args[0] == "https://download.url/test.zip":
            return download_response
        return api_response
    mock_get.side_effect = mock_get_side_effect

    # Mock stat and Path operations to handle resume correctly
    with patch("pathlib.Path.stat") as mock_stat, \
         patch("pathlib.Path.mkdir") as mock_mkdir:
        # Setup mock stat to return valid file info
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o100644  # Regular file mode
        mock_stat_result.st_size = len(partial_data)
        mock_stat.return_value = mock_stat_result

        # Don't raise error on mkdir since the dir already exists
        mock_mkdir.return_value = None

        result = download_file("https://civitai.com/models/1234", str(setup_test_dir))
        assert result == str(setup_test_dir / "test.zip")
        assert partial_file.exists()
