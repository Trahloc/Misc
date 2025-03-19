# FILE: tmux_manager/tests/test_server_management.py
"""
# PURPOSE: Tests for the server management module.

## INTERFACES:
  - test_is_tmux_server_running(): Tests the server running check
  - test_ensure_tmux_server_is_running(): Tests server startup functionality

## DEPENDENCIES:
  - pytest: For test framework
  - unittest.mock: For mocking
  - tmux_manager.server_management: Module being tested

## TODO:
  - Add more comprehensive tests
  - Add integration tests
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess
from src.tmux_manager import server_management

def test_is_tmux_server_running_when_running() -> None:
    """
    PURPOSE: Test that _is_tmux_server_running returns True when server is running.
    """
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert server_management._is_tmux_server_running() is True
        mock_run.assert_called_once()

def test_is_tmux_server_running_when_not_running() -> None:
    """
    PURPOSE: Test that _is_tmux_server_running returns False when server is not running.
    """
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert server_management._is_tmux_server_running() is False
        mock_run.assert_called_once()

def test_is_tmux_server_running_with_exception() -> None:
    """
    PURPOSE: Test that _is_tmux_server_running handles exceptions gracefully.
    """
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.SubprocessError("Test error")
        assert server_management._is_tmux_server_running() is False
        mock_run.assert_called_once()

def test_ensure_tmux_server_is_running_already_running() -> None:
    """
    PURPOSE: Test that ensure_tmux_server_is_running returns True when server is already running.
    """
    with patch('src.tmux_manager.server_management._is_tmux_server_running') as mock_is_running:
        mock_is_running.return_value = True

        assert server_management.ensure_tmux_server_is_running() is True
        mock_is_running.assert_called_once()

def test_ensure_tmux_server_is_running_start_via_systemd() -> None:
    """
    PURPOSE: Test that ensure_tmux_server_is_running tries systemd first.
    """
    with patch('src.tmux_manager.server_management._is_tmux_server_running') as mock_is_running, \
         patch('src.tmux_manager.server_management._is_systemd_service_available') as mock_systemd_available, \
         patch('src.tmux_manager.server_management._start_tmux_via_systemd') as mock_start_systemd:

        # Configure mocks
        mock_is_running.return_value = False
        mock_systemd_available.return_value = True
        mock_start_systemd.return_value = True

        # Call the function
        result = server_management.ensure_tmux_server_is_running()

        # Verify results
        assert result is True
        mock_is_running.assert_called_once()
        mock_systemd_available.assert_called_once()
        mock_start_systemd.assert_called_once()

def test_ensure_tmux_server_is_running_start_directly() -> None:
    """
    PURPOSE: Test that ensure_tmux_server_is_running falls back to direct start.
    """
    with patch('src.tmux_manager.server_management._is_tmux_server_running') as mock_is_running, \
         patch('src.tmux_manager.server_management._is_systemd_service_available') as mock_systemd_available, \
         patch('src.tmux_manager.server_management._start_tmux_directly') as mock_start_directly:

        # Configure mocks
        mock_is_running.return_value = False
        mock_systemd_available.return_value = False
        mock_start_directly.return_value = True

        # Call the function
        result = server_management.ensure_tmux_server_is_running()

        # Verify results
        assert result is True
        mock_is_running.assert_called_once()
        mock_systemd_available.assert_called_once()
        mock_start_directly.assert_called_once()

"""
## KNOWN ERRORS:
- No known errors

## IMPROVEMENTS:
- Comprehensive unit tests with mocks
- Tests for edge cases and error conditions

## FUTURE TODOs:
- Add integration tests with actual tmux
- Add parametrized tests for different configurations
"""