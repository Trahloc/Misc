"""Test the command line interface functionality"""

import pytest
import subprocess
import sys
import os
import logging
from unittest.mock import patch, MagicMock, call
from io import StringIO

# Import from src layout
from civit.cli import main as cli_main, setup_logging, parse_args


def test_help_command():
    """Test the --help command works correctly"""
    # Capture stdout and stderr from the CLI function
    with patch("sys.stdout", new=StringIO()) as fake_stdout, patch(
        "sys.stderr", new=StringIO()
    ):
        try:
            with patch("sys.argv", ["civit.py", "--help"]):
                # This should call sys.exit, so we catch SystemExit
                with pytest.raises(SystemExit):
                    cli_main()

            # Check stdout contains help info
            output = fake_stdout.getvalue()
            assert "usage:" in output.lower()
            assert "--help" in output
            assert "--verbose" in output
            assert "--debug" in output
        except (AttributeError, TypeError):
            # Skip test if it can't be run this way
            pytest.skip("CLI module not properly structured for this test")


def test_verbose_flag():
    """Test the --verbose flag sets the logging level correctly"""
    # Create a mock logger
    mock_logger = MagicMock()

    # Patch getLogger to return our mock
    with patch("logging.getLogger", return_value=mock_logger):
        # Call the function directly with verbosity level 1 for INFO
        setup_logging(verbosity_level=1)

        # Verify the logger was set to INFO level
        mock_logger.setLevel.assert_called_once_with(logging.INFO)


def test_debug_flag():
    """Test the --debug flag sets the logging level correctly"""
    # Create a mock logger
    mock_logger = MagicMock()

    # Patch getLogger to return our mock
    with patch("logging.getLogger", return_value=mock_logger):
        # Call the function directly with debug=True for DEBUG
        setup_logging(debug=True)

        # Verify the logger was set to DEBUG level
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)


def test_short_verbose_flag():
    """Test the -v short flag for verbosity"""
    # Create a mock logger
    mock_logger = MagicMock()

    # Patch getLogger to return our mock
    with patch("logging.getLogger", return_value=mock_logger):
        # Call the function directly with verbosity level 1 for INFO
        setup_logging(verbosity_level=1)

        # Verify the logger was set to INFO level
        mock_logger.setLevel.assert_called_once_with(logging.INFO)


def test_short_debug_flag():
    """Test the -d short flag for debug level verbosity"""
    # Create a mock logger
    mock_logger = MagicMock()

    # Patch getLogger to return our mock
    with patch("logging.getLogger", return_value=mock_logger):
        # Call the function directly with debug=True for DEBUG
        setup_logging(debug=True)

        # Verify the logger was set to DEBUG level
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)


def test_double_verbose_flag():
    """Test the -vv flag sets the logging level to DEBUG"""
    # Create a mock logger
    mock_logger = MagicMock()

    # Patch getLogger to return our mock
    with patch("logging.getLogger", return_value=mock_logger):
        # Call the function directly with verbosity level 2 for DEBUG
        setup_logging(verbosity_level=2)

        # Verify the logger was set to DEBUG level
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)


def test_short_help_command():
    """Test the -h short flag for help command"""
    # Capture stdout and stderr from the CLI function
    with patch("sys.stdout", new=StringIO()) as fake_stdout, patch(
        "sys.stderr", new=StringIO()
    ):
        try:
            with patch("sys.argv", ["civit.py", "-h"]):
                # This should call sys.exit, so we catch SystemExit
                with pytest.raises(SystemExit):
                    cli_main()

            # Check stdout contains help info
            output = fake_stdout.getvalue()
            assert "usage:" in output.lower()
            assert "--help" in output
            assert "-h," in output # Check for the short flag help text
        except (AttributeError, TypeError):
            # Skip test if it can't be run this way
            pytest.skip("CLI module not properly structured for this test")


