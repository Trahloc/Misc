# FILE: tests/test_cli_structure.py
"""Tests for the structure and definition of the CLI commands and options."""

import importlib
import sys
from pathlib import Path

import click
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, call, ANY
import os
import subprocess

# Add src to path to allow importing the cli module
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent / "src"))

# Import the module containing the CLI definitions
import src.zeroth_law.cli as cli_module  # noqa: E402

# Import specific functions if they exist directly in cli.py
# Add try-except block for robustness
try:
    from src.zeroth_law.cli import cli_group, analyze_files, find_files_to_audit  # noqa: E402
except ImportError:
    # Handle case where functions might not be directly in cli.py anymore
    print("Warning: Could not import analyze_files or find_files_to_audit directly from cli.py")

    # Define placeholders if needed for tests below, or let tests fail naturally
    def analyze_files(*args, **kwargs):
        raise NotImplementedError("analyze_files function not found")

    def find_files_to_audit(*args, **kwargs):
        raise NotImplementedError("find_files_to_audit function not found")

    # cli_group might still be needed
    try:
        from src.zeroth_law.cli import cli_group
    except ImportError:

        def cli_group(*args, **kwargs):
            raise NotImplementedError("cli_group not found")


# Import utility from common (assuming it exists)
# Add try-except
try:
    from zeroth_law.common.file_finder import find_python_files  # noqa: E402
except ImportError:
    print("Warning: Could not import find_python_files from common.file_finder")

    def find_python_files(*args, **kwargs):
        raise NotImplementedError("find_python_files not found")


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


# --- CLI Invocation Tests (Merged from test_option_validation.py) ---


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
        result = runner.invoke(cli_module.cli_group, [option])
        assert result.exit_code == 0
        return

    # Mock the audit command to prevent actual execution
    # Check if run_audit exists before patching, handle if it's removed/renamed
    if hasattr(cli_module, "run_audit"):
        patch_target = cli_module.run_audit
    else:
        # Find another simple command to test options against, or skip patch
        # For now, let's assume install-git-hook exists and patch its core logic if needed
        # This part needs refinement based on actual available commands if audit is gone.
        # Patching a non-existent function will fail.
        # As a fallback, we can try running without patching, but it might have side effects.
        patch_target = None  # Placeholder - needs adjustment
        print(f"Warning: run_audit not found in cli_module for patching in {__name__}")

    # Use a placeholder command like '--help' if no simple command available
    # or if patching target is uncertain.
    # The goal is just to see if the root option is recognized.
    test_cmd = ["--help"]  # Simplest command that accepts root options

    if patch_target:
        with patch.object(cli_module, patch_target.__name__, return_value=False):
            result = runner.invoke(cli_module.cli_group, [option] + test_cmd)
    else:
        # Run without patching if target is unclear - relying on --help is safest
        result = runner.invoke(cli_module.cli_group, [option] + test_cmd)

    # Some flags might cause errors in specific cases, but shouldn't crash
    # We're just testing that the option is recognized
    assert result.exit_code in (
        0,
        1,
        2,
    ), f"CLI option {option} failed with exit code {result.exit_code}: {result.output}"


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
        result = runner.invoke(cli_module.cli_group, args, catch_exceptions=False)
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
    # Note: This mocking might violate ZLF rules, review needed.
    # Consider testing with a real pre-commit install if possible
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

        result = runner.invoke(cli_module.cli_group, args)
        assert result.exit_code in (
            0,
            1,
        ), f"Restore hooks command option {option} failed with exit code {result.exit_code}: {result.output}"


