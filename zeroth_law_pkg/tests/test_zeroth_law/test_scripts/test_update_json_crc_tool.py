"""Tests for scripts/update_json_crc_tool.py"""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from click.testing import CliRunner

# We need to make the script importable or invoke it via subprocess
# For simplicity, let's assume we can import its main function
# This might require path adjustments or running pytest from the root
try:
    from scripts.update_json_crc_tool import main as update_crc_main
except ImportError:
    # Handle cases where direct import might fail depending on test execution context
    update_crc_main = None
    print("Warning: Could not import update_json_crc_tool.main directly.", file=sys.stderr)

# --- Test Setup Data ---

MOCK_TOOL_INDEX_CONTENT = (
    json.dumps(
        {
            "tool1": {
                "crc": "0xabcdef12",
                "updated_timestamp": 1678886400.0,
                "checked_timestamp": 1678886400.0,
                "baseline_file": "tool1/tool1.txt",
                "json_definition_file": "tool1/tool1.json",
            },
            "tool2": {
                "crc": "0x11223344",
                "updated_timestamp": 1678886400.0,
                "checked_timestamp": 1678886400.0,
                "baseline_file": "tool2/tool2.txt",
                "json_definition_file": "tool2/tool2.json",
                "subcommands": {
                    "subA": {
                        "crc": "0x55667788",
                        "updated_timestamp": 1678886400.0,
                        "checked_timestamp": 1678886400.0,
                        "baseline_file": "tool2/subA/subA.txt",
                        "json_definition_file": "tool2/subA/subA.json",
                    }
                },
            },
        },
        indent=2,
    )
    + "\n"
)

MOCK_TOOL1_JSON_OLD_CRC = (
    json.dumps(
        {
            "command": ["tool1"],
            "description": "Test tool 1",
            "options": [],
            "arguments": [],
            "metadata": {
                "ground_truth_crc": "0xOLDDDDDD"  # Needs update
            },
        },
        indent=4,
    )
    + "\n"
)

MOCK_TOOL1_JSON_NEW_CRC = (
    json.dumps(
        {
            "command": ["tool1"],
            "description": "Test tool 1",
            "options": [],
            "arguments": [],
            "metadata": {
                "ground_truth_crc": "0xabcdef12"  # Updated value
            },
        },
        indent=4,
    )
    + "\n"
)

MOCK_TOOL2_SUBA_JSON_MISSING_CRC = (
    json.dumps(
        {
            "command": ["tool2", "subA"],
            "description": "Test tool 2 sub A",
            "options": [],
            "arguments": [],
            "metadata": {
                # Missing ground_truth_crc
            },
        },
        indent=4,
    )
    + "\n"
)

MOCK_TOOL2_SUBA_JSON_NEW_CRC = (
    json.dumps(
        {
            "command": ["tool2", "subA"],
            "description": "Test tool 2 sub A",
            "options": [],
            "arguments": [],
            "metadata": {
                "ground_truth_crc": "0x55667788"  # Added/updated value
            },
        },
        indent=4,
    )
    + "\n"
)

# Mock index content with a missing CRC key for tool1
MOCK_TOOL_INDEX_MISSING_CRC = (
    json.dumps(
        {
            "tool1": {
                # "crc": "0xABCDEF12", # CRC is missing
                "updated_timestamp": 1678886400.0,
                "checked_timestamp": 1678886400.0,
                "baseline_file": "tool1/tool1.txt",
                "json_definition_file": "tool1/tool1.json",
            }
        },
        indent=2,
    )
    + "\n"
)

# --- Tests ---


# Use mark.skipif to gracefully handle cases where the import fails
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
@patch("builtins.open", new_callable=mock_open)
def test_update_crc_success_base_tool(mock_open_func, mock_is_file, tmp_path):
    """Test successfully updating CRC for a base tool JSON."""
    # Define paths relative to tmp_path
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    target_json_path = workspace_root / "src/zeroth_law/tools/tool1/tool1.json"

    # Mock file existence checks
    def is_file_side_effect(path_arg):
        # Need to compare Path objects correctly
        return path_arg in [tool_index_path, target_json_path]

    mock_is_file.side_effect = is_file_side_effect

    # Configure mock_open: first reads index, second reads target json
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL1_JSON_OLD_CRC).return_value,
        mock_open().return_value,  # For the write call
    ]

    # Mock WORKSPACE_ROOT within the script's context
    # Also mock TOOL_INDEX_PATH and TOOLS_DIR if they are module-level constants used directly
    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        # Mock sys.argv for argparse
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            # We expect SystemExit(0) on success
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 0

    # Verify file interactions
    # Expected calls: read index, read target json, write target json
    assert mock_open_func.call_count == 3
    # Check the write call args
    write_call_args, write_call_kwargs = mock_open_func.call_args_list[2]
    assert write_call_args[0] == target_json_path
    assert write_call_args[1] == "w"

    # Check the data that was written
    # mock_open().write.call_args gives the arguments of the *last* call to write
    # To capture all written content if written in chunks (less likely with json.dump):
    written_data = "".join(call.args[0] for call in mock_open_func().write.call_args_list)

    # Compare ignoring whitespace differences
    assert json.loads(written_data) == json.loads(MOCK_TOOL1_JSON_NEW_CRC)


