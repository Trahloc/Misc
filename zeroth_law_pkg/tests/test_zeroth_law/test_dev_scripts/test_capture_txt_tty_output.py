"""Tests for src/zeroth_law/dev_scripts/capture_txt_tty_output.py."""

import pytest
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from src.zeroth_law.dev_scripts.capture_txt_tty_output import (
    main,
    capture_tty_output,
    DEFAULT_TERM_ROWS,
    DEFAULT_TERM_COLS,
)


# Helper for sys.exit mocking
class MockSystemExit(Exception):
    pass


@pytest.fixture
def mock_exit_fixture():
    with patch("sys.exit") as mock_exit:
        mock_exit.side_effect = MockSystemExit
        yield mock_exit


# --- Tests for main() function (Refactored to avoid internal mocks) ---


@patch("builtins.print")
def test_main_success_stdout(mock_print, mock_exit_fixture, monkeypatch):
    """Test main successful execution printing to stdout via real capture_tty_output."""
    test_cmd = "echo -n hello_stdout"
    monkeypatch.setattr(sys, "argv", ["capture_txt_tty_output.py", test_cmd])

    with pytest.raises(MockSystemExit):
        main()

    # Assert print and exit code
    # Note: echo -n produces no newline, normalization doesn't add one.
    mock_print.assert_called_once_with("hello_stdout", end="")  # FIX: Removed expected newline
    mock_exit_fixture.assert_called_once_with(0)


@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open)
def test_main_success_file_output(mock_open_func, mock_mkdir, mock_exit_fixture, monkeypatch, tmp_path):
    """Test main successful execution writing to file via real capture_tty_output."""
    output_file = tmp_path / "main_output.txt"
    test_cmd = f"echo -n file_content"
    encoding = "ascii"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_txt_tty_output.py",
            test_cmd,
            "-o",
            str(output_file),
            "--encoding",
            encoding,
            "--encoding-errors",
            "ignore",
        ],
    )

    with pytest.raises(MockSystemExit):
        main()

    # Assert file write and exit code
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_open_func.assert_called_once_with(output_file, "w", encoding=encoding)
    # Note: echo -n produces no newline, normalization doesn't add one.
    mock_open_func().write.assert_called_once_with("file_content")  # FIX: Removed expected newline
    mock_exit_fixture.assert_called_once_with(0)


def test_main_empty_command(mock_exit_fixture, monkeypatch):
    """Test main handling of an empty command string argument."""
    monkeypatch.setattr(sys, "argv", ["capture_txt_tty_output.py", ""])  # Empty command
    with pytest.raises(MockSystemExit):
        main()
    mock_exit_fixture.assert_called_once_with(1)


def test_main_capture_failure(mock_exit_fixture, monkeypatch):
    """Test main propagating a non-zero exit code from real capture_tty_output."""
    fail_code = 7
    test_cmd = f'{sys.executable} -c "import sys; sys.exit({fail_code})"'
    monkeypatch.setattr(sys, "argv", ["capture_txt_tty_output.py", test_cmd])
    with pytest.raises(MockSystemExit):
        main()
    mock_exit_fixture.assert_called_once_with(fail_code)


@patch("builtins.print")  # Still need to mock print
def test_main_decode_error(mock_print, mock_exit_fixture, monkeypatch):
    """Test main handling of a decoding error with real capture_tty_output."""
    invalid_byte_cmd = "import sys; sys.stdout.buffer.write(b'\xff')"
    test_cmd = f'{sys.executable} -c "{invalid_byte_cmd}"'
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_txt_tty_output.py",
            test_cmd,
            "--encoding",
            "ascii",
            "--encoding-errors",
            "strict",  # Cause failure
        ],
    )
    with pytest.raises(MockSystemExit):
        main()
    mock_print.assert_not_called()
    mock_exit_fixture.assert_called_once_with(max(0, -3))


@patch("builtins.open", new_callable=mock_open)
def test_main_file_write_error(mock_open_func, mock_exit_fixture, monkeypatch, tmp_path):
    """Test main handling of a file write error with real capture_tty_output."""
    output_file = tmp_path / "write_error.txt"
    test_cmd = "echo -n write_test"
    monkeypatch.setattr(sys, "argv", ["capture_txt_tty_output.py", test_cmd, "-o", str(output_file)])
    mock_open_func.side_effect = IOError("Simulated write error")
    with pytest.raises(MockSystemExit):
        main()
    mock_open_func.assert_called_once_with(output_file, "w", encoding="utf-8")
    mock_exit_fixture.assert_called_once_with(0)


# --- Tests for capture_tty_output() --- (Refined)


def test_capture_tty_output_echo():
    """Test capturing simple echo output."""
    command = ["echo", "-n", "hello world"]
    output_bytes, exit_code = capture_tty_output(command)
    assert exit_code == 0
    assert b"hello world" in output_bytes
    assert b"echo" not in output_bytes


def test_capture_tty_output_exit_code():
    """Test capturing the exit code of a failing command."""
    command = [sys.executable, "-c", "import sys; sys.exit(9)"]
    output_bytes, exit_code = capture_tty_output(command)
    assert exit_code == 9


def test_capture_tty_output_command_not_found(mock_exit_fixture):  # FIX: Add fixture
    """Test capture_tty_output handling of FileNotFoundError."""
    command = ["_this_command_should_not_exist_12345_"]
    # Expect the internal sys.exit(1) to be called
    with pytest.raises(MockSystemExit):  # FIX: Expect MockSystemExit
        capture_tty_output(command)
    # FIX: Assert sys.exit was called with 1
    mock_exit_fixture.assert_called_once_with(1)


# TODO: Add tests for other branches in capture_tty_output:
# - select timeout but process finishes
# - os.read OSError
# - fcntl.ioctl error
# - subprocess.TimeoutExpired
# - generic Exception
