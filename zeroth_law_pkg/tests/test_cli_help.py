# File: tests/test_cli_help.py
"""Tests for the --help output of the CLI commands."""

import importlib
import sys
from pathlib import Path
import pytest
from click.testing import CliRunner

# Add src to path to allow importing the cli module
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent / "src"))

# Import the module containing the CLI definitions
import src.zeroth_law.cli as cli_module  # Import the module

# --- Constants ---
EXPECTED_HELP_OUTPUT_SUBSTRINGS = [
    "Usage: zeroth-law [OPTIONS] COMMAND [ARGS]...",
]


def test_all_commands_help():
    """Verify that '--help' works for the main command and all subcommands."""
    runner = CliRunner()

    # Reload module to ensure commands are loaded
    importlib.reload(cli_module)

    # 1. Test main command help
    result_main = runner.invoke(cli_module.cli_group, ["--help"], catch_exceptions=False)
    print(f"Main command help output:\n{result_main.output}")
    assert result_main.exit_code == 0, f"zlt --help failed: {result_main.output}"
    assert "Usage: cli-group [OPTIONS] COMMAND [ARGS]..." in result_main.output
    assert "Zeroth Law Toolkit (zlt)" in result_main.output

    # 2. Test subcommand help
    subcommands = list(cli_module.cli_group.commands.keys())
    print(f"Found subcommands: {subcommands}")
    assert subcommands, "No subcommands found for cli_group after reload"

    for cmd_name in subcommands:
        print(f"Testing help for subcommand: {cmd_name}")
        result_sub = runner.invoke(cli_module.cli_group, [cmd_name, "--help"], catch_exceptions=False)
        print(f"Subcommand '{cmd_name}' help output:\n{result_sub.output}")
        assert result_sub.exit_code == 0, f"zlt {cmd_name} --help failed: {result_sub.output}"
        # Basic check for usage string - adjust based on dynamic command structure
        assert f"Usage: cli-group {cmd_name}" in result_sub.output
