"""Tests for the command-line interface (cli.py)."""

import os
import stat
import subprocess
import sys
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.zeroth_law.cli import cli_group, run_audit
from zeroth_law.git_utils import generate_custom_hook_script

# Ensure src is in path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent / "src"))


# Helper to get path to CLI test data file
def get_cli_test_data_path(filename: str) -> Path:
    return Path(__file__).parent / "data" / "cli" / filename


def test_restore_hooks_not_git_repo(mocker, tmp_path: Path):
    """Test restore hooks failure if the target directory isn't a Git repo."""
    # Arrange
    runner = CliRunner()
    # Patch is_dir using mocker to return False
    mock_is_dir = mocker.patch("pathlib.Path.is_dir", return_value=False)

    # Act
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(cli_group, ["restore-git-hooks", "--git-root", "."], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 1, f"CLI failed with output: {result.output}"
    assert f"Error: Directory '{tmp_path}' does not contain a .git directory." in result.output
