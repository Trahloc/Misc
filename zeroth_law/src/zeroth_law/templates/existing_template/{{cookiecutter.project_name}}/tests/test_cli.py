# FILE_LOCATION: source_project2/tests/test_cli.py
"""
# PURPOSE: Tests for the CLI interface of source_project2

## INTERFACES:
#   test_cli_hello: Test the CLI hello command
#   test_cli_info: Test the CLI info command
#   test_cli_verbose: Test the CLI verbose option

## DEPENDENCIES:
#   pytest
#   click.testing
#   source_project2.cli
"""
import pytest
from click.testing import CliRunner
from {{ cookiecutter.project_name }}.cli import main


def test_cli_hello():
    """Test the CLI hello command with different inputs"""
    runner = CliRunner()

    # Test default hello (no name provided)
    result = runner.invoke(main, ["hello"])
    assert result.exit_code == 0
    assert "Hello, world!" in result.output

    # Test hello with a name
    result = runner.invoke(main, ["hello", "Alice"])
    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output

    # Test hello with formal flag
    result = runner.invoke(main, ["hello", "--formal", "Alice"])
    assert result.exit_code == 0
    assert "Greetings, Alice!" in result.output


def test_cli_info():
    """Test the CLI info command"""
    runner = CliRunner()

    # Test basic info
    result = runner.invoke(main, ["info"])
    assert result.exit_code == 0
    assert "Project: source_project2" in result.output

    # Test detailed info
    result = runner.invoke(main, ["info", "--details"])
    assert result.exit_code == 0
    assert "Project: source_project2" in result.output
    assert "Description:" in result.output
    assert "Zeroth Law AI Framework" in result.output


def test_cli_verbose():
    """Test the CLI verbose option affects logging"""
    runner = CliRunner()

    # This is a simple check that the command runs with verbose flag
    # More detailed logging tests would need to capture log output
    result = runner.invoke(main, ["-v", "info"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["-vv", "info"])
    assert result.exit_code == 0


@pytest.fixture
def cli_runner():
    """Provides a Click test runner"""
    return CliRunner()


def test_cli_error_handling(cli_runner, monkeypatch):
    """Test CLI error handling when a command fails"""
    # Mock greet_user in the commands/hello module where it's actually used
    def mock_greet_user(*args, **kwargs):
        raise ValueError("Test error")

    # Apply the mock to the correct module where it's imported and used
    monkeypatch.setattr(
        "source_project2.commands.hello.greet_user",
        mock_greet_user
    )

    # Test that the CLI handles errors correctly
    result = cli_runner.invoke(main, ["hello"], catch_exceptions=True)
    assert "Error during greeting" in result.output
    assert result.exit_code == 1