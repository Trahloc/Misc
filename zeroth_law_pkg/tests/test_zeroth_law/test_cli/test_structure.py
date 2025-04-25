# FILE: tests/test_cli_structure.py
"""Tests for the structure and definition of the CLI commands and options."""

import importlib
import sys
from pathlib import Path

import click

# Add src to path to allow importing the cli module
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent / "src"))

# Import the module containing the CLI definitions
import src.zeroth_law.cli as cli_module  # noqa: E402


# Helper function to get parameters from a Click command/group
def get_command_params(command: click.Command) -> dict[str, click.Parameter]:
    """Extracts parameters (options, arguments) from a Click command."""
    return {p.name: p for p in command.params}


# --- Test Cases ---


def test_cli_group_exists():
    """Verify the main cli group function exists."""
    assert hasattr(cli_module, "cli_group")
    assert isinstance(cli_module.cli_group, click.Group)


def test_cli_root_options():
    """Verify expected options directly on the root cli command."""
    params = get_command_params(cli_module.cli_group)
    assert "version" in params
    assert "quiet" in params
    assert "verbosity" in params
    assert "color" in params

    # Check some option details
    assert params["version"].opts == ["--version"]
    assert params["quiet"].opts == ["-q", "--quiet"]
    assert params["quiet"].is_flag
    assert params["verbosity"].opts == ["-v", "--verbose"]
    assert params["verbosity"].count is True
    assert params["color"].opts == ["--color"]


# Remove obsolete tests for the old 'audit' command
# def test_audit_command_exists():
#     """Verify the audit command exists within the cli group."""
#     assert "audit" in cli_module.cli_group.commands
#
#
# def test_audit_command_options():
#     """Verify expected options and arguments on the audit command."""
#     audit_cmd = cli_module.cli_group.commands["audit"]
#     params = get_command_params(audit_cmd)
#
#     # Check options
#     assert "config" in params
#     assert "recursive" in params
#
#     # Check argument
#     assert "paths" in params
#     assert params["paths"].nargs == -1 # Corresponds to '*'


def test_install_hook_command_exists():
    """Verify the install-git-hook command exists."""
    importlib.reload(cli_module)
    assert "install-git-hook" in cli_module.cli_group.commands
    assert isinstance(cli_module.cli_group.commands["install-git-hook"], click.Command)


def test_install_hook_options():
    """Verify options for install-git-hook command."""
    importlib.reload(cli_module)
    cmd = cli_module.cli_group.commands["install-git-hook"]
    params = get_command_params(cmd)
    assert "git_root" in params
    assert params["git_root"].opts == ["--git-root"]
    assert params["git_root"].default is None


def test_restore_hooks_command_exists():
    """Verify the restore-git-hooks command exists."""
    importlib.reload(cli_module)
    assert "restore-git-hooks" in cli_module.cli_group.commands
    assert isinstance(cli_module.cli_group.commands["restore-git-hooks"], click.Command)


def test_restore_hooks_options():
    """Verify options for restore-git-hooks command."""
    importlib.reload(cli_module)
    cmd = cli_module.cli_group.commands["restore-git-hooks"]
    params = get_command_params(cmd)
    assert "git_root" in params
    assert params["git_root"].opts == ["--git-root"]
    assert params["git_root"].default is None


# <<< ZEROTH LAW FOOTER >>>