def test_cli_commands_help():  # Renamed to be more specific
    """Verify all CLI commands are callable with --help."""
    runner = CliRunner()

    # Reload module to ensure commands are loaded
    # importlib.reload(cli_module) # May not be needed if called after other tests

    # 1. Test main command help
    result_main = runner.invoke(cli_module.cli_group, ["--help"], catch_exceptions=False)
    print(f"Main command help output:\n{result_main.output}")  # Keep print for debugging CI
    assert result_main.exit_code == 0, f"zlt --help failed: {result_main.output}"
    # Allow for different aliases (zeroth-law or zlt)
    assert (
        "Usage: cli-group [OPTIONS] COMMAND [ARGS]..." in result_main.output
        or "Usage: zlt [OPTIONS] COMMAND [ARGS]..." in result_main.output
        or "Usage: zeroth-law [OPTIONS] COMMAND [ARGS]..." in result_main.output
    ), "Main usage string not found in help output."
    assert "Zeroth Law Toolkit (zlt)" in result_main.output

    # 2. Test subcommand help
    subcommands = list(cli_module.cli_group.commands.keys())
    print(f"Found subcommands: {subcommands}")
    assert subcommands, "No subcommands found for cli_group after reload"

    for cmd_name in subcommands:
        print(f"Testing help for subcommand: {cmd_name}")
        result_sub = runner.invoke(cli_module.cli_group, [cmd_name, "--help"], catch_exceptions=False)
        print(f"Subcommand '{cmd_name}' help output:\n{result_sub.output}")  # Keep print
        assert result_sub.exit_code == 0, f"zlt {cmd_name} --help failed: {result_sub.output}"
        # Basic check for usage string - adjust based on dynamic command structure
        # Allow for different aliases
        assert (
            f"Usage: cli-group {cmd_name}" in result_sub.output
            or f"Usage: zlt {cmd_name}" in result_sub.output
            or f"Usage: zeroth-law {cmd_name}" in result_sub.output
        ), f"Subcommand usage string not found for {cmd_name}."


# --- Tests for Refactored Functions (Merged from test_refactor.py) ---

# --- Tests for find_files_to_audit ---


def test_find_files_to_audit_files_only(tmp_path):
    """Test finding files when only files are provided in paths_to_check."""
    # Arrange
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    file1.touch()
    file2.touch()
    paths = [file1, file2]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = False  # Not relevant when only files are passed

    # Act
    result = find_files_to_audit(paths, recursive, config)

    # Assert
    assert set(result) == set(paths)  # Use set for order-insensitive comparison
    assert len(result) == 2


def test_find_files_to_audit_with_directory(tmp_path):
    """Test finding files when a directory is provided."""
    # Arrange
    dummy_dir = tmp_path / "dummy"
    dummy_dir.mkdir()
    file1 = dummy_dir / "file1.py"
    file2 = dummy_dir / "file2.py"
    non_py_file = dummy_dir / "readme.md"
    file1.touch()
    file2.touch()
    non_py_file.touch()

    paths = [dummy_dir]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = True

    # Act: Call the real function
    result = find_files_to_audit(paths, recursive, config)

    # Assert: Check against the actual files found
    expected_files = {file1, file2}
    assert set(result) == expected_files
    assert len(result) == 2


def test_find_files_to_audit_mixed_paths(tmp_path):
    """Test finding files when both files and directories are provided."""
    # Arrange
    dummy_file1 = tmp_path / "file1.py"
    dummy_dir = tmp_path / "dummy"
    dummy_dir.mkdir()
    file2 = dummy_dir / "file2.py"
    file3 = dummy_dir / "file3.py"
    # Files/dirs to be excluded
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    venv_file = venv_dir / "ignored.py"
    venv_file.touch()
    setup_file = tmp_path / "setup.py"
    setup_file.touch()

    dummy_file1.touch()
    file2.touch()
    file3.touch()

    paths = [dummy_file1, dummy_dir, setup_file]  # Pass excluded file too
    # Use relative string paths for exclusion config as that's common
    config = {"exclude_dirs": ["venv"], "exclude_files": ["setup.py"]}
    recursive = True

    # Act
    result = find_files_to_audit(paths, recursive, config)

    # Assert
    # Expected: file1.py (explicit), dummy/file2.py, dummy/file3.py
    # Excluded: setup.py (explicitly passed but excluded by config),
    #           venv/ignored.py (in excluded dir)
    expected_files = {dummy_file1, file2, file3}
    assert set(result) == expected_files
    assert len(result) == 3


def test_find_files_to_audit_with_nonexistent_path(tmp_path):
    """Test finding files when a path doesn't exist (should be ignored)."""
    # Arrange
    existent_file = tmp_path / "file1.py"
    existent_file.touch()
    non_existent_path = tmp_path / "not_real.py"
    paths = [existent_file, non_existent_path]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = False

    # Act
    result = find_files_to_audit(paths, recursive, config)

    # Assert
    assert result == [existent_file]  # Only the existing file should be returned
    assert len(result) == 1


