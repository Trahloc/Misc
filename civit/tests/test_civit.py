"""Tests for the main civit.py module"""

from unittest.mock import patch, MagicMock
import pytest
import requests
import os
from civit.download_handler import download_file


@pytest.fixture
def setup_test_dir(tmp_path):
    """Create a temporary directory for test downloads"""
    test_dir = tmp_path / "test_downloads"
    test_dir.mkdir()
    return test_dir


@patch("src.civit.download_handler.requests.head")
@patch("src.civit.download_handler.requests.get")
def test_successful_download(mock_get, mock_head, setup_test_dir):
    """Test successful file download"""
    # Mock the HEAD response
    mock_head_response = MagicMock()
    mock_head_response.headers = {
        "content-length": "1024",
        "content-disposition": 'filename="test.zip"',
    }
    mock_head_response.raise_for_status = MagicMock()
    mock_head.return_value = mock_head_response

    # Mock the GET response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {
        "content-length": "1024",
        "content-disposition": 'filename="test.zip"',
    }
    mock_response.iter_content.return_value = [b"test data"]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    # Call function
    result = download_file("https://civitai.com/models/1234", str(setup_test_dir))

    # Assert it would create the file
    assert mock_head.called
    assert mock_get.called
    assert isinstance(result, str)  # Success returns a string (file path)


@patch("src.civit.download_handler.requests.head")
@patch("src.civit.download_handler.requests.get")
def test_failed_download(mock_get, mock_head, tmp_path):
    """Test that download_file returns error info when download fails."""
    # Set up the mock to raise an exception
    mock_head.side_effect = Exception("Mock download failure")

    # Call the function
    result = download_file("https://example.com/file.zip", str(tmp_path))

    # Assert that we get an error dictionary on failure
    assert isinstance(result, dict)
    assert "error" in result
    assert "message" in result
    assert "status_code" in result
    assert "unexpected_error" == result["error"]


@patch("src.civit.download_handler.requests.head")
@patch("src.civit.download_handler.requests.get")
def test_connection_timeout(mock_get, mock_head, tmp_path):
    """Test handling of connection timeout."""
    # Set up the mock to raise a timeout exception
    mock_head.side_effect = requests.exceptions.ConnectTimeout("Connection timed out")

    # Call the function
    result = download_file("https://example.com/file.zip", str(tmp_path))

    # Assert that we get the correct error information
    assert isinstance(result, dict)
    assert result["error"] == "connection_timeout"
    assert "timed out" in result["message"].lower()


@patch("src.civit.download_handler.requests.head")
@patch("src.civit.download_handler.requests.get")
def test_http_error(mock_get, mock_head, tmp_path):
    """Test handling of HTTP errors."""
    # Create a response with error status
    error_response = MagicMock()
    error_response.status_code = 404

    # Create HTTPError with the response
    mock_head.side_effect = requests.exceptions.HTTPError(
        "404 Client Error", response=error_response
    )

    # Call the function
    result = download_file("https://example.com/file.zip", str(tmp_path))

    # Assert that we get the correct error information
    assert isinstance(result, dict)
    assert result["error"] == "http_error"
    assert result["status_code"] == 404


@patch("src.civit.download_handler.requests.head")
@patch("src.civit.download_handler.requests.get")
def test_resume_interrupted_download(mock_get, mock_head, setup_test_dir):
    """Test resuming interrupted download"""
    # Create a partial file to simulate an interrupted download
    partial_file = setup_test_dir / "test.zip"
    partial_data = b"x" * 100  # 100 bytes of initial data
    with open(partial_file, "wb") as f:
        f.write(partial_data)

    # Mock HEAD response
    mock_head_response = MagicMock()
    mock_head_response.headers = {
        "content-length": "512",  # Total size is 512 bytes
        "content-disposition": 'filename="test.zip"',
    }
    mock_head_response.raise_for_status = MagicMock()
    mock_head.return_value = mock_head_response

    # Mock GET response for resumed download
    mock_get_response = MagicMock()
    mock_get_response.status_code = 206  # Partial Content
    mock_get_response.headers = {
        "content-length": "412",  # Remaining bytes
        "content-disposition": 'filename="test.zip"',
        "Content-Range": "bytes 100-511/512",  # Total size is 512
    }
    mock_get_response.iter_content.return_value = [b"y" * 412]  # Remaining data
    mock_get_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_get_response

    # Call function with a specific filename to ensure exact match in the test
    result = download_file(
        "https://civitai.com/models/1234",
        str(setup_test_dir),
        filename="test.zip",  # Force the filename to be test.zip
    )

    # Verify mock was called
    mock_head.assert_called_once()
    mock_get.assert_called_once()

    # Verify function returned something
    assert isinstance(result, str)  # Success returns a string (file path)

    # Verify filename is correct
    assert os.path.basename(result) == "test.zip"
