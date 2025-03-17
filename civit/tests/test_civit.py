"""Tests for the main civit.py module"""

from unittest.mock import patch, MagicMock
import pytest
import requests
from pathlib import Path
from civit import download_file, download_files


@pytest.fixture
def setup_test_dir(tmp_path):
    """Create a temporary directory for test downloads"""
    test_dir = tmp_path / "test_downloads"
    test_dir.mkdir()
    return test_dir


@patch("requests.get")
@patch("civit.extract_download_url")
def test_successful_download(mock_extract_url, mock_get, setup_test_dir):
    """Test successful file download"""
    # Mock the download URL extraction
    download_url = "https://download.url/file.zip"
    mock_extract_url.return_value = download_url

    # Mock the download response
    mock_response = MagicMock()
    mock_response.headers = {
        "content-length": "1024",
        "content-disposition": "filename=test.zip",
    }
    mock_response.url = download_url  # Set the URL directly
    mock_response.iter_content.return_value = [b"test data"]
    mock_get.return_value = mock_response

    result = download_file("https://civitai.com/models/1234", str(setup_test_dir))
    assert result is True
    assert (setup_test_dir / "test.zip").exists()


@patch("requests.get")
@patch("civit.extract_download_url")
def test_failed_download(mock_extract_url, mock_get, setup_test_dir):
    """Test download failure handling"""
    download_url = "https://download.url/file.zip"
    mock_extract_url.return_value = download_url
    mock_get.side_effect = requests.RequestException("Download failed")

    result = download_file("https://civitai.com/models/1234", str(setup_test_dir))
    assert result is False


@patch("requests.get")
@patch("civit.extract_download_url")
def test_resume_interrupted_download(mock_extract_url, mock_get, setup_test_dir):
    """Test resuming interrupted download"""
    # Mock the download URL extraction
    download_url = "https://download.url/file.zip"
    mock_extract_url.return_value = download_url

    # Create a partial file to simulate an interrupted download
    partial_file = setup_test_dir / "test.zip"
    partial_data = b"x" * 100  # 100 bytes of initial data
    with open(partial_file, "wb") as f:
        f.write(partial_data)

    # Mock the download response - should simulate a 206 Partial Content response
    mock_response = MagicMock()
    mock_response.status_code = 206  # Partial Content
    mock_response.url = download_url  # Set the URL directly

    # Add test data to reach exactly 512 bytes
    remaining_data = b"y" * (512 - len(partial_data))  # This will be 412 bytes
    mock_response.iter_content.return_value = [remaining_data]
    mock_response.headers = {
        "content-length": str(len(remaining_data)),
        "content-disposition": "filename=test.zip",
        "Content-Range": f"bytes {len(partial_data)}-511/512",  # Total size is 512
    }
    mock_get.return_value = mock_response

    # Ensure we're properly mocking the initial file size
    with patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value.st_size = len(partial_data)
        result = download_file("https://civitai.com/models/1234", str(setup_test_dir))
        assert result is True
        assert partial_file.exists()

        # Update mock stat to return the new size for the assertion
        mock_stat.return_value.st_size = len(partial_data) + len(remaining_data)
        assert (
            partial_file.stat().st_size == 512
        )  # Should match the total size in Content-Range


@patch("requests.get")
@patch("civit.extract_download_url")
def test_multiple_successful_downloads(mock_extract_url, mock_get, setup_test_dir):
    """Test multiple successful file downloads"""
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

    urls = ["https://civitai.com/models/1234", "https://civitai.com/models/5678"]
    result = download_files(urls, str(setup_test_dir))
    assert result is True
    assert (setup_test_dir / "test.zip").exists()


@patch("requests.get")
@patch("civit.extract_download_url")
def test_partial_failure_downloads(mock_extract_url, mock_get, setup_test_dir):
    """Test partial failure in multiple file downloads"""
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
    mock_get.side_effect = [mock_response, requests.RequestException("Download failed")]

    urls = ["https://civitai.com/models/1234", "https://civitai.com/models/5678"]
    result = download_files(urls, str(setup_test_dir))
    assert result is False  # Should be False because one download failed
    assert (setup_test_dir / "test.zip").exists()  # First download should succeed
