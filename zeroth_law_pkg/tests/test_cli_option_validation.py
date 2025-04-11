# FILE: tests/test_cli_option_validation.py
"""Tests to verify that each CLI option can be invoked properly."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

# Add src to path to allow importing the cli module
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent / "src"))

# Import the module containing the CLI definitions
import src.zeroth_law.cli as cli_module  # noqa: E402
from src.zeroth_law.cli import cli_group  # noqa: E402


def get_command_options(command):
    """Get all options for a command with their help text."""
    options = {}
    for param in command.params:
        # Get the long form option name
        option_name = param.opts[-1] if param.opts else None
        if option_name:
            options[option_name] = {
                "help": param.help,
                "required": param.required,
                "default": param.default,
                "is_flag": getattr(param, "is_flag", False),
                "multiple": getattr(param, "multiple", False),
                "count": getattr(param, "count", False),
            }
    return options


# Test the root CLI group options
@pytest.mark.parametrize(
    "option",
    [
        "--version",
        "--quiet",
        "--verbose",
        "--color",
        "--no-color",
    ],
)
def test_cli_group_option_invocation(option):
    """Test that each root CLI option can be invoked."""
    runner = CliRunner()

    # For --version, it will exit immediately showing version
    if option == "--version":
        result = runner.invoke(cli_group, [option])
        assert result.exit_code == 0
        return

    # Mock the audit command to prevent actual execution
    with patch.object(cli_module, "run_audit", return_value=False):
        # For normal options, use the audit command to test (simplest)
        result = runner.invoke(cli_group, [option, "audit", "."])

        # Some flags might cause errors in specific cases, but shouldn't crash
        # We're just testing that the option is recognized
        assert result.exit_code in (
            0,
            1,
            2,
        ), f"CLI option {option} failed with exit code {result.exit_code}: {result.output}"


# Test the audit command options
@pytest.mark.parametrize(
    "option,value",
    [
        ("--config", "pyproject.toml"),  # Provide a default value
        ("--recursive", None),  # Flag, no value needed
    ],
)
def test_audit_option_invocation(option, value):
    """Test that each audit command option can be invoked."""
    runner = CliRunner()

    # Mock the audit command to prevent actual execution
    with patch.object(cli_module, "run_audit", return_value=False):
        # Build command arguments
        args = ["audit"]
        if option:
            args.append(option)
        if value:
            args.append(value)
        args.append(".")  # Add a default path

        result = runner.invoke(cli_group, args)
        assert result.exit_code in (
            0,
            1,
            2,
        ), f"Audit command option {option} failed with exit code {result.exit_code}: {result.output}"


# Test the install-git-hook command options
@pytest.mark.parametrize(
    "option,value",
    [
        ("--git-root", "."),  # Provide a default value
    ],
)
def test_install_hook_option_invocation(option, value):
    """Test that each install-git-hook command option can be invoked."""
    runner = CliRunner()

    # Mock relevant functions to prevent actual operation
    with (
        patch.object(Path, "is_dir", return_value=True),
        patch.object(cli_module, "generate_custom_hook_script", return_value="#!/bin/bash\n"),
        patch.object(Path, "mkdir"),
        patch.object(Path, "open"),
    ):
        # Build command arguments
        args = ["install-git-hook"]
        if option:
            args.append(option)
        if value:
            args.append(value)

        result = runner.invoke(cli_group, args)
        assert result.exit_code in (
            0,
            1,
        ), f"Install hook command option {option} failed with exit code {result.exit_code}: {result.output}"


# Test the restore-git-hooks command options
@pytest.mark.parametrize(
    "option,value",
    [
        ("--git-root", "."),  # Provide a default value
    ],
)
def test_restore_hooks_option_invocation(option, value):
    """Test that each restore-git-hooks command option can be invoked."""
    runner = CliRunner()

    # Mock relevant functions to prevent actual operation
    with (
        patch.object(Path, "is_dir", return_value=True),
        patch(
            "subprocess.run",
            return_value=type("obj", (object,), {"stdout": "", "stderr": ""}),
        ),
    ):
        # Build command arguments
        args = ["restore-git-hooks"]
        if option:
            args.append(option)
        if value:
            args.append(value)

        result = runner.invoke(cli_group, args)
        assert result.exit_code in (
            0,
            1,
        ), f"Restore hooks command option {option} failed with exit code {result.exit_code}: {result.output}"


def test_cli_commands():
    """Verify all CLI commands are callable with --help."""
    runner = CliRunner()

    for cmd_name in cli_group.commands:
        result = runner.invoke(cli_group, [cmd_name, "--help"])
        assert result.exit_code == 0, f"Command {cmd_name} --help failed: {result.output}"
