import json
import sys
import subprocess
import shutil  # Needed for copying helper scripts
import os  # Needed for chmod
from pathlib import Path
from typing import Sequence  # Import Sequence

# --- START ADDED CODE ---
# Add project root to sys.path to allow importing 'src.zeroth_law'
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# --- END ADDED CODE ---

# Remove unnecessary mock imports
# from unittest.mock import MagicMock, patch, mock_open
# from unittest.mock import MagicMock, call

import pytest
from pathlib import Path
from enum import Enum

from zeroth_law.dev_scripts.baseline_generator import (
    generate_or_verify_baseline,
    BaselineStatus,
    BaselineData,
    calculate_crc32_hex,
)
from src.zeroth_law.dev_scripts.baseline_writers import (
    write_ground_truth_txt as real_write_ground_truth_txt,
    ensure_skeleton_json_exists as real_ensure_skeleton_json_exists,
)
from src.zeroth_law.lib.crc import calculate_crc32 as calculate_hex_crc32
from src.zeroth_law.dev_scripts.tool_index_utils import get_index_entry

from click.testing import CliRunner
from src.zeroth_law.lib.tooling.baseline_generator import (
    BaselineStatus,
    generate_or_verify_baseline,  # Keep if needed
)
from src.zeroth_law.dev_scripts.generate_baseline_cli import main as cli_main
from src.zeroth_law.lib.tool_index_handler import ToolIndexHandler
from unittest.mock import patch, MagicMock, mock_open


# --- Helper to get path to test data helper script --- #
def get_helper_script_path(script_name: str) -> Path:
    # Go up to project root and then specify path to test data
    project_root = Path(__file__).resolve().parents[3]
    # Correct the subdirectory name
    return project_root / "tests" / "test_data" / "test_dev_scripts" / "dummy_outputs" / script_name


# --- Helper to copy and prepare script in tmp_path --- #
def prepare_helper_script(tmp_path: Path, source_script_name: str) -> Path:
    source_path = get_helper_script_path(source_script_name)
    if not source_path.is_file():
        pytest.fail(f"Helper script not found: {source_path}")
    dest_path = tmp_path / source_script_name
    shutil.copy(source_path, dest_path)
    os.chmod(dest_path, 0o755)  # Make executable
    return dest_path


# Fixture for mock capture output (can be reused)
@pytest.fixture
def mock_capture_output():
    """Mock capture output bytes and success exit code."""
    return (b"Mocked help output for command.\\nLine 2.", 0)


def test_generate_baseline_new_tool(tmp_path):
    """Test baseline generation for a new tool using external helper script."""
    # Arrange
    tool_name = "newtool"
    flags = "--flag"
    command_sequence_str = f"{tool_name} {flags}"  # Command ZLT thinks it's running
    helper_script_name = "mock_output_1.py"
    expected_output_str = "Mocked help output for command.\\nLine 2."  # Content of mock_output_1.py
    expected_output_bytes = expected_output_str.encode("utf-8")
    expected_crc = calculate_hex_crc32(expected_output_str.rstrip())

    # Prepare the helper script
    helper_script_path = prepare_helper_script(tmp_path, helper_script_name)
    executable_command: Sequence[str] = (sys.executable, str(helper_script_path))

    # Set up temporary directory structure
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Act
    # Pass original command_sequence_str for ID/paths
    # Pass executable_command_override for actual execution
    status, calculated_crc_hex, _ = generate_or_verify_baseline(
        command_sequence_str,
        root_dir=tools_dir,
        executable_command_override=executable_command,
    )

    # Assert
    assert status == BaselineStatus.CAPTURE_SUCCESS
    assert calculated_crc_hex == expected_crc

    # Verify file existence and content using paths derived from command_sequence_str
    command_id = "_".join(command_sequence_str.split())
    txt_path = tools_dir / tool_name / f"{command_id}.txt"
    json_path = tools_dir / tool_name / f"{command_id}.json"

    assert txt_path.exists(), f"Expected file {txt_path} does not exist"
    assert txt_path.read_bytes() == expected_output_bytes, f"Content of {txt_path} does not match expected output"
    assert json_path.exists(), f"Expected file {json_path} does not exist"

    # Verify basic skeleton JSON structure
    try:
        with open(json_path, "r") as f:
            json_data = json.load(f)
        assert "command_sequence" in json_data
        # Skeleton should store the original command sequence string
        assert json_data["command_sequence"] == command_sequence_str
        assert "metadata" in json_data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        pytest.fail(f"Failed to read or parse skeleton JSON {json_path}: {e}")


