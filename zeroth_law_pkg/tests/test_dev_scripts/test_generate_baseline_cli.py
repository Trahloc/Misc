import json
import sys
from pathlib import Path

# --- START ADDED CODE ---
# Add project root to sys.path to allow importing 'src.zeroth_law'
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # tests/test_dev_scripts -> tests -> workspace
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# --- END ADDED CODE ---

from unittest.mock import MagicMock, patch, mock_open

# Remove click testing imports if no longer testing the CLI directly
# from click.testing import CliRunner

import pytest

# Import functions and classes from the actual script
from src.zeroth_law.dev_scripts.baseline_generator import (
    derive_tool_and_id,
    generate_or_verify_baseline,
    BaselineStatus,
    TOOLS_DIR_ROOT as SCRIPT_TOOLS_DIR_ROOT,  # Import and alias for clarity
)

# Import other dependencies needed for mocking if necessary
from src.zeroth_law.lib.crc import calculate_crc32 as calculate_hex_crc32  # Import if needed

# Redefine constants if needed, or rely on imported ones
# TOOLS_DIR = Path(__file__).parent.parent.parent / "src/zeroth_law/tools"
INDEX_PATH = SCRIPT_TOOLS_DIR_ROOT / "tool_index.json"  # Use imported root
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]  # Define workspace root if needed elsewhere


# Fixture for mock capture output (can be reused)
@pytest.fixture
def mock_capture_output():
    # Simple docstring
    """Mock capture output bytes and success exit code."""
    # Corrected: Use \n for newline in bytes literal
    return (b"Mocked help output for command.\nLine 2.", 0)


# --- Remove old subprocess helper and test ---
# def run_generate_script(...): ...
# @pytest.mark.skip(...)
# def test_generate_baseline_for_subcommand(...): ...

# --- Remove old cleanup fixture ---
# @pytest.fixture(scope="function")
# def clean_generated_files(request): ...


# --- NEW TESTS ---


# Test derive_tool_and_id function
@pytest.mark.parametrize(
    "command_list, expected_tool, expected_id",
    [
        (["tool"], "tool", "tool"),
        (["tool", "subcommand"], "tool", "tool_subcommand"),
        (["tool-with-hyphen", "arg"], "tool-with-hyphen", "tool-with-hyphen_arg"),
        # Add more cases if needed (e.g., sanitization)
    ],
)
def test_derive_tool_and_id(command_list, expected_tool, expected_id):
    tool_name, tool_id = derive_tool_and_id(command_list)
    assert tool_name == expected_tool
    assert tool_id == expected_id


def test_derive_tool_and_id_empty():
    with pytest.raises(ValueError):
        derive_tool_and_id([])


# Test baseline generation logic with mocks (Example: New Tool)
def test_generate_baseline_new_tool(mock_capture_output):
    # Arrange
    command = "newtool --flag"
    tool_name, tool_id = derive_tool_and_id(command.split())

    # Create mock functions
    mock_capture = MagicMock(return_value=mock_capture_output)
    mock_load_index = MagicMock(return_value={})
    mock_save_index = MagicMock()
    mock_write_txt = MagicMock(return_value=True)
    mock_ensure_skeleton = MagicMock(return_value=True)

    expected_crc = calculate_hex_crc32(
        mock_capture_output[0].decode().replace("\r\n", "\n").replace("\r", "\n").rstrip()
    )

    # Act
    # Pass mocks directly
    status = generate_or_verify_baseline(
        command_str=command,
        load_tool_index_func=mock_load_index,
        save_tool_index_func=mock_save_index,
        capture_tty_output_func=mock_capture,
        write_ground_truth_txt_func=mock_write_txt,
        ensure_skeleton_json_exists_func=mock_ensure_skeleton,
    )

    # Assert
    assert status == BaselineStatus.UPDATED
    mock_capture.assert_called_once()
    # Check the command passed to capture includes 'sh -c "... --help | cat"'
    assert mock_capture.call_args[0][0][0] == "sh"
    assert mock_capture.call_args[0][0][1] == "-c"
    assert mock_capture.call_args[0][0][2] == f"{command} --help | cat"
    mock_load_index.assert_called_once()
    mock_write_txt.assert_called_once()
    mock_save_index.assert_called_once()
    # Check the data saved to the index
    saved_index_data = mock_save_index.call_args[0][0]
    assert tool_id in saved_index_data
    assert saved_index_data[tool_id]["crc"] == expected_crc
    mock_ensure_skeleton.assert_called_once()


# Test baseline generation logic (Example: Up to Date)
def test_generate_baseline_up_to_date(mock_capture_output):
    # Arrange
    command = "existingtool"
    tool_name, tool_id = derive_tool_and_id(command.split())

    # Calculate CRC for the mock output
    current_crc = calculate_hex_crc32(
        mock_capture_output[0].decode().replace("\r\n", "\n").replace("\r", "\n").rstrip()
    )

    # Create mock functions
    mock_capture = MagicMock(return_value=mock_capture_output)
    mock_load_index = MagicMock(return_value={tool_id: {"crc": current_crc}})
    mock_save_index = MagicMock()
    mock_write_txt = MagicMock(return_value=True)
    mock_ensure_skeleton = MagicMock(return_value=True)

    # Act
    # Pass mocks directly
    status = generate_or_verify_baseline(
        command_str=command,
        load_tool_index_func=mock_load_index,
        save_tool_index_func=mock_save_index,
        capture_tty_output_func=mock_capture,
        write_ground_truth_txt_func=mock_write_txt,
        ensure_skeleton_json_exists_func=mock_ensure_skeleton,
    )

    # Assert
    assert status == BaselineStatus.UP_TO_DATE
    mock_capture.assert_called_once()
    mock_load_index.assert_called_once()
    mock_write_txt.assert_not_called()  # Should not write TXT if up-to-date
    mock_save_index.assert_not_called()  # Should not save index if up-to-date
    mock_ensure_skeleton.assert_called_once()  # Should still ensure skeleton exists