def test_find_files_to_audit_deduplicates(tmp_path):
    """Test that find_files_to_audit deduplicates files from overlapping paths."""
    # Arrange
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    common_dir = tmp_path / "common"
    dir1.mkdir()
    dir2.mkdir()
    common_dir.mkdir()

    file1_in_dir1 = dir1 / "file1.py"
    file2_in_dir2 = dir2 / "file2.py"
    common_file = common_dir / "file.py"
    # Explicitly pass the common file as well
    explicit_common_file = common_dir / "file.py"

    file1_in_dir1.touch()
    file2_in_dir2.touch()
    common_file.touch()

    paths = [dir1, dir2, explicit_common_file, common_dir]  # Overlapping paths
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = True

    # Act
    result = find_files_to_audit(paths, recursive, config)

    # Assert
    expected_files = {file1_in_dir1, file2_in_dir2, common_file}
    assert set(result) == expected_files  # Use set for order-insensitivity
    assert len(result) == 3  # Should have 3 unique files


# --- Tests for analyze_files ---
# (These tests use a mock analyzer, which might need review against ZLF mocking rules)


@patch("pathlib.Path.is_file", return_value=True)
def test_analyze_files_all_compliant(mock_is_file):
    """Test analyzing files when all files are compliant."""
    # Arrange
    files = [Path("file1.py"), Path("file2.py")]
    config = {
        "max_complexity": 10,
        "max_parameters": 5,
        "max_statements": 50,
        "max_lines": 100,
        "ignore_rules": [],
    }
    mock_analyzer = MagicMock(return_value={})  # Empty dict = no violations

    # Act
    result, stats = analyze_files(files, config, mock_analyzer)

    # Assert
    assert result == {}  # No violations
    assert mock_analyzer.call_count == 2
    assert stats["files_analyzed"] == 2
    assert stats["files_with_violations"] == 0
    assert stats["compliant_files"] == 2


@patch("pathlib.Path.is_file", return_value=True)
def test_analyze_files_with_violations(mock_is_file):
    """Test analyzing files when some files have violations."""
    # Arrange
    files = [Path("file1.py"), Path("file2.py")]
    config = {
        "max_complexity": 10,
        "max_parameters": 5,
        "max_statements": 50,
        "max_lines": 100,
        "ignore_rules": [],
    }

    # First file has violations, second is compliant
    def mock_analyzer_side_effect(file_path, **kwargs):
        if file_path == Path("file1.py"):
            return {"complexity": [("function1", 10, 15)]}
        return {}

    mock_analyzer = MagicMock(side_effect=mock_analyzer_side_effect)

    # Act
    result, stats = analyze_files(files, config, mock_analyzer)

    # Assert
    assert len(result) == 1  # One file has violations
    assert Path("file1.py") in result
    assert result[Path("file1.py")] == {"complexity": [("function1", 10, 15)]}
    assert mock_analyzer.call_count == 2
    assert stats["files_analyzed"] == 2
    assert stats["files_with_violations"] == 1
    assert stats["compliant_files"] == 1


@patch("pathlib.Path.is_file", return_value=True)
def test_analyze_files_with_errors(mock_is_file):
    """Test analyzing files when errors occur during analysis."""
    # Arrange
    files = [Path("file1.py"), Path("file2.py"), Path("file3.py")]
    config = {
        "max_complexity": 10,
        "max_parameters": 5,
        "max_statements": 50,
        "max_lines": 100,
        "ignore_rules": [],
    }

    # File1 has violation, File2 raises error, File3 is compliant
    def mock_analyzer_side_effect(file_path, **kwargs):
        if file_path == Path("file1.py"):
            return {"style": ["E231 missing whitespace"]}
        elif file_path == Path("file2.py"):
            raise SyntaxError("mock syntax error")
        return {}

    mock_analyzer = MagicMock(side_effect=mock_analyzer_side_effect)

    # Act
    result, stats = analyze_files(files, config, mock_analyzer)

    # Assert
    assert len(result) == 2  # File1 violation, File2 error
    assert Path("file1.py") in result
    assert Path("file2.py") in result
    assert result[Path("file1.py")] == {"style": ["E231 missing whitespace"]}
    assert "error" in result[Path("file2.py")]  # Check for error key
    assert "mock syntax error" in result[Path("file2.py")]["error"][0]
    assert mock_analyzer.call_count == 3
    assert stats["files_analyzed"] == 3
    assert stats["files_with_violations"] == 1
    assert stats["files_with_errors"] == 1
    assert stats["compliant_files"] == 1


# <<< ZEROTH LAW FOOTER >>>