# --- Add more tests here for subcommands, missing CRC, no update needed, errors etc. ---
# Example skeleton for subcommand test:
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
@patch("builtins.open", new_callable=mock_open)
def test_update_crc_success_subcommand(mock_open_func, mock_is_file, tmp_path):
    """Test successfully updating CRC for a subcommand JSON."""
    # Define paths relative to tmp_path
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    target_json_path = workspace_root / "src/zeroth_law/tools/tool2/subA/subA.json"  # Subcommand path

    # Mock file existence checks
    def is_file_side_effect(path_arg):
        return path_arg in [tool_index_path, target_json_path]

    mock_is_file.side_effect = is_file_side_effect

    # Configure mock_open: read index, read target (missing crc)
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL2_SUBA_JSON_MISSING_CRC).return_value,
        mock_open().return_value,  # For the write call
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 0

    assert mock_open_func.call_count == 3
    write_call_args, write_call_kwargs = mock_open_func.call_args_list[2]
    assert write_call_args[0] == target_json_path
    assert write_call_args[1] == "w"
    written_data = "".join(call.args[0] for call in mock_open_func().write.call_args_list)
    assert json.loads(written_data) == json.loads(MOCK_TOOL2_SUBA_JSON_NEW_CRC)


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
# No mock_open needed as target file shouldn't be opened
def test_update_crc_target_json_not_found(mock_is_file, tmp_path):
    """Test script exits with error if target JSON file is not found."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    target_json_path = workspace_root / "src/zeroth_law/tools/tool_missing/missing.json"

    # Mock only index existence
    mock_is_file.return_value = False  # Default to not found

    def is_file_side_effect(path_arg):
        return path_arg == tool_index_path  # Only index exists

    mock_is_file.side_effect = is_file_side_effect

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            # Expect SystemExit(1) for failure
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    mock_is_file.assert_called_with(target_json_path)  # Check that it checked the target path


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
# No mock_open needed as index file shouldn't be opened if not found
def test_update_crc_index_not_found(mock_is_file, tmp_path):
    """Test script exits with error if tool_index.json file is not found."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    target_json_path = workspace_root / "src/zeroth_law/tools/tool1/tool1.json"

    # Mock only target JSON existence
    mock_is_file.return_value = False  # Default

    def is_file_side_effect(path_arg):
        return path_arg == target_json_path  # Only target exists

    mock_is_file.side_effect = is_file_side_effect

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    # Check it checked both file paths
    assert mock_is_file.call_count == 2
    assert tool_index_path in [call[0][0] for call in mock_is_file.call_args_list]
    assert target_json_path in [call[0][0] for call in mock_is_file.call_args_list]


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
@patch("builtins.open", new_callable=mock_open)
def test_update_crc_missing_index_entry(mock_open_func, mock_is_file, tmp_path):
    """Test script exits with error if the tool_id isn't found in the index."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    # Use a path for a tool not in MOCK_TOOL_INDEX_CONTENT
    target_json_path = workspace_root / "src/zeroth_law/tools/tool_missing/missing.json"

    mock_is_file.return_value = True  # Both files exist

    # Configure mock_open: read index (no write expected)
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        # No read for target json as script should fail before that
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    # Only index should have been read
    assert mock_open_func.call_count == 1
    read_call_args, _ = mock_open_func.call_args_list[0]
    assert read_call_args[0] == tool_index_path


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
@patch("builtins.open", new_callable=mock_open)
def test_update_crc_missing_crc_in_index(mock_open_func, mock_is_file, tmp_path):
    """Test script exits with error if the CRC value is missing in the index entry."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    target_json_path = workspace_root / "src/zeroth_law/tools/tool1/tool1.json"

    mock_is_file.return_value = True  # Both files exist

    # Configure mock_open: read index (with missing crc), no target read expected
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_MISSING_CRC).return_value,
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1  # Should fail

    assert mock_open_func.call_count == 1
    read_call_args, _ = mock_open_func.call_args_list[0]
    assert read_call_args[0] == tool_index_path


