# File: tests/test_cli.py
"""Tests for the command-line interface (cli.py)."""

import importlib
import os
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

# Import the module as cli_module
import src.zeroth_law.cli as cli_module

# Ensure src is in path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent / "src"))


# Helper to get path to CLI test data file
def get_cli_test_data_path(filename: str) -> Path:
    return Path(__file__).parent / "data" / "cli" / filename


def test_restore_hooks_not_git_repo(mocker, tmp_path: Path, caplog):
    """Test restore hooks failure if the target directory isn't a Git repo."""
    # Arrange
    runner = CliRunner()
    # Patch is_dir using mocker to return False
    mock_is_dir = mocker.patch("pathlib.Path.is_dir", return_value=False)

    # Act
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(cli_module.cli_group, ["restore-git-hooks", "--git-root", "."], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 1, f"CLI failed with output: {result.output}"
    # Check the captured log messages instead of stdout/stderr
    # assert "'pre-commit install' failed" in result.output
    assert "'pre-commit install' failed" in caplog.text
    assert "An error occurred during git hook restoration." in caplog.text


def test_zlt_lint_loads_and_runs(tmp_path: Path, mocker):
    """Test that 'zlt lint' correctly loads from config and runs the command."""
    # Arrange: Create a temporary project structure and config
    project_dir = tmp_path / "test_project_pkg"
    project_dir.mkdir()
    src_dir = project_dir / "src"
    src_dir.mkdir()
    zeroth_law_dir = src_dir / "zeroth_law"  # Create the package dir structure
    zeroth_law_dir.mkdir()

    # Create pyproject.toml with a simple echo command for lint
    pyproject_content = """
[tool.poetry]
name = "test-project"
version = "0.1.0"
description = ""
authors = ["Test User <test@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.10"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

# --- Zeroth Law Config ---
[tool.zeroth-law.actions.lint]
description = "Run simple echo lint."
# Define the zlt interface (minimal needed for this test)
zlt_options = { paths = { type = "positional", default = [] } }
# Define the tool(s)
tools = { echo_linter = { command = ["echo", "Linting", "done"], maps_options = {} } }
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    original_cwd = Path.cwd()
    os.chdir(project_dir)  # Change to project root for discovery

    try:
        # Reload the cli module AFTER creating config and changing dir
        importlib.reload(cli_module)

        # Mock subprocess.run to check the arguments passed to it
        mock_run = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b""))

        # Instantiate runner AFTER reloading
        runner = CliRunner(mix_stderr=True)  # Keep mix_stderr for logs if needed

        # Act: Explicitly call the 'lint' subcommand
        result = runner.invoke(cli_module.cli_group, ["lint"], catch_exceptions=False)

    finally:
        # Clean up: Change back to original directory
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"

    # Verify that subprocess.run was called with the expected command
    mock_run.assert_called_once()
    call_args, call_kwargs = mock_run.call_args
    # Command should be ['echo', 'Linting', 'done'] + project_root_path
    expected_command_base = ["echo", "Linting", "done"]
    assert call_args[0][:3] == expected_command_base
    # Check that the project root was passed as the path argument (fallback)
    assert call_args[0][-1] == "."
    assert call_kwargs.get("cwd") == project_dir  # Should run in the temp project dir

    # Remove assertion checking stdout, as we are now mocking subprocess.run
    # assert "Linting done" in result.output
