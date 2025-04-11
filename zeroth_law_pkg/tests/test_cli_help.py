# File: tests/test_cli_help.py
"""Tests for the --help output of the CLI commands."""

from click.testing import CliRunner

from src.zeroth_law.cli import cli_group


def test_all_commands_help():
    """Verify that '--help' works for the main command and all subcommands."""
    runner = CliRunner()

    # 1. Test main command help
    result_main = runner.invoke(cli_group, ["--help"], catch_exceptions=False)
    print(f"Main command help output:\n{result_main.output}")
    assert result_main.exit_code == 0, f"zlt --help failed: {result_main.output}"
    assert "Usage: cli-group [OPTIONS] COMMAND [ARGS]..." in result_main.output
    assert "Zeroth Law Toolkit (zlt)" in result_main.output

    # 2. Test subcommand help
    subcommands = list(cli_group.commands.keys())
    print(f"Found subcommands: {subcommands}")
    assert subcommands, "No subcommands found for cli_group"

    for cmd_name in subcommands:
        print(f"Testing help for subcommand: {cmd_name}")
        result_sub = runner.invoke(cli_group, [cmd_name, "--help"], catch_exceptions=False)
        print(f"Subcommand '{cmd_name}' help output:\n{result_sub.output}")
        assert result_sub.exit_code == 0, f"zlt {cmd_name} --help failed: {result_sub.output}"
        # Basic check for usage string
        assert f"Usage: cli-group {cmd_name} [OPTIONS]" in result_sub.output