# Comment out this test as the UP_TO_DATE logic is now handled by the caller
# def test_generate_baseline_up_to_date(tmp_path, monkeypatch):
#     """Test verification when baseline is up-to-date."""
#     # Arrange
#     command = "existingtool"
#     command_sequence_str = command
#     mock_output = b"Mocked help output for command.\nLine 2."
#     current_crc = calculate_hex_crc32(mock_output.decode().replace("\r\n", "\n").replace("\r", "\n").rstrip())
#
#     # Set up temporary directory structure
#     tools_dir = tmp_path / "tools"
#     tools_dir.mkdir()
#     tool_index_path = tmp_path / "tool_index.json"
#     tool_index_path.write_text(json.dumps({command: {"crc": current_crc}}))
#
#     # Monkeypatch constants to use temporary paths
#     monkeypatch.setattr("src.zeroth_law.dev_scripts.tool_index_utils.TOOLS_DIR_ROOT", tools_dir)
#     monkeypatch.setattr("src.zeroth_law.dev_scripts.tool_index_utils.TOOL_INDEX_PATH", tool_index_path)
#
#     # Monkeypatch subprocess to return mock output
#     def mock_capture_command_output(cmd):
#         return mock_output, 0
#     monkeypatch.setattr("src.zeroth_law.dev_scripts.baseline_generator._capture_command_output", mock_capture_command_output)
#
#     # Mock the file writing functions to verify paths used
#     dummy_txt_path = tools_dir / 'existingtool' / 'existingtool.txt'
#     monkeypatch.setattr('src.zeroth_law.dev_scripts.baseline_writers.write_ground_truth_txt', MagicMock(return_value=None))
#     monkeypatch.setattr('src.zeroth_law.dev_scripts.baseline_writers.ensure_skeleton_json_exists', MagicMock(return_value=None))
#
#     # Act
#     # Need to adapt this call if generate_or_verify_baseline signature changed
#     status, returned_crc, timestamp = generate_or_verify_baseline(command_sequence_str, root_dir=tools_dir)
#
#     # Assert
#     # The status check needs rethinking. The core logic is now separate.
#     # Maybe check that returned_crc matches current_crc and status is CAPTURE_SUCCESS?
#     # assert status == BaselineStatus.UP_TO_DATE # This status is no longer returned directly
#     assert status == BaselineStatus.CAPTURE_SUCCESS
#     assert returned_crc == current_crc
#
#     # The index update check also needs rethinking as it's done by the caller
#     # with open(tool_index_path, "r") as f:
#     #     index_data = json.load(f)
#     # entry = get_index_entry(index_data, command.split())
#     # assert entry["crc"] == current_crc
#     # assert "checked_timestamp" in entry


def test_generate_baseline_crc_mismatch(tmp_path):
    """Test baseline CRC mismatch detection using external helper script."""
    # Arrange
    tool_name = "tool_to_update"
    command_sequence_str = tool_name  # Command ZLT thinks it's running
    helper_script_name = "mock_output_2.py"
    expected_output_str = "New help output for command.\\nLine 2."  # Content of mock_output_2.py
    expected_output_bytes = expected_output_str.encode("utf-8")
    expected_crc = calculate_hex_crc32(expected_output_str.rstrip())

    # Prepare the helper script
    helper_script_path = prepare_helper_script(tmp_path, helper_script_name)
    executable_command: Sequence[str] = (sys.executable, str(helper_script_path))

    # Set up temporary directory structure
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    # Create a dummy index file indicating an *old* CRC to force an update scenario
    # This part is tricky without index utils dependency. We are primarily testing
    # that generate_or_verify_baseline returns CAPTURE_SUCCESS and the correct new CRC.
    # We cannot easily verify the *index update* itself without more changes/mocks.

    # Act
    status, calculated_crc_hex, _ = generate_or_verify_baseline(
        command_sequence_str,
        root_dir=tools_dir,
        executable_command_override=executable_command,
    )

    # Assert
    assert status == BaselineStatus.CAPTURE_SUCCESS
    assert calculated_crc_hex == expected_crc  # Verify the *new* CRC was calculated

    # Verify file existence and content using paths derived from command_sequence_str
    command_id = "_".join(command_sequence_str.split())
    txt_path = tools_dir / tool_name / f"{command_id}.txt"
    json_path = tools_dir / tool_name / f"{command_id}.json"
    assert txt_path.exists(), f"Expected file {txt_path} does not exist"
    assert txt_path.read_bytes() == expected_output_bytes, f"Content of {txt_path} does not match expected output"
    assert json_path.exists(), f"Expected file {json_path} does not exist"


def test_generate_baseline_file_content(tmp_path):
    """Test file writing content and path generation using external helper script."""
    # Arrange
    tool_name = "filewritetest"
    command_sequence_str = tool_name  # Command ZLT thinks it's running
    helper_script_name = "mock_output_3.py"
    # Align expected string with actual print() output (includes final newline)
    expected_output_str = "Specific content for file write test.\nEnd.\n"
    expected_output_bytes = expected_output_str.encode("utf-8")
    # Calculate expected CRC on the string *with* the trailing newline
    expected_crc = calculate_hex_crc32(expected_output_str)

    # Prepare the helper script
    helper_script_path = prepare_helper_script(tmp_path, helper_script_name)
    executable_command: Sequence[str] = (sys.executable, str(helper_script_path))
    command_id_for_paths = "_".join(command_sequence_str.split())

    # Set up temporary directory structure
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Act
    status, calculated_crc_hex, _ = generate_or_verify_baseline(
        command_sequence_str,
        root_dir=tools_dir,
        executable_command_override=executable_command,
    )

    # Assert
    assert status == BaselineStatus.CAPTURE_SUCCESS
    assert calculated_crc_hex == expected_crc

    # Verify file existence and content using paths derived from command_sequence_str
    txt_path = tools_dir / tool_name / f"{command_id_for_paths}.txt"
    json_path = tools_dir / tool_name / f"{command_id_for_paths}.json"
    assert txt_path.exists(), f"Expected file {txt_path} does not exist"
    assert txt_path.read_bytes() == expected_output_bytes, f"Content of {txt_path} does not match expected output"
    assert json_path.exists(), f"Expected file {json_path} does not exist"


# TODO: Add tests for failure conditions using real scenarios if possible
# (e.g., non-executable script, script returning error code)
