import os
import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Module to be tested (will be created next)
from zeroth_law.dev_scripts.environment_scanner import get_executables_from_env

# Helper function to create dummy executable files
def create_dummy_executables(dir_path: Path, names: list[str]):
    dir_path.mkdir(parents=True, exist_ok=True)
    for name in names:
        (dir_path / name).touch(mode=0o755) # Make executable

@patch('subprocess.run')
def test_scan_successful_unix(mock_subprocess_run, tmp_path):
    """Test successful scan on a Unix-like system."""
    python_path = tmp_path / ".venv" / "bin" / "python"
    bin_path = python_path.parent
    executables = ["python", "pip", "ruff", "my_tool"]
    create_dummy_executables(bin_path, executables)

    # Mock the 'uv run which python' call
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = str(python_path) + "\n" # Add newline as subprocess might
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    found_executables = get_executables_from_env()

    # Assert subprocess was called correctly
    mock_subprocess_run.assert_called_once_with(
        ["uv", "run", "--quiet", "--", "which", "python"],
        capture_output=True,
        text=True,
        check=False, # Verify check=False is used internally
        timeout=15
    )

    # Check the returned set (base names)
    assert found_executables == set(executables)

@patch('subprocess.run')
@patch('sys.platform', 'win32') # Simulate Windows platform
def test_scan_successful_windows(mock_subprocess_run, tmp_path):
    """Test successful scan on Windows."""
    python_path = tmp_path / ".venv" / "Scripts" / "python.exe"
    scripts_path = python_path.parent
    # Windows often includes .exe, .bat, etc. The function should handle base names.
    executables_with_ext = ["python.exe", "pip.exe", "ruff.bat", "my_tool"]
    executable_bases = ["python", "pip", "ruff", "my_tool"]
    create_dummy_executables(scripts_path, executables_with_ext)

    # Mock the 'uv run which python' call
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = str(python_path)
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    found_executables = get_executables_from_env()

    # Assert subprocess was called correctly
    mock_subprocess_run.assert_called_once_with(
        ["uv", "run", "--quiet", "--", "which", "python"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15
    )

    # Check the returned set (base names)
    assert found_executables == set(executable_bases)


@patch('subprocess.run')
def test_scan_uv_which_fails(mock_subprocess_run):
    """Test scenario where 'uv run which python' fails."""
    # Mock the 'uv run which python' call to fail
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "uv command failed"
    mock_subprocess_run.return_value = mock_result

    # Expect the function to handle this, perhaps returning empty set or raising
    # Assuming it returns an empty set on failure to find python
    found_executables = get_executables_from_env()
    assert found_executables == set()

    # Or if it should raise an error:
    # with pytest.raises(RuntimeError): # Or a more specific custom error
    #     get_executables_from_env()

@patch('subprocess.run')
def test_scan_uv_command_not_found(mock_subprocess_run):
    """Test scenario where 'uv' command itself is not found."""
    mock_subprocess_run.side_effect = FileNotFoundError("uv command not found")

    # Assuming it returns an empty set on failure
    found_executables = get_executables_from_env()
    assert found_executables == set()

    # Or if it should raise an error:
    # with pytest.raises(FileNotFoundError): # Or a custom error
    #     get_executables_from_env()


@patch('subprocess.run')
def test_scan_derived_bin_path_missing(mock_subprocess_run, tmp_path):
    """Test scenario where uv finds python, but the derived bin path doesn't exist."""
    # Simulate python path, but don't create the bin directory
    python_path = tmp_path / ".venv" / "bin" / "python"
    # bin_path = python_path.parent # Not created

    # Mock the 'uv run which python' call
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = str(python_path)
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    # Assuming it returns an empty set if bin path is invalid
    found_executables = get_executables_from_env()
    assert found_executables == set()

    # Assert subprocess was still called
    mock_subprocess_run.assert_called_once()


@patch('subprocess.run')
def test_scan_empty_bin_directory(mock_subprocess_run, tmp_path):
    """Test scanning an existing but empty bin directory."""
    python_path = tmp_path / ".venv" / "bin" / "python"
    bin_path = python_path.parent
    bin_path.mkdir(parents=True, exist_ok=True) # Create empty dir

    # Mock the 'uv run which python' call
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = str(python_path)
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    found_executables = get_executables_from_env()
    assert found_executables == set()

    # Assert subprocess was called
    mock_subprocess_run.assert_called_once()