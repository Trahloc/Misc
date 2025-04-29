import pytest
import json
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, mock_open

# Assume main cli entry point
from zeroth_law.cli import main as zlt_cli

# Mark all tests in this module to be skipped until implementation is ready
pytestmark = pytest.mark.skip(reason="Implementation for 'zlt tools definition' subcommand group is pending.")


# Helper function to create mock files/dirs
def setup_mock_tool_def(tmp_path: Path, tool_id: str, initial_data: dict) -> Path:
    tool_name = tool_id.split("_")[0]  # Simple assumption for test
    tool_dir = tmp_path / "src" / "zeroth_law" / "tools" / tool_name
    tool_dir.mkdir(parents=True, exist_ok=True)
    json_path = tool_dir / f"{tool_id}.json"
    with open(json_path, "w") as f:
        json.dump(initial_data, f, indent=2)
    return json_path


def setup_mock_capability_defs(tmp_path: Path, capabilities: dict):
    defs_path = tmp_path / "src" / "zeroth_law" / "zlt_capabilities.json"
    defs_path.parent.mkdir(parents=True, exist_ok=True)
    with open(defs_path, "w") as f:
        json.dump(capabilities, f, indent=2)
    return defs_path


# Test case for add-capability
def test_add_capability_success(tmp_path):  # Use pytest tmp_path fixture
    """Test successfully adding a valid capability."""
    runner = CliRunner()
    tool_id = "mytool_testcmd"
    capability_to_add = "TestCapability"
    initial_def_data = {
        "command_sequence": ["mytool", "testcmd"],
        "metadata": {
            "tool_name": "mytool",
            "provides_capabilities": ["ExistingCapability"],
            "supported_filetypes": [".test"],
            # ... other metadata
        },
        # ... other sections
    }
    valid_capabilities = {
        "ExistingCapability": {"description": "..."},
        "TestCapability": {"description": "A new capability for testing."},
    }

    # --- Setup --- Create mock files in tmp_path
    tool_json_path = setup_mock_tool_def(tmp_path, tool_id, initial_def_data)
    cap_defs_path = setup_mock_capability_defs(tmp_path, valid_capabilities)

    # Mock WORKSPACE_ROOT lookup and definition file paths within the command's logic
    # This assumes the command logic uses functions/constants to find these paths
    with (
        patch("zeroth_law.subcommands.tools.definition.WORKSPACE_ROOT", tmp_path),
        patch("zeroth_law.subcommands.tools.definition.TOOLS_DIR", tmp_path / "src/zeroth_law/tools"),
        patch("zeroth_law.subcommands.tools.definition.ZLT_CAPABILITIES_PATH", cap_defs_path),
    ):  # Assuming a constant like this
        # --- Act --- Run the CLI command
        result = runner.invoke(
            zlt_cli,
            [
                "tools",  # <-- Updated path
                "definition",
                "add-capability",
                tool_id,
                capability_to_add,
            ],
        )

    # --- Assert --- Check results
    assert result.exit_code == 0, f"CLI failed: {result.output}\nException: {result.exception}"
    assert f"Successfully added capability '{capability_to_add}'" in result.output

    # Verify file modification
    with open(tool_json_path, "r") as f:
        updated_data = json.load(f)

    assert capability_to_add in updated_data["metadata"]["provides_capabilities"]
    assert "ExistingCapability" in updated_data["metadata"]["provides_capabilities"]
    assert len(updated_data["metadata"]["provides_capabilities"]) == 2


# TODO: Add more tests for add-capability:
# - Adding a capability that already exists (should be idempotent or inform user)
# - Adding an invalid capability (not in zlt_capabilities.json)
# - Tool ID not found
# - File I/O errors
# - Missing metadata key
# - Missing provides_capabilities key


