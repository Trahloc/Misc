# FILE: tests/test_cli_simple.py
"""Simple test for the command-line interface."""

from click.testing import CliRunner

from src.zeroth_law.cli import cli_group


def test_cli_help():
    """Test that the CLI help command works."""
    runner = CliRunner()
    result = runner.invoke(cli_group, ["--help"], catch_exceptions=False)
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    assert "Usage:" in result.output
