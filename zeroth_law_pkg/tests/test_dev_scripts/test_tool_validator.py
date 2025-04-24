import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add path to import the module under test
_test_file_path = Path(__file__).resolve()
_project_root = _test_file_path.parents[2]
_src_path = _project_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Module to be tested (will be created next)
from zeroth_law.dev_scripts.tool_validator import is_tool_available

@patch('subprocess.run')
def test_tool_available_success(mock_subprocess_run):
    """Test when 'uv run which' finds the tool successfully."""
    tool_name = "existing_tool"
    expected_command = ["uv", "run", "--quiet", "--", "which", tool_name]

    # Mock successful execution
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = f"/path/to/{tool_name}"
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    assert is_tool_available(tool_name) is True
    mock_subprocess_run.assert_called_once_with(
        expected_command,
        capture_output=True,
        text=True,
        check=False, # Important: function checks return code itself
        timeout=10 # Assuming a default timeout in the implementation
    )

@patch('subprocess.run')
def test_tool_available_failure(mock_subprocess_run):
    """Test when 'uv run which' fails to find the tool (non-zero exit)."""
    tool_name = "missing_tool"
    expected_command = ["uv", "run", "--quiet", "--", "which", tool_name]

    # Mock failed execution
    mock_result = MagicMock()
    mock_result.returncode = 1 # Non-zero indicates failure
    mock_result.stdout = ""
    mock_result.stderr = f"{tool_name} not found"
    mock_subprocess_run.return_value = mock_result

    assert is_tool_available(tool_name) is False
    mock_subprocess_run.assert_called_once_with(
        expected_command,
        capture_output=True,
        text=True,
        check=False,
        timeout=10
    )

@patch('subprocess.run')
def test_tool_available_uv_not_found(mock_subprocess_run):
    """Test when the 'uv' command itself is not found."""
    tool_name = "any_tool"
    mock_subprocess_run.side_effect = FileNotFoundError("uv command not found")

    assert is_tool_available(tool_name) is False
    # Check that it was attempted
    mock_subprocess_run.assert_called_once()

@patch('subprocess.run')
def test_tool_available_timeout(mock_subprocess_run):
    """Test when the 'uv run which' command times out."""
    tool_name = "slow_tool"
    expected_command = ["uv", "run", "--quiet", "--", "which", tool_name]
    mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd=expected_command, timeout=10)

    assert is_tool_available(tool_name) is False
    mock_subprocess_run.assert_called_once_with(
        expected_command,
        capture_output=True,
        text=True,
        check=False,
        timeout=10
    )