def test_remove_capability_success(tmp_path):
    """Test successfully removing an existing capability."""
    runner = CliRunner()
    tool_id = "mytool_testcmd"
    capability_to_remove = "ExistingCapability"
    initial_def_data = {
        "command_sequence": ["mytool", "testcmd"],
        "metadata": {
            "tool_name": "mytool",
            "provides_capabilities": ["ExistingCapability", "AnotherCap"],
            "supported_filetypes": [".test"],
        },
    }
    valid_capabilities = {  # Not strictly needed for remove, but good practice
        "ExistingCapability": {"description": "..."},
        "AnotherCap": {"description": "..."},
    }
    tool_json_path = setup_mock_tool_def(tmp_path, tool_id, initial_def_data)
    cap_defs_path = setup_mock_capability_defs(tmp_path, valid_capabilities)

    with (
        patch("zeroth_law.subcommands.tools.definition.WORKSPACE_ROOT", tmp_path),
        patch("zeroth_law.subcommands.tools.definition.TOOLS_DIR", tmp_path / "src/zeroth_law/tools"),
        patch("zeroth_law.subcommands.tools.definition.ZLT_CAPABILITIES_PATH", cap_defs_path),
    ):
        result = runner.invoke(
            zlt_cli,
            [
                "tools",  # <-- Updated path
                "definition",
                "remove-capability",
                tool_id,
                capability_to_remove,
            ],
        )

    assert result.exit_code == 0, f"CLI failed: {result.output}\nException: {result.exception}"
    assert f"Successfully removed capability '{capability_to_remove}'" in result.output
    with open(tool_json_path, "r") as f:
        updated_data = json.load(f)
    assert capability_to_remove not in updated_data["metadata"]["provides_capabilities"]
    assert "AnotherCap" in updated_data["metadata"]["provides_capabilities"]
    assert len(updated_data["metadata"]["provides_capabilities"]) == 1


def test_set_filetypes_success(tmp_path):
    """Test successfully setting (overwriting) filetypes."""
    runner = CliRunner()
    tool_id = "mytool_testcmd"
    new_filetypes = [".py", ".pyi"]
    initial_def_data = {
        "command_sequence": ["mytool", "testcmd"],
        "metadata": {
            "tool_name": "mytool",
            "provides_capabilities": ["Linter"],
            "supported_filetypes": [".test", ".old"],
        },
    }
    tool_json_path = setup_mock_tool_def(tmp_path, tool_id, initial_def_data)
    # No capabilities file needed for this test

    with (
        patch("zeroth_law.subcommands.tools.definition.WORKSPACE_ROOT", tmp_path),
        patch("zeroth_law.subcommands.tools.definition.TOOLS_DIR", tmp_path / "src/zeroth_law/tools"),
    ):
        result = runner.invoke(
            zlt_cli,
            [
                "tools",  # <-- Updated path
                "definition",
                "set-filetypes",
                tool_id,
            ]
            + new_filetypes,
        )  # Pass new types as separate args

    assert result.exit_code == 0, f"CLI failed: {result.output}\nException: {result.exception}"
    assert f"Successfully set filetypes for tool '{tool_id}'" in result.output
    with open(tool_json_path, "r") as f:
        updated_data = json.load(f)
    # Check list content regardless of order
    assert sorted(updated_data["metadata"]["supported_filetypes"]) == sorted(new_filetypes)


