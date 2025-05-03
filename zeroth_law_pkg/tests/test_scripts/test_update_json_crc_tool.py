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
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")  # Patch ArgumentParser
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path")  # Keep patch for constants, but configure instances manually
def test_update_crc_success_base_tool(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test successfully updating CRC for a base tool JSON."""
    # Define paths relative to tmp_path
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool1/tool1.json")

    # --- Configure Mock Path Instances --- #
    mock_tool_index = MagicMock(spec=Path)
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True
    mock_tool_index.parent = MagicMock(spec=Path)
    mock_tool_index.parent.name = "tools"

    mock_target_json = MagicMock(spec=Path)
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True
    mock_target_json.stem = "tool1"
    mock_target_json.parent = MagicMock(spec=Path)
    mock_target_json.parent.name = "tool1"
    mock_target_json.is_relative_to.return_value = True
    mock_target_json.relative_to.return_value = MagicMock(parts=["tool1", "tool1.json"])

    mock_tools_dir = MagicMock(spec=Path)
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir

    mock_ws_root_real = MagicMock(spec=Path)
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    # --- Configure Mock ArgumentParser --- #
    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    # --- Configure mock_open --- #
    mock_write_handle = mock_open().return_value
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL1_JSON_OLD_CRC).return_value,
        mock_write_handle,
    ]

    # Patch constants
    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                # Remove debug logs before final run if they were added
                update_crc_main()
            assert excinfo.value.code == 0

    # --- Assertions --- #
    assert mock_open_func.call_count == 3
    assert mock_open_func.call_args_list[0][0][0] is mock_tool_index
    assert mock_open_func.call_args_list[1][0][0] is mock_target_json
    assert mock_open_func.call_args_list[2][0][0] is mock_target_json
    assert mock_open_func.call_args_list[2][0][1] == "w"
    mock_target_json.is_file.assert_called()
    mock_tool_index.is_file.assert_called()
    written_data = "".join(call.args[0] for call in mock_write_handle.write.call_args_list)
    assert json.loads(written_data) == json.loads(MOCK_TOOL1_JSON_NEW_CRC)


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")  # Patch ArgumentParser
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path")  # Patch Path
def test_update_crc_success_subcommand(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test successfully updating CRC for a subcommand JSON."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool2/subA/subA.json")

    # Configure Mocks (similar to base_tool, adjust paths and relative_to)
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True
    mock_tool_index.parent = MagicMock(spec=Path, name="mock_tool_index.parent")
    mock_tool_index.parent.name = "tools"

    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True
    mock_target_json.stem = "subA"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "subA"  # Immediate parent
    mock_target_json.is_relative_to.return_value = True
    # Adjust relative path parts for subcommand
    mock_target_json.relative_to.return_value = MagicMock(parts=["tool2", "subA", "subA.json"])

    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir

    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    mock_write_handle = mock_open().return_value
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL2_SUBA_JSON_MISSING_CRC).return_value,  # Use missing CRC data
        mock_write_handle,
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 0

    # Assertions
    assert mock_open_func.call_count == 3
    assert mock_open_func.call_args_list[0][0][0] is mock_tool_index
    assert mock_open_func.call_args_list[1][0][0] is mock_target_json
    assert mock_open_func.call_args_list[2][0][0] is mock_target_json
    mock_target_json.is_file.assert_called()
    mock_tool_index.is_file.assert_called()
    written_data = "".join(call.args[0] for call in mock_write_handle.write.call_args_list)
    # Compare against expected updated subcommand JSON
    assert json.loads(written_data) == json.loads(MOCK_TOOL2_SUBA_JSON_NEW_CRC)


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open)  # Keep mock_open for index read
@patch("pathlib.Path")
def test_update_crc_target_json_not_found(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test script exits with error if target JSON file is not found."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool_missing/missing.json")

    # Configure Mocks - Index exists, Target does NOT
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True  # Index exists
    mock_tool_index.parent.name = "tools"

    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = False  # Target does NOT exist
    mock_target_json.stem = "missing"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "tool_missing"

    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir

    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json  # Return the non-existent mock
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    # mock_open should NOT be called in this case
    mock_open_func.side_effect = IOError("Should not be called")

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    # Assertions
    mock_target_json.is_file.assert_called()  # is_file check should happen
    mock_open_func.assert_not_called()  # open should not happen


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open)  # mock_open not really needed, but keep patch
@patch("pathlib.Path")
def test_update_crc_index_not_found(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test script exits with error if tool_index.json file is not found."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool1/tool1.json")

    # Configure Mocks - Index does NOT exist, Target exists
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = False  # Index does NOT exist
    mock_tool_index.parent.name = "tools"

    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True  # Target exists
    mock_target_json.stem = "tool1"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "tool1"
    mock_target_json.is_relative_to.return_value = True
    mock_target_json.relative_to.return_value = MagicMock(parts=["tool1", "tool1.json"])

    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir
    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index  # Return non-existent index mock
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    mock_open_func.side_effect = IOError("Should not be called")

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    # Assertions
    mock_target_json.is_file.assert_called()  # Target file check should happen first
    mock_tool_index.is_file.assert_called()  # Index file check should happen after target ID is derived
    mock_open_func.assert_not_called()


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path")
def test_update_crc_missing_index_entry(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test script exits with error if the tool_id isn't found in the index."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(
        workspace_root / "src/zeroth_law/tools/tool_missing/missing.json"
    )  # Path for missing tool

    # Configure Mocks - Both files exist, but index lacks entry for 'tool_missing'
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True
    mock_tool_index.parent.name = "tools"

    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True
    mock_target_json.stem = "missing"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "tool_missing"
    mock_target_json.is_relative_to.return_value = True
    mock_target_json.relative_to.return_value = MagicMock(
        parts=["tool_missing", "missing.json"]
    )  # Tool ID derived as tool_missing_missing

    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir
    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock_open - only index should be read
    mock_index_read_handle = mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value
    mock_open_func.side_effect = [mock_index_read_handle]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    # Assertions
    mock_target_json.is_file.assert_called()
    mock_tool_index.is_file.assert_called()
    mock_open_func.assert_called_once_with(mock_tool_index, "r", encoding="utf-8")


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path")
def test_update_crc_missing_crc_in_index(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test script exits with error if the CRC value is missing in the index entry."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool1/tool1.json")  # Use tool1 path

    # Configure Mocks - Both files exist, but index has missing CRC for tool1
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True
    mock_tool_index.parent.name = "tools"
    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True
    mock_target_json.stem = "tool1"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "tool1"
    mock_target_json.is_relative_to.return_value = True
    mock_target_json.relative_to.return_value = MagicMock(parts=["tool1", "tool1.json"])
    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir
    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock_open - read index with missing CRC
    mock_index_read_handle = mock_open(read_data=MOCK_TOOL_INDEX_MISSING_CRC).return_value
    mock_open_func.side_effect = [mock_index_read_handle]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    # Assertions
    mock_target_json.is_file.assert_called()
    mock_tool_index.is_file.assert_called()
    mock_open_func.assert_called_once_with(mock_tool_index, "r", encoding="utf-8")


# --- JSON Load Error Tests ---
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path")
def test_update_crc_invalid_index_json(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test script exits with error if tool_index.json is invalid JSON."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool1/tool1.json")

    # Configure Mocks - Both files exist
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True
    mock_tool_index.parent.name = "tools"
    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True
    mock_target_json.stem = "tool1"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "tool1"
    mock_target_json.is_relative_to.return_value = True
    mock_target_json.relative_to.return_value = MagicMock(parts=["tool1", "tool1.json"])
    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir
    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock_open - return invalid JSON for index read
    mock_open_func.side_effect = [mock_open(read_data="{invalid json").return_value]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    mock_target_json.is_file.assert_called()
    mock_tool_index.is_file.assert_called()
    mock_open_func.assert_called_once_with(mock_tool_index, "r", encoding="utf-8")


@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path")
def test_update_crc_invalid_target_json(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test script exits with error if target JSON file is invalid JSON."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool1/tool1.json")

    # Configure Mocks - Both files exist
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True
    mock_tool_index.parent.name = "tools"
    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True
    mock_target_json.stem = "tool1"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "tool1"
    mock_target_json.is_relative_to.return_value = True
    mock_target_json.relative_to.return_value = MagicMock(parts=["tool1", "tool1.json"])
    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir
    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock_open - return invalid JSON for target read
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data="}malformed{").return_value,
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    mock_target_json.is_file.assert_called()
    mock_tool_index.is_file.assert_called()
    assert mock_open_func.call_count == 2
    assert mock_open_func.call_args_list[0][0][0] is mock_tool_index
    assert mock_open_func.call_args_list[1][0][0] is mock_target_json


# --- File Write Error Test ---
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path")
def test_update_crc_write_error(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test script exits with error if writing the updated JSON fails."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool1/tool1.json")

    # Configure Mocks - Both files exist
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True
    mock_tool_index.parent.name = "tools"
    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True
    mock_target_json.stem = "tool1"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "tool1"
    mock_target_json.is_relative_to.return_value = True
    mock_target_json.relative_to.return_value = MagicMock(parts=["tool1", "tool1.json"])
    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir
    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock_open - raise error on write
    mock_write_handle = MagicMock()
    mock_write_handle.__enter__.return_value = mock_write_handle  # Return self for context mgmt
    mock_write_handle.write.side_effect = IOError("Disk full")
    mock_write_handle.__exit__.return_value = None  # No error suppression

    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL1_JSON_OLD_CRC).return_value,
        mock_write_handle,  # Use our error-raising handle
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 1

    # Assertions
    assert mock_open_func.call_count == 3
    assert mock_open_func.call_args_list[0][0][0] is mock_tool_index
    assert mock_open_func.call_args_list[1][0][0] is mock_target_json
    assert mock_open_func.call_args_list[2][0][0] is mock_target_json
    mock_target_json.is_file.assert_called()
    mock_tool_index.is_file.assert_called()
    # Check write was attempted
    mock_write_handle.write.assert_called()


# --- Argument Parsing Test ---
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
def test_update_crc_missing_file_arg(tmp_path):
    """Test script exits with error if --file argument is missing."""
    workspace_root = tmp_path
    tool_index_path = workspace_root / "src/zeroth_law/tools/tool_index.json"

    # No need to mock Path here as argparse fails before path usage
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
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path")
def test_update_crc_no_update_needed(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test script completes successfully without writing if CRC already matches."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool1/tool1.json")

    # Configure Mocks - Both files exist
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True
    mock_tool_index.parent.name = "tools"
    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True
    mock_target_json.stem = "tool1"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "tool1"
    mock_target_json.is_relative_to.return_value = True
    mock_target_json.relative_to.return_value = MagicMock(parts=["tool1", "tool1.json"])
    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir
    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock_open - read index, read target (with matching CRC)
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL1_JSON_MATCHING_CRC).return_value,  # Use matching CRC data
        # No third call expected for write
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            assert excinfo.value.code == 0

    # Assertions
    assert mock_open_func.call_count == 2  # Only read calls
    assert mock_open_func.call_args_list[0][0][0] is mock_tool_index
    assert mock_open_func.call_args_list[1][0][0] is mock_target_json
    mock_target_json.is_file.assert_called()
    mock_tool_index.is_file.assert_called()


# --- Edge Case Path Parsing Test ---
@pytest.mark.skipif(update_crc_main is None, reason="Could not import script main function for testing")
@patch("scripts.update_json_crc_tool.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path")
def test_update_crc_edge_path_parsing(MockPath, mock_open_func, MockArgumentParser, tmp_path):
    """Test script handles a path that *might* confuse simple parsing (but should still work if using relative path logic)."""
    workspace_root = tmp_path
    tool_index_path_str = str(workspace_root / "src/zeroth_law/tools/tool_index.json")
    # Path with extra directory, but logically corresponds to tool2/subA
    target_json_path_str = str(workspace_root / "src/zeroth_law/tools/tool2/subA/unexpected_dir/subA.json")

    # Configure Mocks - Both files exist
    mock_tool_index = MagicMock(spec=Path, name="mock_tool_index")
    mock_tool_index.__str__.return_value = tool_index_path_str
    mock_tool_index.resolve.return_value = mock_tool_index
    mock_tool_index.is_file.return_value = True
    mock_tool_index.parent.name = "tools"
    mock_target_json = MagicMock(spec=Path, name="mock_target_json")
    mock_target_json.__str__.return_value = target_json_path_str
    mock_target_json.resolve.return_value = mock_target_json
    mock_target_json.is_file.return_value = True
    mock_target_json.stem = "subA"
    mock_target_json.parent = MagicMock(spec=Path, name="mock_target_json.parent")
    mock_target_json.parent.name = "unexpected_dir"  # Immediate parent is unexpected_dir
    mock_target_json.is_relative_to.return_value = True
    # Crucial: relative_to should return the logical structure
    mock_target_json.relative_to.return_value = MagicMock(parts=["tool2", "subA", "unexpected_dir", "subA.json"])

    mock_tools_dir = MagicMock(spec=Path, name="mock_tools_dir")
    mock_tools_dir.__str__.return_value = str(workspace_root / "src/zeroth_law/tools")
    mock_tools_dir.resolve.return_value = mock_tools_dir
    mock_ws_root_real = MagicMock(spec=Path, name="mock_ws_root_real")
    mock_ws_root_real.resolve.return_value = mock_ws_root_real

    def path_side_effect(path_arg):
        path_str = str(path_arg)
        if path_str == tool_index_path_str:
            return mock_tool_index
        elif path_str == target_json_path_str:
            return mock_target_json
        elif path_str == str(mock_tools_dir):
            return mock_tools_dir
        elif path_str == str(Path(__file__).parent.parent):
            return mock_ws_root_real
        new_mock = MagicMock(spec=Path)
        new_mock.__str__.return_value = path_str
        new_mock.resolve.return_value = new_mock
        return new_mock

    MockPath.side_effect = path_side_effect

    mock_parser_instance = MockArgumentParser.return_value
    mock_args = MagicMock()
    mock_args.file = mock_target_json
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock_open - read index, read target (missing CRC), write target
    mock_write_handle = mock_open().return_value
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_TOOL_INDEX_CONTENT).return_value,
        mock_open(read_data=MOCK_TOOL2_SUBA_JSON_MISSING_CRC).return_value,
        mock_write_handle,
    ]

    with (
        patch("scripts.update_json_crc_tool.WORKSPACE_ROOT", mock_ws_root_real),
        patch("scripts.update_json_crc_tool.TOOL_INDEX_PATH", mock_tool_index),
        patch("scripts.update_json_crc_tool.TOOLS_DIR", mock_tools_dir),
    ):
        test_args = ["update_json_crc_tool.py", "--file", target_json_path_str]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as excinfo:
                update_crc_main()
            # We expect this to succeed because get_tool_id_from_path should correctly identify 'tool2_subA'
            assert excinfo.value.code == 0

    # Assertions
    assert mock_open_func.call_count == 3
    assert mock_open_func.call_args_list[0][0][0] is mock_tool_index
    assert mock_open_func.call_args_list[1][0][0] is mock_target_json
    assert mock_open_func.call_args_list[2][0][0] is mock_target_json
    mock_target_json.is_file.assert_called()
    mock_tool_index.is_file.assert_called()
    written_data = "".join(call.args[0] for call in mock_write_handle.write.call_args_list)
    # Should write the CRC for tool2/subA ('0x55667788')
    assert json.loads(written_data) == json.loads(MOCK_TOOL2_SUBA_JSON_NEW_CRC)


# --- TODO: Implement tests for: ... (keep existing todos) ...

# --- REMOVE HELPER --- #
# ... (keep removed helper commented out or delete fully) ...
