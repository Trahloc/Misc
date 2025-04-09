# FILE: tests/test_cli.py
"""Tests for the command-line interface (cli.py)."""

import os
import stat
import subprocess
import sys
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

from src.zeroth_law.cli import run_audit
from zeroth_law.git_utils import generate_custom_hook_script


# Helper to run the CLI script via subprocess
def run_cli(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Runs the zeroth-law script as a subprocess using the installed script path."""
    env_bin_dir = Path(sys.executable).parent
    script_path = env_bin_dir / "zeroth-law"
    if not script_path.exists():
        raise FileNotFoundError(f"zeroth-law script not found in {env_bin_dir}")

    command = [str(script_path)] + args
    process_env = os.environ.copy()

    # --- Coverage Setup for Subprocess ---
    project_root = Path(__file__).parent.parent  # Assumes tests/ is one level below root
    coverage_rc_path = project_root / "pyproject.toml"
    if coverage_rc_path.exists():
        process_env["COVERAGE_PROCESS_START"] = str(coverage_rc_path)
        # Ensure the source directory is discoverable by the subprocess coverage
        if "PYTHONPATH" in process_env:
            process_env["PYTHONPATH"] = f"{project_root / 'src'}:{process_env['PYTHONPATH']}"
        else:
            process_env["PYTHONPATH"] = str(project_root / "src")
    else:
        print(f"Warning: Coverage config not found at {coverage_rc_path}", file=sys.stderr)
    # -------------------------------------

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd or Path.cwd(),
        env=process_env,
    )


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

    # Act
    result = run_cli(["audit", "src"], cwd=tmp_path)

    # Assert
    assert result.returncode == 0
    assert "Starting audit" in result.stderr
    assert "Found 2 Python files" in result.stderr
    assert "Using configuration" in result.stderr
    assert "Audit Summary" in result.stderr
    assert "Compliant files: 2" in result.stderr
    assert "Project is compliant!" in result.stderr
    assert "Analyzing:" not in result.stderr
    assert result.stdout == ""


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

    # Act
    result = run_cli(["audit", "-q", "src"], cwd=tmp_path)

    # Assert
    assert result.returncode == 1
    assert "Starting audit" not in result.stderr
    assert "Found 2 Python files" not in result.stderr
    assert "Analyzing:" not in result.stderr
    assert "-> Violations found in bad.py: ['footer']" in result.stderr
    assert "Audit Summary" in result.stderr
    assert "Files with violations: 1" in result.stderr
    assert "Detailed Violations:" in result.stderr
    assert "File: bad.py" in result.stderr
    assert result.stdout == ""


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

    # Act
    result = run_cli(["audit", "-vv", "src"], cwd=tmp_path)

    # Assert
    assert result.returncode == 0
    assert "Starting audit" in result.stderr
    assert "Found 2 Python files" in result.stderr
    assert "Analyzing: __init__.py" in result.stderr
    assert "Analyzing: compliant.py" in result.stderr
    assert "Audit Summary" in result.stderr
    assert "Compliant files: 2" in result.stderr
    assert "Project is compliant!" in result.stderr
    assert result.stdout == ""


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
    run_audit(paths_to_check=[project_dir], recursive=True, config=config)

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
    result = run_cli(["install-git-hook", "--help"])
    assert result.returncode == 0
    assert "Install the custom multi-project pre-commit hook script" in result.stdout


def test_cli_install_hook_runs(tmp_path):
    """Test that the install-git-hook command runs (placeholder check)."""
    # Create a fake .git directory to simulate being in a repo
    (tmp_path / ".git").mkdir()
    # Change CWD for the test
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = run_cli(["install-git-hook", "--git-root", "."])
        assert result.returncode == 0
        assert "Placeholder: Would install custom hook" in result.stdout
        assert "Warning: This feature is not yet fully implemented." in result.stdout
    finally:
        os.chdir(original_cwd)


def test_cli_restore_hooks_exists():
    """Test that the restore-git-hooks command exists."""
    result = run_cli(["restore-git-hooks", "--help"])
    assert result.returncode == 0
    assert "Restore the default pre-commit hook script" in result.stdout


def test_cli_restore_hooks_runs(tmp_path):
    """Test that the restore-git-hooks command runs (placeholder check)."""
    # Create a fake .git directory
    (tmp_path / ".git").mkdir()
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = run_cli(["restore-git-hooks", "--git-root", "."])
        assert result.returncode == 0
        assert "Placeholder: Would run pre-commit install" in result.stdout
        assert "Warning: This feature is not yet fully implemented." in result.stdout
    finally:
        os.chdir(original_cwd)


# --- Detailed Tests for install-git-hook ---

# We will use mocker fixture provided by pytest-mock


def test_install_hook_success(mocker, tmp_path):
    """Test successful installation of the custom hook."""
    # Arrange
    mock_git_root = tmp_path
    dot_git_path = mock_git_root / ".git"
    hooks_dir = dot_git_path / "hooks"
    hook_file_path = hooks_dir / "pre-commit"
    expected_script_content = generate_custom_hook_script()  # Get real script content

    # Mock Path operations
    mocker.patch("pathlib.Path.resolve", return_value=mock_git_root)
    mocker.patch("pathlib.Path.is_dir", return_value=True)  # Assume .git exists
    mock_mkdir = mocker.patch("pathlib.Path.mkdir")
    mock_open = mocker.patch("builtins.open", mock.mock_open())
    mock_stat_result = mocker.MagicMock()
    mock_stat_result.st_mode = 0o644  # Some default mode
    mock_stat = mocker.patch("os.stat", return_value=mock_stat_result)
    mock_chmod = mocker.patch("os.chmod")
    # Mock root config check
    mocker.patch("pathlib.Path.is_file", return_value=False)  # Assume no root config initially

    # Act
    result = run_cli(["install-git-hook", "--git-root", str(mock_git_root)])

    # Assert
    assert result.returncode == 0
    mock_mkdir.assert_called_once_with(exist_ok=True)  # Check hooks dir creation
    mock_open.assert_called_once_with(hook_file_path, "w", encoding="utf-8")
    handle = mock_open()
    handle.write.assert_called_once_with(expected_script_content)
    mock_stat.assert_called_once_with(hook_file_path)
    expected_permissions = 0o644 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    mock_chmod.assert_called_once_with(hook_file_path, expected_permissions)
    assert f"Successfully installed Zeroth Law custom pre-commit hook to: {hook_file_path}" in result.stdout
    assert "WARNING: Found" not in result.stderr  # No warning expected


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
    mock_not_git_root = tmp_path
    mocker.patch("pathlib.Path.resolve", return_value=mock_not_git_root)
    # MOCK .git directory DOES NOT exist
    mocker.patch("pathlib.Path.is_dir", return_value=False)
    mock_open = mocker.patch("builtins.open", mock.mock_open())
    mock_chmod = mocker.patch("os.chmod")

    # Act
    result = run_cli(["install-git-hook", "--git-root", str(mock_not_git_root)])

    # Assert
    assert result.returncode != 0  # Should fail
    assert f"Error: Directory '{mock_not_git_root}' does not contain a .git directory." in result.stderr
    mock_open.assert_not_called()  # Should not attempt to write
    mock_chmod.assert_not_called()  # Should not attempt to chmod


# Add more tests below (write error, chmod error etc.)

# --- Detailed Tests for restore-git-hooks ---


def test_restore_hooks_success(mocker, tmp_path):
    """Test successful restoration of default hooks."""
    # Arrange
    mock_git_root = tmp_path
    mocker.patch("pathlib.Path.resolve", return_value=mock_git_root)
    mocker.patch("pathlib.Path.is_dir", return_value=True)  # Assume .git exists
    mock_run = mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="pre-commit installed at .git/hooks/pre-commit", stderr=""),
    )

    # Act
    result = run_cli(["restore-git-hooks", "--git-root", str(mock_git_root)])

    # Assert
    assert result.returncode == 0
    mock_run.assert_called_once_with(
        ["pre-commit", "install"],
        capture_output=True,
        text=True,
        check=True,
        cwd=mock_git_root,
        errors="ignore",
    )
    assert "Successfully restored default pre-commit hooks." in result.stdout
    assert "pre-commit installed at .git/hooks/pre-commit" in result.stdout


def test_restore_hooks_not_git_repo(mocker, tmp_path):
    """Test restore hooks failure if the target directory isn't a Git repo."""
    # Arrange
    mock_not_git_root = tmp_path
    mocker.patch("pathlib.Path.resolve", return_value=mock_not_git_root)
    mocker.patch("pathlib.Path.is_dir", return_value=False)  # .git dir doesn't exist
    mock_run = mocker.patch("subprocess.run")

    # Act
    result = run_cli(["restore-git-hooks", "--git-root", str(mock_not_git_root)])

    # Assert
    assert result.returncode != 0
    assert f"Error: Directory '{mock_not_git_root}' does not contain a .git directory." in result.stderr
    mock_run.assert_not_called()  # Should not attempt to run pre-commit install


def test_restore_hooks_pre_commit_not_found(mocker, tmp_path):
    """Test restore hooks failure if pre-commit command is not found."""
    # Arrange
    mock_git_root = tmp_path
    mocker.patch("pathlib.Path.resolve", return_value=mock_git_root)
    mocker.patch("pathlib.Path.is_dir", return_value=True)  # Assume .git exists
    mock_run = mocker.patch("subprocess.run", side_effect=FileNotFoundError("pre-commit not found"))

    # Act
    result = run_cli(["restore-git-hooks", "--git-root", str(mock_git_root)])

    # Assert
    assert result.returncode != 0
    assert "Error: 'pre-commit' command not found." in result.stderr
    mock_run.assert_called_once()


def test_restore_hooks_pre_commit_install_fails(mocker, tmp_path):
    """Test restore hooks failure if pre-commit install command fails."""
    # Arrange
    mock_git_root = tmp_path
    mocker.patch("pathlib.Path.resolve", return_value=mock_git_root)
    mocker.patch("pathlib.Path.is_dir", return_value=True)  # Assume .git exists
    mock_run = mocker.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, cmd=[], stderr="Install failed"))

    # Act
    result = run_cli(["restore-git-hooks", "--git-root", str(mock_git_root)])

    # Assert
    assert result.returncode != 0
    assert "Error running 'pre-commit install': Install failed" in result.stderr
    mock_run.assert_called_once()


# Add more tests below if needed

# <<< ZEROTH LAW FOOTER >>>
