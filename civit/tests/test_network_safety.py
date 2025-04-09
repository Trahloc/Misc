"""
Tests to validate that our network safety measures are working.
"""

import pytest
import requests
import json
from tests.test_utils.network_guard import RealNetworkAccessError


def test_direct_network_blocked():
    """Test that direct network requests are blocked."""
    with pytest.raises(RealNetworkAccessError):
        requests.get("https://civitai.com")


def test_mock_requests_fixture(mock_requests):
    """Test that the mock_requests fixture works."""
    # First, remove the default side effect that raises an exception
    mock_requests["get"].side_effect = None

    # Configure the mock to return a specific response
    mock_response = mock_requests["get"].return_value = requests.Response()
    mock_response.status_code = 200
    mock_response._content = b'{"success": true}'

    # This should now work without error since we've mocked it
    response = requests.get("https://civitai.com/api/v1/models")

    # Verify the mock was called with the expected URL
    mock_requests["get"].assert_called_once_with("https://civitai.com/api/v1/models")
    assert response.status_code == 200


def test_mock_requests_function(mock_requests):
    """Test how to properly mock a function that uses requests."""
    # Remove the default side effect
    mock_requests["get"].side_effect = None

    # Configure the mock
    mock_response = mock_requests["get"].return_value = requests.Response()
    mock_response.status_code = 200
    mock_response._content = b'{"data": "test"}'

    # Example function that would use requests
    def fetch_data():
        response = requests.get("https://civitai.com/api/v1/data")
        return json.loads(response._content.decode("utf-8"))

    # Call the function with our mock
    result = fetch_data()

    # Verify it worked
    assert result == {"data": "test"}
    mock_requests["get"].assert_called_once_with("https://civitai.com/api/v1/data")


def test_custom_mock_with_context():
    """Test using a custom mock within a specific context."""
    import unittest.mock as mock

    with mock.patch("requests.get") as mock_get:
        # Configure the mock
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_get.return_value = mock_response

        # Make a request that would normally be blocked
        response = requests.get("https://civitai.com/api/example")
        data = response.json()

        # Verify
        mock_get.assert_called_once_with("https://civitai.com/api/example")
        assert data == {"result": "success"}