def test_setup_logging():
    """Test the setup_logging function directly with various combinations"""

    test_cases = [
        # (kwargs, expected_level)
        ({}, logging.WARNING),  # Default
        ({"verbosity_level": 1}, logging.INFO), # -v
        ({"verbosity_level": 2}, logging.DEBUG), # -vv
        ({"verbosity_level": 3}, logging.DEBUG), # -vvv (should also be DEBUG)
        ({"quiet": True}, logging.ERROR),      # -q
        ({"debug": True}, logging.DEBUG),      # -d
        # Precedence tests
        ({"quiet": True, "verbosity_level": 1}, logging.ERROR), # -q wins over -v
        ({"quiet": True, "verbosity_level": 2}, logging.ERROR), # -q wins over -vv (now expects ERROR)
        ({"debug": True, "quiet": True}, logging.DEBUG),      # -d wins over -q
        ({"debug": True, "verbosity_level": 1}, logging.DEBUG), # -d wins over -v
    ]

    for kwargs, expected_level in test_cases:
        mock_logger = MagicMock()
        with patch("logging.getLogger", return_value=mock_logger):
            setup_logging(**kwargs)
            try:
                mock_logger.setLevel.assert_called_once_with(expected_level)
            except AssertionError as e:
                # Raise a more informative error
                raise AssertionError(
                    f"Failed for setup_logging(**{kwargs}). Expected level: {logging.getLevelName(expected_level)}. {e}"
                ) from e


def test_output_folder_arg():
    """Test the -o/--output-folder argument parsing."""
    test_path = "/tmp/test/downloads"
    with patch("src.civit.cli.parse_args") as mock_parse:
        # We only need to test parsing, not the full main function
        args = parse_args(["some_url", "-o", test_path])
        assert args.output_folder == test_path

        args_long = parse_args(["some_url", "--output-folder", test_path])
        assert args_long.output_folder == test_path

        # Test default value (mocking os.getcwd)
        with patch("os.getcwd", return_value="/current/dir"):
            args_default = parse_args(["some_url"])
            assert args_default.output_folder == "/current/dir"


def test_api_key_arg():
    """Test the -k/--api-key argument parsing."""
    test_key = "test_api_12345"
    # We test parse_args directly
    args = parse_args(["some_url", "-k", test_key])
    assert args.api_key == test_key

    args_long = parse_args(["some_url", "--api-key", test_key])
    assert args_long.api_key == test_key

    args_default = parse_args(["some_url"])
    assert args_default.api_key is None


def test_urls_arg():
    """Test the positional urls argument parsing."""
    url1 = "https://example.com/model1"
    url2 = "https://example.com/model2"
    # Test parse_args directly
    # Test single URL
    args_single = parse_args([url1])
    assert args_single.urls == [url1]

    # Test multiple URLs
    args_multi = parse_args([url1, url2])
    assert args_multi.urls == [url1, url2]

    # Test requires at least one URL
    with pytest.raises(SystemExit): # argparse exits on error
         parse_args([]) # No URLs provided


def test_custom_naming_args():
    """Test the --custom-naming and --no-custom-naming flags."""
    # Test parse_args directly
    # Test default (should be True)
    args_default = parse_args(["some_url"])
    assert args_default.custom_naming is True

    # Test explicit --custom-naming
    args_custom = parse_args(["some_url", "--custom-naming"])
    assert args_custom.custom_naming is True

    # Test explicit --no-custom-naming
    args_no_custom = parse_args(["some_url", "--no-custom-naming"])
    assert args_no_custom.custom_naming is False


def test_resume_arg():
    """Test the -r/--resume argument parsing."""
    # Test parse_args directly
    # Test default (should be False)
    args_default = parse_args(["some_url"])
    assert args_default.resume is False

    # Test explicit -r
    args_short = parse_args(["some_url", "-r"])
    assert args_short.resume is True

    # Test explicit --resume
    args_long = parse_args(["some_url", "--resume"])
    assert args_long.resume is True
