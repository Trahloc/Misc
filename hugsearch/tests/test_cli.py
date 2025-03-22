# FILE_LOCATION: hugsearch/tests/test_cli.py
"""
# PURPOSE: Tests for the CLI functionality.

## INTERFACES:
 - test_cli_check(): Test the check command
 - test_cli_version(): Test the version command
 - test_cli_verbose(): Test verbose logging
 - test_cli_error_handling(): Test error handling

## DEPENDENCIES:
 - click.testing: CLI testing utilities
 - pytest: Testing framework
"""
import pytest
from click.testing import CliRunner

from hugsearch.cli import cli  # Import cli instead of main

def test_cli_check():
    """Test the CLI check command with different options"""
    runner = CliRunner()

    # Test basic check
    result = runner.invoke(cli, ["check"])
    assert result.exit_code == 0

    # Test with verbose flag
    result = runner.invoke(cli, ["-v", "check"])
    assert result.exit_code == 0

def test_cli_version():
    """Test the CLI version command"""
    runner = CliRunner()

    # Test basic version
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0

    # Test with verbose flag
    result = runner.invoke(cli, ["-v", "version"])
    assert result.exit_code == 0

def test_cli_verbose():
    """Test the CLI verbose option affects logging"""
    runner = CliRunner()

    # Test with different verbosity levels
    result = runner.invoke(cli, ["-v", "version"])
    assert result.exit_code == 0
    assert "INFO" in result.output or "DEBUG" in result.output

    result = runner.invoke(cli, ["-vv", "version"])
    assert result.exit_code == 0
    assert "DEBUG" in result.output

def test_cli_error_handling(cli_runner, monkeypatch):
    """Test CLI error handling when a command fails"""
    # Mock check_environment in the commands/check module
    def mock_check_environment(*args, **kwargs):
        raise ValueError("Test error")

    # Apply the mock to the correct module
    monkeypatch.setattr(
        "hugsearch.commands.check.check_environment",
        mock_check_environment
    )

    # Test that the CLI handles errors correctly
    result = cli_runner.invoke(cli, ["check"], catch_exceptions=True)
    assert result.exit_code != 0
    assert "Error" in result.output

@pytest.fixture
def cli_runner():
    """Provides a Click test runner"""
    return CliRunner()