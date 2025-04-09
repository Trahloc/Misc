# FILE: tests/test_cli.py
"""Tests for the command-line interface (cli.py)."""

import os
import stat
import sys
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.zeroth_law.cli import cli_group, run_audit
from zeroth_law.git_utils import generate_custom_hook_script

# Common compliant content for __init__.py in tests
INIT_PY_CONTENT = """# FILE: __init__.py
\"\"\"Test Source Package Init.\"\"\"
# <<< ZEROTH LAW FOOTER >>>
"""


# Test Case 1: Default Output (No Flags)
def test_cli_default_output(tmp_path: Path) -> None:
    """Test the default output level (expect INFO like behavior)."""
    # Arrange
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text(INIT_PY_CONTENT)
    compliant_content = """# FILE: src/compliant.py
\"\"\"Module docstring.\"\"\"
# <<< ZEROTH LAW FOOTER >>>
"""
    (tmp_path / "src" / "compliant.py").write_text(compliant_content)
    (tmp_path / "pyproject.toml").touch()

    runner = CliRunner()
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(cli_group, ["audit", "src"], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    assert "Starting audit" in result.output
    assert "Found 2 Python files" in result.output
    assert "Using configuration" in result.output
    assert "Audit Summary" in result.output
    assert "Compliant files: 2" in result.output
    assert "Project is compliant!" in result.output
    assert "Analyzing:" not in result.output


# Test Case 2: Quiet Output (-q)
def test_cli_quiet_output(tmp_path: Path) -> None:
    """Test the quiet output level (-q)."""
    # Arrange
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text(INIT_PY_CONTENT)
    non_compliant_content = """# FILE: src/bad.py
\"\"\"Module docstring.\"\"\"
# No footer here
"""
    (tmp_path / "src" / "bad.py").write_text(non_compliant_content)
    pyproject_content = """[tool.poetry]
name = "test"
version = "0.1.0"
description = ""
authors = [""]
[tool.zeroth-law]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    runner = CliRunner()
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(cli_group, ["audit", "-q", "src"], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 1, f"CLI failed with output: {result.output}"
    assert "Starting audit" not in result.output
    assert "Found 2 Python files" not in result.output
    assert "Analyzing:" not in result.output
    assert "-> Violations found in bad.py: ['footer']" in result.output
    assert "Audit Summary" in result.output
    assert "Files with violations: 1" in result.output
    assert "Detailed Violations:" in result.output
    assert "File: bad.py" in result.output


# Test Case 3: Debug Output (-vv)
def test_cli_debug_output(tmp_path: Path) -> None:
    """Test the debug output level (-vv)."""
    # Arrange
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text(INIT_PY_CONTENT)
    compliant_content = """# FILE: src/compliant.py
\"\"\"Module docstring.\"\"\"
# <<< ZEROTH LAW FOOTER >>>
"""
    (tmp_path / "src" / "compliant.py").write_text(compliant_content)
    (tmp_path / "pyproject.toml").touch()

    runner = CliRunner()
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(cli_group, ["audit", "-vv", "src"], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    assert "Starting audit" in result.output
    assert "Found 2 Python files" in result.output
    assert "Analyzing: __init__.py" in result.output
    assert "Analyzing: compliant.py" in result.output
    assert "Audit Summary" in result.output
    assert "Compliant files: 2" in result.output
    assert "Project is compliant!" in result.output


# TODO: Add test_cli_verbose_output (might be same as default for now)
# TODO: Add test_cli_version
# TODO: Add test_cli_file_not_found


# New Test Case for run_audit parameter passing
@patch("src.zeroth_law.cli.analyze_file_compliance")
def test_run_audit_calls_analyzer_with_all_params(mock_analyzer: MagicMock, tmp_path: Path) -> None:
    """Verify run_audit calls analyze_file_compliance with all required parameters."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "test.py").write_text("# Test file")  # Dummy file

    # Sample config including the parameters
    config = {
        "max_complexity": 15,
        "max_lines": 150,
        "max_parameters": 7,
        "max_statements": 70,
        "exclude_dirs": [],
        "exclude_files": [],
    }

    # Mock the return value of the analyzer to avoid issues if it returns None etc.
    mock_analyzer.return_value = {}

    # Act
    # Pass project_dir as a list to paths_to_check and set recursive=True
    run_audit(paths_to_check=[project_dir], recursive=True, config=config, analyzer_func=mock_analyzer)

    # Assert
    mock_analyzer.assert_called()  # Check if it was called at all
    call_args, call_kwargs = mock_analyzer.call_args
    # call_args[0] should be the Path object for test.py
    assert isinstance(call_args[0], Path)
    assert call_args[0].name == "test.py"

    # Check that the necessary config values were passed as keyword arguments
    assert call_kwargs.get("max_complexity") == config["max_complexity"]
    assert call_kwargs.get("max_lines") == config["max_lines"]
    assert call_kwargs.get("max_params") == config["max_parameters"]
    assert call_kwargs.get("max_statements") == config["max_statements"]


# --- Tests for Git Hook Management Commands ---


def test_cli_install_hook_exists():
    """Test that the install-git-hook command exists."""
    runner = CliRunner()
    result = runner.invoke(cli_group, ["install-git-hook", "--help"], catch_exceptions=False)
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    assert "Install the custom multi-project pre-commit hook script" in result.output


def test_cli_install_hook_runs(mock_install: MagicMock, tmp_path):
    """Test that the install-git-hook command runs (placeholder check)."""
    # Create a fake .git directory to simulate being in a repo
    (tmp_path / ".git").mkdir()
    # Change CWD for the test
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    runner = CliRunner()
    try:
        result = runner.invoke(cli_group, ["install-git-hook", "--git-root", "."], catch_exceptions=False)
        assert result.exit_code == 0, f"CLI failed with output: {result.output}"
        mock_install.assert_called_once_with(git_root_dir=tmp_path)
    finally:
        os.chdir(original_cwd)


def test_cli_restore_hooks_exists():
    """Test that the restore-git-hooks command exists."""
    runner = CliRunner()
    result = runner.invoke(cli_group, ["restore-git-hooks", "--help"], catch_exceptions=False)
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    assert "Restore the default pre-commit hook script" in result.output


def test_cli_restore_hooks_runs(mock_restore: MagicMock, tmp_path):
    """Test that the restore-git-hooks command runs (placeholder check)."""
    # Create a fake .git directory
    (tmp_path / ".git").mkdir()
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    runner = CliRunner()
    try:
        result = runner.invoke(cli_group, ["restore-git-hooks", "--git-root", "."], catch_exceptions=False)
        assert result.exit_code == 0, f"CLI failed with output: {result.output}"
        mock_restore.assert_called_once_with(git_root_dir=tmp_path)
    finally:
        os.chdir(original_cwd)


# --- Detailed Tests for install-git-hook ---

# We will use mocker fixture provided by pytest-mock


def test_install_hook_success(mock_is_dir: MagicMock, mock_exists: MagicMock, mock_open: MagicMock, mock_chmod: MagicMock, tmp_path: Path):
    """Test successful installation of the custom hook."""
    # Arrange
    runner = CliRunner()
    git_root = tmp_path
    hooks_dir = git_root / ".git" / "hooks"
    pre_commit_hook_path = hooks_dir / "pre-commit"
    expected_script_content = generate_custom_hook_script()  # Get real script content

    # Mock Path operations
    mock_is_dir.return_value = True
    mock_exists.return_value = True
    mock_open.return_value = mock.mock_open()
    mock_chmod.return_value = None

    # Act
    original_cwd = Path.cwd()
    os.chdir(git_root)
    try:
        result = runner.invoke(cli_group, ["install-git-hook", "--git-root", "."], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    assert f"Ensuring hooks directory exists: {hooks_dir}" in result.output
    assert f"Installing custom pre-commit hook to {pre_commit_hook_path}" in result.output
    assert f"Custom pre-commit hook installed successfully to {pre_commit_hook_path}" in result.output

    # Check that .git and .git/hooks were checked for existence/type
    mock_is_dir.assert_any_call()
    assert mock_is_dir.call_args_list[0].args[0] == git_root / ".git"

    # Check that the hook file was opened for writing
    mock_open.assert_called_once_with(pre_commit_hook_path, "w", encoding="utf-8")
    # Check that the generated script content was written
    handle = mock_open()
    handle.write.assert_called_once_with(expected_script_content)

    # Check that chmod was called to make the hook executable
    mock_chmod.assert_called_once_with(pre_commit_hook_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


def test_install_hook_warning_on_root_config(mocker, tmp_path):
    """Test that a warning is shown if a root config file exists."""
    # Arrange
    mock_git_root = tmp_path
    dot_git_path = mock_git_root / ".git"
    hooks_dir = dot_git_path / "hooks"
    hook_file_path = hooks_dir / "pre-commit"
    expected_script_content = generate_custom_hook_script()

    # Mock Path operations
    mocker.patch("pathlib.Path.resolve", return_value=mock_git_root)
    mocker.patch("pathlib.Path.is_dir", return_value=True)  # Assume .git exists
    mocker.patch("pathlib.Path.mkdir")
    mocker.patch("builtins.open", mock.mock_open())
    mock_stat_result = mocker.MagicMock()
    mock_stat_result.st_mode = 0o644
    mocker.patch("os.stat", return_value=mock_stat_result)
    mocker.patch("os.chmod")

    # MOCK ROOT CONFIG EXISTS
    # Need to make Path("...").is_file() return True only for the root config path check
    def mock_is_file(path_obj):
        if path_obj == mock_git_root / ".pre-commit-config.yaml":
            return True
        return False

    mocker.patch("pathlib.Path.is_file", side_effect=mock_is_file)

    # Act
    result = run_cli(["install-git-hook", "--git-root", str(mock_git_root)])

    # Assert
    assert result.returncode == 0  # Command still succeeds
    assert f"Successfully installed Zeroth Law custom pre-commit hook to: {hook_file_path}" in result.stdout
    # Check for specific warning text in stderr
    assert "WARNING: Found '.pre-commit-config.yaml' at the Git root." in result.stderr
    assert "Consider running: zeroth-law restore-git-hooks" in result.stderr


def test_install_hook_not_git_repo(mocker, tmp_path):
    """Test install hook failure if the target directory isn't a Git repo."""
    # Arrange
    mock_git_root = tmp_path
    mocker.patch("pathlib.Path.resolve", return_value=mock_git_root)
    # Mock is_dir to return False specifically when checking for '.git'
    mocker.patch("pathlib.Path.is_dir", side_effect=lambda p: p.name != ".git")

    # Act
    result = run_cli(["install-git-hook", "--git-root", str(mock_git_root)])

    # Assert
    assert result.returncode != 0  # Should exit with error
    assert f"Error: Directory '{mock_git_root}' does not contain a .git directory." in result.stderr


# Add more tests below (write error, chmod error etc.)

# --- Detailed Tests for restore-git-hooks ---


def test_restore_hooks_success(mock_is_dir: MagicMock, mock_subprocess_run: MagicMock, tmp_path: Path):
    """Test successful restoration of default hooks."""
    # Arrange
    runner = CliRunner()
    git_root = tmp_path
    (git_root / ".git").mkdir()  # Need .git dir for the check

    # Simulate successful subprocess run
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="pre-commit installed", stderr="")

    # Act
    original_cwd = Path.cwd()
    os.chdir(git_root)
    try:
        result = runner.invoke(cli_group, ["restore-git-hooks", "--git-root", "."], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    assert "Attempting to restore default hooks using 'pre-commit install'" in result.output
    assert "pre-commit installed" in result.output  # Check stdout from mock
    assert "Default git hooks restored successfully." in result.output

    mock_is_dir.assert_called_once_with(git_root / ".git")
    mock_subprocess_run.assert_called_once_with(
        ["pre-commit", "install"],
        capture_output=True,
        text=True,
        check=True,
        cwd=git_root,
        errors="ignore",
    )


def test_restore_hooks_not_git_repo(mock_is_dir: MagicMock, tmp_path: Path):
    """Test restore hooks failure if the target directory isn't a Git repo."""
    # Arrange
    runner = CliRunner()
    mock_not_git_root = tmp_path
    mocker.patch("pathlib.Path.resolve", return_value=mock_not_git_root)
    # Mock is_dir to return False, simulating missing .git
    mocker.patch("pathlib.Path.is_dir", return_value=False)

    # Act
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(cli_group, ["restore-git-hooks", "--git-root", "."], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 1, f"CLI failed with output: {result.output}"
    assert f"Error: Not a git repository (or .git directory missing): {tmp_path}" in result.output
    mock_is_dir.assert_called_once_with(tmp_path / ".git")


def test_restore_hooks_pre_commit_not_found(mock_is_dir: MagicMock, mock_subprocess_run: MagicMock, tmp_path: Path):
    """Test restore hooks failure if pre-commit command is not found."""
    # Arrange
    runner = CliRunner()
    git_root = tmp_path
    (git_root / ".git").mkdir()

    # Simulate FileNotFoundError
    mock_subprocess_run.side_effect = FileNotFoundError("No such file or directory: 'pre-commit'")

    # Act
    original_cwd = Path.cwd()
    os.chdir(git_root)
    try:
        result = runner.invoke(cli_group, ["restore-git-hooks", "--git-root", "."], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 1, f"CLI failed with output: {result.output}"
    assert "Error: 'pre-commit' command not found." in result.output
    assert "Please install pre-commit" in result.output

    mock_is_dir.assert_called_once_with(git_root / ".git")
    mock_subprocess_run.assert_called_once_with(
        ["pre-commit", "install"],
        capture_output=True,
        text=True,
        check=True,
        cwd=git_root,
        errors="ignore",
    )


def test_restore_hooks_pre_commit_install_fails(mock_is_dir: MagicMock, mock_subprocess_run: MagicMock, tmp_path: Path):
    """Test restore hooks failure if pre-commit install command fails."""
    # Arrange
    runner = CliRunner()
    git_root = tmp_path
    (git_root / ".git").mkdir()

    # Simulate subprocess failure
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["pre-commit", "install"], stderr="Install failed")

    # Act
    original_cwd = Path.cwd()
    os.chdir(git_root)
    try:
        result = runner.invoke(cli_group, ["restore-git-hooks", "--git-root", "."], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 1, f"CLI failed with output: {result.output}"
    assert "Error running 'pre-commit install': Install failed" in result.output

    mock_is_dir.assert_called_once_with(git_root / ".git")
    mock_subprocess_run.assert_called_once_with(
        ["pre-commit", "install"],
        capture_output=True,
        text=True,
        check=True,
        cwd=git_root,
        errors="ignore",
    )


# Add more tests below if needed

# <<< ZEROTH LAW FOOTER >>>
