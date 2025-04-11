"""Tests for the command-line interface (cli.py)."""

import os
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from src.zeroth_law.cli import cli_group
from src.zeroth_law.path_utils import find_project_root

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
    assert "Error: Not a Git repository or git command failed\n" in result.output


def test_zlt_lint_calls_runner(mocker, tmp_path: Path):
    """Test that 'zlt lint' calls the underlying subprocess for linting."""
    # Arrange
    runner = CliRunner()
    real_project_root = find_project_root(Path.cwd())

    # Mock subprocess.run within the actions.lint.python module
    # to simulate a successful linter execution without actually running it.
    mock_subprocess = mocker.patch(
        "src.zeroth_law.actions.lint.python.subprocess.run",
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )

    # Mock config loading / project root finding as before
    mocker.patch("src.zeroth_law.cli.find_project_root", return_value=real_project_root)
    mocker.patch(
        "src.zeroth_law.cli.find_pyproject_toml",
        return_value=real_project_root / "pyproject.toml",
    )
    mocker.patch("src.zeroth_law.cli.load_config", return_value={"some_config": True})

    # Act
    # Explicitly call the 'lint' subcommand
    result = runner.invoke(cli_group, ["lint"], catch_exceptions=False)

    # Assert
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"

    # Verify that subprocess.run was called (meaning run_python_lint executed it)
    mock_subprocess.assert_called_once()
    # Optionally, check the command arguments if needed:
    # args, kwargs = mock_subprocess.call_args
    # assert args[0][0:4] == ["poetry", "run", "ruff", "check"]
    # assert kwargs["cwd"] == real_project_root
