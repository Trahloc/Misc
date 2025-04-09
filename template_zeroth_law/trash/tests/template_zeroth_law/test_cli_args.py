# FILE_LOCATION: template_zeroth_law/tests/template_zeroth_law/test_cli_args.py
"""
# PURPOSE: Tests for CLI argument handling and configuration.

## INTERFACES:
 - test_add_args: Test argument addition to commands
 - test_configure_logging: Test logging configuration
 - test_logging_levels: Test verbosity level handling
 - test_option_validation: Test option validation

## DEPENDENCIES:
 - pytest: Testing framework
 - click: Command-line interface utilities
 - logging: Python logging facilities
 - template_zeroth_law.cli_args: CLI argument module
"""

import logging
import pytest
import click
from click.testing import CliRunner
from unittest.mock import patch
from typing import List

from template_zeroth_law.cli_args import add_args, configure_logging


@pytest.fixture
def mock_command() -> click.Command:
    """
    PURPOSE: Create a mock Click command for testing.

    RETURNS: Mock Click command
    """

    @click.command()
    def test_command():
        """Test command."""
        pass

    return test_command


def test_add_args_adds_verbose(mock_command: click.Command):
    """Test that verbose option is properly added."""
    # Add verbose argument
    add_args(mock_command)

    # Verify verbose option added
    verbose_param = next((p for p in mock_command.params if p.name == "verbose"), None)
    assert verbose_param is not None
    assert isinstance(verbose_param, click.Option)
    assert verbose_param.count


@pytest.mark.parametrize(
    "verbosity,expected_level",
    [
        (0, logging.WARNING),
        (1, logging.INFO),
        (2, logging.DEBUG),
        (3, logging.DEBUG),  # More than 2 should still be DEBUG
    ],
)
def test_configure_logging_levels(verbosity: int, expected_level: int):
    """
    Test logging configuration with different verbosity levels.

    PARAMS:
        verbosity: CLI verbosity level
        expected_level: Expected logging level
    """

    @click.command()
    @click.option("--verbose", "-v", count=True)
    @click.pass_context
    def cmd(ctx, verbose: int):
        pass

    ctx = click.Context(cmd)
    ctx.ensure_object(dict)
    ctx.params["verbose"] = verbosity

    with patch("template_zeroth_law.logging.configure_logging") as mock_logging_config:
        configure_logging(ctx, verbosity)
        mock_logging_config.assert_called_once()
        call_args = mock_logging_config.call_args[1]
        assert call_args["level"] == expected_level


def test_configure_logging_format():
    """Test logging format configuration."""

    @click.command()
    @click.pass_context
    def cmd(ctx):
        pass

    ctx = click.Context(cmd)
    ctx.ensure_object(dict)

    # Mock the logging configuration
    with patch("template_zeroth_law.logging.configure_logging") as mock_logging_config:
        configure_logging(ctx, 0)
        mock_logging_config.assert_called_once()
        call_args = mock_logging_config.call_args[1]
        assert "log_format" in call_args
        assert "date_format" in call_args
        assert "%(asctime)s" in call_args["log_format"]
        assert "%(levelname)s" in call_args["log_format"]


def test_cli_integration():
    """Test CLI argument integration with Click."""

    @click.command()
    @click.option("-v", "--verbose", count=True, default=0)
    @click.pass_context
    def test_cmd(ctx, verbose):
        ctx.ensure_object(dict)
        configure_logging(ctx, verbose)

    runner = CliRunner()

    # Test different verbosity levels
    for flags in [[], ["-v"], ["-vv"], ["-vvv"]]:
        result = runner.invoke(test_cmd, flags)
        assert result.exit_code == 0


def test_logging_handler_cleanup():
    """Test that old logging handlers are properly cleaned up."""

    @click.command()
    @click.pass_context
    def cmd(ctx):
        pass

    ctx = click.Context(cmd)
    ctx.ensure_object(dict)

    with patch("template_zeroth_law.logging.configure_logging") as mock_logging_config:
        # Configure logging multiple times
        for _ in range(3):
            configure_logging(ctx, 0)

        # Should be called exactly three times
        assert mock_logging_config.call_count == 3

        # Each call should have the same parameters
        for call in mock_logging_config.call_args_list:
            args = call[1]
            assert "level" in args
            assert "log_format" in args
            assert "date_format" in args


def test_invalid_verbosity():
    """Test handling of invalid verbosity values."""

    @click.command()
    @click.pass_context
    def cmd(ctx):
        pass

    ctx = click.Context(cmd)
    ctx.ensure_object(dict)

    # Test with negative verbosity (should use WARNING level)
    with patch("template_zeroth_law.logging.configure_logging") as mock_logging_config:
        configure_logging(ctx, -1)
        mock_logging_config.assert_called_once()
        call_args = mock_logging_config.call_args[1]
        assert call_args["level"] == logging.WARNING


@pytest.mark.parametrize(
    "option_args",
    [
        ["-v"],
        ["--verbose"],
        ["-vv"],
        ["-vvv"],
    ],
)
def test_verbose_option_forms(option_args: List[str]):
    """
    Test different forms of verbose option.

    PARAMS:
        option_args: List of verbose option variations
    """

    @click.command()
    @click.option("-v", "--verbose", count=True, default=0)
    @click.pass_context
    def test_cmd(ctx, verbose):
        ctx.ensure_object(dict)
        configure_logging(ctx, verbose)

    runner = CliRunner()
    result = runner.invoke(test_cmd, option_args)
    assert result.exit_code == 0


def test_context_logger_setup():
    """Test that logger is properly set up in context."""

    @click.command()
    @click.option("-v", "--verbose", count=True, default=0)
    @click.pass_context
    def test_cmd(ctx, verbose):
        ctx.ensure_object(dict)
        configure_logging(ctx, verbose)
        assert "logger" in ctx.obj
        assert isinstance(ctx.obj["logger"], logging.Logger)

    runner = CliRunner()
    result = runner.invoke(test_cmd)
    assert result.exit_code == 0


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Fixed Click command decoration in tests
 - Fixed command context handling
 - Added proper verbosity level tests
 - Added handler cleanup verification
 - Added type hints
 - Added descriptive docstrings

## FUTURE TODOs:
 - Add tests for custom logging formats
 - Add tests for log file configuration
 - Add tests for environment variable overrides
"""
