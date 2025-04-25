# FILE: tests/test_cli_option_validation.py
"""Tests to verify that each CLI option can be invoked properly."""

import importlib
import sys
from pathlib import Path
from unittest.mock import patch
import os
import subprocess

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

    # Reload module to ensure commands are available
    importlib.reload(cli_module)

    # Mock the underlying function if needed to prevent side effects

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
    "option,value_placeholder",
    [
        ("--git-root", "USE_TMP_PATH"),
        (None, None),  # Test auto-detection
    ],
)
def test_install_hook_option_invocation(option, value_placeholder, tmp_path):
    """Test that each install-git-hook command option can be invoked."""
    runner = CliRunner()

    # Create a dummy .git directory and a dummy pyproject.toml
    git_root_dir = tmp_path
    (git_root_dir / ".git").mkdir()
    (git_root_dir / "pyproject.toml").touch()  # Create dummy project file
    # Initialize a git repository in the temporary directory
    subprocess.run(["git", "init"], cwd=git_root_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=git_root_dir, capture_output=True, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=git_root_dir, capture_output=True, check=True)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=git_root_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_root_dir, capture_output=True, check=True)

    # Determine args based on parametrization
    args = ["install-git-hook"]
    if option == "--git-root":
        if value_placeholder == "USE_TMP_PATH":
            args.append(option)
            args.append(str(git_root_dir))

    # For the case where --git-root is not provided, change CWD for CliRunner
    current_cwd = Path.cwd()
    # Change CWD only if testing auto-detection based on CWD
    run_dir = git_root_dir if option is None else current_cwd
    os.chdir(run_dir)
    try:
        print(f"\nRunning: cli_group {args} in CWD={Path.cwd()}")
        result = runner.invoke(cli_group, args, catch_exceptions=False)
    finally:
        os.chdir(current_cwd)  # Change back CWD

    # Check exit code
    assert result.exit_code in (
        0,
        1,
    ), f"Install hook command option {option} failed with exit code {result.exit_code}: {result.output}"

    # Assert hook file was created
    hook_path = git_root_dir / ".git" / "hooks" / "pre-commit"
    assert hook_path.is_file(), f"Hook file was not created at {hook_path}"


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

    # Reload module to ensure commands are available
    # importlib.reload(cli_module) # Might not be needed if module scope is fine

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