# --- JSON Load Error Tests ---
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
@patch("builtins.open", new_callable=mock_open)
def test_update_crc_invalid_index_json(mock_open_func, mock_is_file, tmp_path):
    """Test script exits with error if tool_index.json is invalid JSON."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    target_json_path = workspace_root / "src/zeroth_law/tools/tool1/tool1.json"

    mock_is_file.return_value = True  # Both files exist
    mock_open_func.return_value = mock_open(read_data="{invalid json").return_value

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1
    mock_open_func.assert_called_once_with(tool_index_path, "r", encoding="utf-8")


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
@patch("builtins.open", new_callable=mock_open)
def test_update_crc_invalid_target_json(mock_open_func, mock_is_file, tmp_path):
    """Test script exits with error if target JSON file is invalid JSON."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    target_json_path = workspace_root / "src/zeroth_law/tools/tool1/tool1.json"

    mock_is_file.return_value = True  # Both files exist
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data="}malformed{").return_value,  # Invalid target JSON
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1
    assert mock_open_func.call_count == 2


# --- File Write Error Test ---
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
@patch("builtins.open", new_callable=mock_open)
def test_update_crc_write_error(mock_open_func, mock_is_file, tmp_path):
    """Test script exits with error if writing the updated JSON fails."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    target_json_path = workspace_root / "src/zeroth_law/tools/tool1/tool1.json"

    mock_is_file.return_value = True  # Both files exist

    # Configure mock_open: read index, read target, then raise error on write
    mock_write = MagicMock()
    mock_write.write.side_effect = IOError("Disk full")
    mock_handle = MagicMock()
    mock_handle.__enter__.return_value = mock_write
    mock_handle.__exit__.return_value = None

    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL1_JSON_OLD_CRC).return_value,
        mock_handle,  # Mock for the write call that will raise IOError
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1  # Should fail

    assert mock_open_func.call_count == 3  # Read index, read target, attempt write


# --- Argument Parsing Test ---
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
def test_update_crc_missing_file_arg(tmp_path):
    """Test script exits with error if --file argument is missing."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py"]  # No --file argument
        with patch.object(sys, "argv", test_args):
            # Argparse raises SystemExit(2) for missing required args
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 2


# --- No Update Needed Test ---
MOCK_TOOL1_JSON_MATCHING_CRC = (
    json.dumps(
        {
            "command": ["tool1"],
            "description": "Test tool 1",
            "options": [],
            "arguments": [],
            "metadata": {
                "ground_truth_crc": "0xabcdef12"  # Matches index
            },
        },
        indent=4,
    )
    + "\n"
)


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
@patch("builtins.open", new_callable=mock_open)
def test_update_crc_no_update_needed(mock_open_func, mock_is_file, tmp_path):
    """Test script completes successfully without writing if CRC already matches."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    target_json_path = workspace_root / "src/zeroth_law/tools/tool1/tool1.json"

    mock_is_file.return_value = True  # Both files exist

    # Configure mock_open: read index, read target (matching crc). No write expected.
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL1_JSON_MATCHING_CRC).return_value,
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 0  # Success

    # Should only read index and target, no write call
    assert mock_open_func.call_count == 2


# --- Edge Case Path Parsing Test ---
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.Path.is_file")
@patch("builtins.open", new_callable=mock_open)
def test_update_crc_edge_path_parsing(mock_open_func, mock_is_file, tmp_path):
    """Test script handles a path that *might* confuse simple parsing (but should still work if using relative path logic)."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"
    # Use a path with an extra directory level, matching tool2/subA
    target_json_path = workspace_root / "src/zeroth_law/tools/tool2/subA/unexpected_dir/subA.json"

    mock_is_file.return_value = True  # Both files exist

    # Configure mock_open: read index, read target (expecting update)
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL2_SUBA_JSON_MISSING_CRC).return_value,
        mock_open().return_value,  # For the write call
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", workspace_root),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", tool_index_path),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", tool_index_path.parent),
    ):
        # The script should ideally derive the sequence ('tool2', 'subA') from the path
        # relative to the TOOLS_DIR, ignoring the extra 'unexpected_dir'.
        test_args = ["update_json_crc_tool.py", "--file", str(target_json_path)]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            # We expect this to succeed and update based on ('tool2', 'subA')
            assert excinfo.value.code == 0

    # Check write happened and data is correct
    assert mock_open_func.call_count == 3
    write_call_args, _ = mock_open_func.call_args_list[2]
    assert write_call_args[0] == target_json_path  # Should write back to the original path
    written_data = "".join(call.args[0] for call in mock_open_func().write.call_args_list)
    assert json.loads(written_data) == json.loads(MOCK_TOOL2_SUBA_JSON_NEW_CRC)


# --- TODO: Implement tests for:
# - Script runs successfully with valid args (--file). (Covered by success tests)
# - Reads tool_index.json correctly. (Implicitly covered)
# - Finds the correct entry based on json file path/command sequence inference. (Need specific tests for edge cases if get_tool_id_from_path/find_expected_crc are complex)
# - Updates the metadata.ground_truth_crc in the target JSON file correctly. (Covered by success tests)
# - Handles file not found (index or target JSON).
# - Handles missing entry in index.
# - Handles missing CRC in index entry.
# - Handles JSON load errors.
# - Handles file write errors.
# - Test argument parsing (--file required).