def test_map_option_success(tmp_path):
    """Test successfully mapping a tool option to a ZLT option."""
    runner = CliRunner()
    tool_id = "mytool_testcmd"
    tool_option = "--verbose-mode"
    zlt_option = "verbose"
    initial_def_data = {
        "command_sequence": ["mytool", "testcmd"],
        "options": [
            {"name": "--verbose-mode", "type": "flag", "description": "..."},
            {"name": "--config-file", "type": "value", "description": "...", "maps_to_zlt_option": "config"},
        ],
        "arguments": [],
        "metadata": {"tool_name": "mytool"},
    }
    valid_zlt_options = {
        "verbose": {"type": "flag", "description": "..."},
        "config": {"type": "value", "description": "..."},
    }
    tool_json_path = setup_mock_tool_def(tmp_path, tool_id, initial_def_data)
    # Mock the options definitions file path
    opts_defs_path = tmp_path / "src" / "zeroth_law" / "zlt_options_definitions.json"
    opts_defs_path.parent.mkdir(parents=True, exist_ok=True)
    with open(opts_defs_path, "w") as f:
        json.dump(valid_zlt_options, f)

    with (
        patch("zeroth_law.subcommands.tools.definition.WORKSPACE_ROOT", tmp_path),
        patch("zeroth_law.subcommands.tools.definition.TOOLS_DIR", tmp_path / "src/zeroth_law/tools"),
        patch("zeroth_law.subcommands.tools.definition.ZLT_OPTIONS_DEFINITIONS_PATH", opts_defs_path),
    ):  # Assuming constant
        result = runner.invoke(
            zlt_cli,
            [
                "tools",  # <-- Updated path
                "definition",
                "map-option",
                tool_id,
                "--",
                tool_option,
                zlt_option,
            ],
        )

    assert result.exit_code == 0, f"CLI failed: {result.output}\nException: {result.exception}"
    assert f"Successfully mapped tool option '{tool_option}' to ZLT option '{zlt_option}'" in result.output
    with open(tool_json_path, "r") as f:
        updated_data = json.load(f)
    # Find the correct option object in the list and check its mapping
    mapped_option = next((opt for opt in updated_data["options"] if opt.get("name") == tool_option), None)
    assert mapped_option is not None
    assert mapped_option.get("maps_to_zlt_option") == zlt_option
    # Check other option is untouched
    other_option = next((opt for opt in updated_data["options"] if opt.get("name") == "--config-file"), None)
    assert other_option.get("maps_to_zlt_option") == "config"


def test_unmap_option_success(tmp_path):
    """Test successfully removing an option mapping."""
    runner = CliRunner()
    tool_id = "mytool_testcmd"
    tool_option_to_unmap = "--config-file"
    initial_def_data = {
        "command_sequence": ["mytool", "testcmd"],
        "options": [
            {"name": "--verbose-mode", "type": "flag", "description": "...", "maps_to_zlt_option": "verbose"},
            {"name": "--config-file", "type": "value", "description": "...", "maps_to_zlt_option": "config"},
        ],
        "arguments": [],
        "metadata": {"tool_name": "mytool"},
    }
    tool_json_path = setup_mock_tool_def(tmp_path, tool_id, initial_def_data)
    # No options defs needed for unmap

    with (
        patch("zeroth_law.subcommands.tools.definition.WORKSPACE_ROOT", tmp_path),
        patch("zeroth_law.subcommands.tools.definition.TOOLS_DIR", tmp_path / "src/zeroth_law/tools"),
    ):
        result = runner.invoke(
            zlt_cli,
            [
                "tools",  # <-- Updated path
                "definition",
                "unmap-option",
                tool_id,
                "--",
                tool_option_to_unmap,
            ],
        )

    assert result.exit_code == 0, f"CLI failed: {result.output}\nException: {result.exception}"
    assert f"Successfully unmapped tool option '{tool_option_to_unmap}'" in result.output
    with open(tool_json_path, "r") as f:
        updated_data = json.load(f)
    # Find the correct option object and check mapping is removed
    unmapped_option = next((opt for opt in updated_data["options"] if opt.get("name") == tool_option_to_unmap), None)
    assert unmapped_option is not None
    assert "maps_to_zlt_option" not in unmapped_option
    # Check other option is untouched
    other_option = next((opt for opt in updated_data["options"] if opt.get("name") == "--verbose-mode"), None)
    assert other_option.get("maps_to_zlt_option") == "verbose"


# TODO: Add failure case tests for remove, set, map, unmap
