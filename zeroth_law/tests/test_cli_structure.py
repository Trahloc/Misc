# FILE: tests/test_cli_structure.py
"""Tests for the structure and definition of CLI commands and options.

This uses introspection on the Click objects to verify the expected interface,
rather than parsing --help output. This ensures that if the CLI definition
changes in cli.py, these tests will fail, prompting an update.
"""

from pathlib import Path

import click
import pytest

# Assuming src is importable or handled by pytest paths/PYTHONPATH
from zeroth_law import cli as cli_module

# Define helper function or fixtures if needed


def get_command_params(command: click.Command | click.Group) -> dict[str, click.Parameter]:
    """Extract parameters (options and args) into a name-keyed dict."""
    return {p.name: p for p in command.params}


# --- Tests ---


def test_cli_root_command():
    """Verify the main cli object is a Group."""
    assert isinstance(cli_module.cli, click.Group)


def test_cli_root_options():
    """Verify expected options directly on the root cli command."""
    params = get_command_params(cli_module.cli)

    # Check existence
    assert "quiet" in params
    assert "verbose" in params
    assert "debug" in params

    # Check types and properties (examples)
    assert isinstance(params["quiet"], click.Option)
    assert params["quiet"].is_flag
    assert params["quiet"].opts == ["-q", "--quiet"]
    assert params["quiet"].help is not None

    assert isinstance(params["verbose"], click.Option)
    assert params["verbose"].is_flag
    assert params["verbose"].opts == ["-v", "--verbose"]
    assert params["verbose"].help is not None

    assert isinstance(params["debug"], click.Option)
    assert params["debug"].is_flag
    assert params["debug"].opts == ["-vv", "--debug"]
    assert params["debug"].help is not None


def test_cli_root_subcommands():
    """Verify expected subcommands are registered."""
    assert "audit" in cli_module.cli.commands
    assert "install-git-hook" in cli_module.cli.commands
    assert "restore-git-hooks" in cli_module.cli.commands


# Add tests for subcommands below


def test_audit_command_structure():
    """Verify the structure of the 'audit' subcommand."""
    audit_cmd = cli_module.cli.commands.get("audit")
    assert audit_cmd is not None
    assert isinstance(audit_cmd, click.Command)

    params = get_command_params(audit_cmd)

    # Check Arguments
    assert "paths" in params
    assert isinstance(params["paths"], click.Argument)
    assert params["paths"].nargs == -1  # Expects 0 or more

    # Check Options (add more as needed)
    assert "config" in params
    assert isinstance(params["config"], click.Option)
    assert params["config"].opts == ["-c", "--config"]
    assert params["config"].help is not None

    assert "exclude_dir" in params
    assert isinstance(params["exclude_dir"], click.Option)
    assert params["exclude_dir"].opts == ["-e", "--exclude-dir"]
    assert params["exclude_dir"].multiple  # Can be specified multiple times

    assert "exclude_file" in params
    assert isinstance(params["exclude_file"], click.Option)
    assert params["exclude_file"].opts == ["-E", "--exclude-file"]
    assert params["exclude_file"].multiple

    assert "recursive" in params
    assert isinstance(params["recursive"], click.Option)
    assert params["recursive"].opts == ["-r", "--recursive"]
    assert params["recursive"].is_flag

    assert "fix" in params
    assert isinstance(params["fix"], click.Option)
    assert params["fix"].opts == ["--fix"]
    assert params["fix"].is_flag

    assert "report_format" in params
    assert isinstance(params["report_format"], click.Option)
    assert params["report_format"].opts == ["--report-format"]


# Add tests for install-git-hook and restore-git-hooks below


def test_install_hook_command_structure():
    """Verify the structure of the 'install-git-hook' subcommand."""
    cmd = cli_module.cli.commands.get("install-git-hook")
    assert cmd is not None
    assert isinstance(cmd, click.Command)
    params = get_command_params(cmd)

    assert "git_root" in params
    assert isinstance(params["git_root"], click.Option)
    assert params["git_root"].opts == ["--git-root"]
    assert params["git_root"].default == "."
    assert params["git_root"].help is not None


def test_restore_hooks_command_structure():
    """Verify the structure of the 'restore-git-hooks' subcommand."""
    cmd = cli_module.cli.commands.get("restore-git-hooks")
    assert cmd is not None
    assert isinstance(cmd, click.Command)
    params = get_command_params(cmd)

    assert "git_root" in params
    assert isinstance(params["git_root"], click.Option)
    assert params["git_root"].opts == ["--git-root"]
    assert params["git_root"].default == "."
    assert params["git_root"].help is not None
