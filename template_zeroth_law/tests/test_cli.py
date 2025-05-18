# FILE_LOCATION: template_zeroth_law/tests/test_cli.py
"""
# PURPOSE: Tests for the CLI functionality, ensuring command registration and error handling.

## INTERFACES:
 - test_cli_check(): Test the check command
 - test_cli_version(): Test the version command
 - test_cli_verbose(): Test verbose logging
 - test_cli_error_handling(): Test error handling
 - test_cli_config(): Test configuration loading
 - test_cli_context(): Test context initialization

## DEPENDENCIES:
 - click.testing: CLI testing utilities
 - pytest: Testing framework
 - template_zeroth_law.cli: CLI module under test
"""

import logging
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from template_zeroth_law.cli import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """
    PURPOSE: Provides a Click test runner.

    RETURNS: A new CliRunner instance
    """
    return CliRunner()


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """
    PURPOSE: Creates a temporary config file for testing.

    RETURNS: Path to the temporary config file
    """
    config = tmp_path / "config.json"
    config.write_text(
        """
    {
        "app": {
            "name": "test_app",
            "version": "1.0.0",
            "description": "Test configuration"
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(message)s"
        }
    }
    """
    )
    return config


def test_cli_init(cli_runner: CliRunner):
    """Test CLI initialization."""
    result = cli_runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Command-line interface" in result.output


def test_cli_verbose_levels(cli_runner: CliRunner):
    """Test different verbosity levels."""
    # Test default (WARNING)
    result = cli_runner.invoke(main, ["version"])
    assert result.exit_code == 0

    # Test INFO level
    result = cli_runner.invoke(main, ["-v", "version"])
    assert result.exit_code == 0

    # Test DEBUG level
    result = cli_runner.invoke(main, ["-vv", "version"])
    assert result.exit_code == 0


def test_cli_config_loading(cli_runner: CliRunner, config_file: Path):
    """Test configuration file loading."""
    result = cli_runner.invoke(main, ["--config", str(config_file), "version"])
    assert result.exit_code == 0


def test_cli_check_command(cli_runner: CliRunner):
    """Test the check command with different options."""
    # Test basic check
    result = cli_runner.invoke(main, ["check"])
    assert result.exit_code == 0
    assert "Environment Information" in result.output

    # Test with --deps option
    result = cli_runner.invoke(main, ["check", "--deps"])
    assert result.exit_code == 0
    assert "Dependency Information" in result.output

    # Test with --env option
    result = cli_runner.invoke(main, ["check", "--env"])
    assert result.exit_code == 0
    assert "Environment Information" in result.output


def test_cli_version_command(cli_runner: CliRunner):
    """Test the version command with different options."""
    # Test basic version
    result = cli_runner.invoke(main, ["version"])
    assert result.exit_code == 0

    # Test verbose version
    result = cli_runner.invoke(main, ["version", "--verbose"])
    assert result.exit_code == 0
    assert "Python:" in result.output

    # Test JSON output
    result = cli_runner.invoke(main, ["version", "--json"])
    assert result.exit_code == 0
    assert '"name":' in result.output


def test_cli_info_command(cli_runner: CliRunner):
    """Test the info command with different options."""
    # Test basic info
    result = cli_runner.invoke(main, ["info"])
    assert result.exit_code == 0

    # Test detailed info
    result = cli_runner.invoke(main, ["info", "--details"])
    assert result.exit_code == 0


def test_cli_error_handling(cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch):
    """Test CLI error handling when commands fail."""

    def mock_check_environment(*args: Any, **kwargs: Any) -> None:
        raise ValueError("Test error")

    # Patch the check environment function
    monkeypatch.setattr(
        "template_zeroth_law.commands.check.check_environment", mock_check_environment
    )

    # Test that error is properly handled
    result = cli_runner.invoke(main, ["check"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_cli_context_initialization(cli_runner: CliRunner):
    """Test that CLI context is properly initialized."""

    @main.command()
    def test_context():
        """Test command to verify context."""
        import click

        ctx = click.get_current_context()
        assert "logger" in ctx.obj
        assert "config" in ctx.obj
        assert "verbose" in ctx.obj
        assert isinstance(ctx.obj["logger"], logging.Logger)

    # Test context initialization
    result = cli_runner.invoke(main, ["test-context"])
    assert result.exit_code == 0


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added comprehensive test coverage
 - Added fixtures for common test resources
 - Added proper error handling tests
 - Added configuration loading tests
 - Added context initialization tests
 - Added type annotations
 - Added detailed docstrings

## FUTURE TODOs:
 - Add tests for command groups and subcommands
 - Add tests for custom command options
 - Add integration tests with actual file operations
"""
