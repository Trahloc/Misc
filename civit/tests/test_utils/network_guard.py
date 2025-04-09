"""
Utilities to prevent real network calls during tests.
"""

import functools
import socket
import os
from unittest import mock
import pytest

original_socket_connect = socket.socket.connect


class RealNetworkAccessError(Exception):
    """Exception raised when a test attempts to make real network calls."""

    pass


def disable_network():
    """Disable all network connections by raising exceptions."""

    def guarded_connect(self, *args, **kwargs):
        host = args[0][0] if args and isinstance(args[0], tuple) else "unknown"
        if os.environ.get("ALLOW_NETWORK_TESTS") != "1":
            raise RealNetworkAccessError(
                f"Test attempted real network connection to {host}. "
                "All HTTP requests should be mocked in tests."
            )
        return original_socket_connect(self, *args, **kwargs)

    socket.socket.connect = guarded_connect


def enable_network():
    """Restore normal network connections."""
    socket.socket.connect = original_socket_connect


@pytest.fixture
def mock_requests():
    """Fixture that mocks requests and raises on real network calls."""
    with mock.patch("requests.get") as mock_get, mock.patch(
        "requests.post"
    ) as mock_post, mock.patch("requests.put") as mock_put, mock.patch(
        "requests.delete"
    ) as mock_delete, mock.patch("requests.head") as mock_head:
        # Set up the mocks to raise by default
        mock_get.side_effect = RealNetworkAccessError(
            "Unmocked requests.get call detected"
        )
        mock_post.side_effect = RealNetworkAccessError(
            "Unmocked requests.post call detected"
        )
        mock_put.side_effect = RealNetworkAccessError(
            "Unmocked requests.put call detected"
        )
        mock_delete.side_effect = RealNetworkAccessError(
            "Unmocked requests.delete call detected"
        )
        mock_head.side_effect = RealNetworkAccessError(
            "Unmocked requests.head call detected"
        )

        yield {
            "get": mock_get,
            "post": mock_post,
            "put": mock_put,
            "delete": mock_delete,
            "head": mock_head,
        }


def prevent_network_access(func):
    """Decorator that prevents tests from making real network calls."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        disable_network()
        try:
            return func(*args, **kwargs)
        finally:
            enable_network()

    return wrapper