# Test baseline generation logic (Example: CRC Mismatch -> Update)
def test_generate_baseline_crc_mismatch(mock_capture_output):
    # Arrange
    command = "tool_to_update"
    tool_name, tool_id = derive_tool_and_id(command.split())

    # Calculate new CRC for the mock output
    new_crc = calculate_hex_crc32(mock_capture_output[0].decode().replace("\r\n", "\n").replace("\r", "\n").rstrip())
    old_crc = "0xOLDCRC00"

    # Create mock functions
    mock_capture = MagicMock(return_value=mock_capture_output)
    mock_load_index = MagicMock(return_value={tool_id: {"crc": old_crc}})
    mock_save_index = MagicMock()
    mock_write_txt = MagicMock(return_value=True)
    mock_ensure_skeleton = MagicMock(return_value=True)

    # Act
    # Pass mocks directly
    status = generate_or_verify_baseline(
        command_str=command,
        load_tool_index_func=mock_load_index,
        save_tool_index_func=mock_save_index,
        capture_tty_output_func=mock_capture,
        write_ground_truth_txt_func=mock_write_txt,
        ensure_skeleton_json_exists_func=mock_ensure_skeleton,
    )

    # Assert
    assert status == BaselineStatus.UPDATED
    mock_capture.assert_called_once()
    mock_load_index.assert_called_once()
    mock_write_txt.assert_called_once()  # Should write TXT on mismatch
    mock_save_index.assert_called_once()  # Should save index on mismatch
    # Check saved data
    saved_index_data = mock_save_index.call_args[0][0]
    assert tool_id in saved_index_data
    assert saved_index_data[tool_id]["crc"] == new_crc  # Should have new CRC
    mock_ensure_skeleton.assert_called_once()


# Optional: Test file writing content (still requires mocks, but passed in)
# Note: Patching TOOLS_DIR_ROOT directly is still an internal mock.
# Instead, pass mock writer functions that internally use tmp_path.

# Import the real writer functions to wrap them
from src.zeroth_law.dev_scripts.baseline_writers import (
    write_ground_truth_txt as real_write_ground_truth_txt,
    ensure_skeleton_json_exists as real_ensure_skeleton_json_exists,
)


def test_generate_baseline_file_content(mock_capture_output, tmp_path):
    # Arrange
    command = "filewritetest"
    tool_name, tool_id = derive_tool_and_id(command.split())

    # Create mock functions for capture and index I/O
    mock_capture = MagicMock(return_value=mock_capture_output)
    mock_load_index = MagicMock(return_value={})
    mock_save_index = MagicMock()  # Mock saving index to avoid file I/O

    # Create wrapper functions for writers that use tmp_path
    def mock_write_txt_to_tmp(tool_dir, tool_id, content):
        # Original function uses TOOLS_DIR_ROOT, we replace tool_dir base
        actual_tool_dir = tmp_path / tool_dir.name  # Use tmp_path as base
        # Pass the tmp_path based directory to the real function
        return real_write_ground_truth_txt(actual_tool_dir, tool_id, content)

    def mock_ensure_skeleton_in_tmp(tool_dir, tool_id, command_list):
        actual_tool_dir = tmp_path / tool_dir.name
        # Pass the tmp_path based directory to the real function
        return real_ensure_skeleton_json_exists(actual_tool_dir, tool_id, command_list)

    expected_txt_path = tmp_path / tool_name / f"{tool_id}.txt"
    expected_json_path = tmp_path / tool_name / f"{tool_id}.json"
    expected_txt_content = mock_capture_output[0].decode().replace("\r\n", "\n").replace("\r", "\n").rstrip()

    # Act
    # Pass mocks and wrappers directly
    status = generate_or_verify_baseline(
        command_str=command,
        load_tool_index_func=mock_load_index,
        save_tool_index_func=mock_save_index,  # Mocked to prevent real write
        capture_tty_output_func=mock_capture,
        write_ground_truth_txt_func=mock_write_txt_to_tmp,  # Wrapper
        ensure_skeleton_json_exists_func=mock_ensure_skeleton_in_tmp,  # Wrapper
    )

    # Assert
    assert status == BaselineStatus.UPDATED
    assert expected_txt_path.is_file()
    assert expected_txt_path.read_text() == expected_txt_content
    assert expected_json_path.is_file()
    # Check basic skeleton content
    skeleton_data = json.loads(expected_json_path.read_text())
    assert "command_sequence" in skeleton_data
    assert skeleton_data["command_sequence"] == command.split()
    assert "metadata" in skeleton_data
    assert skeleton_data["metadata"]["ground_truth_crc"] == "0x00000000"
    mock_save_index.assert_called_once()  # Verify index saving was attempted


# Add more tests for failure cases (capture failure, write failure, etc.)
# ...
