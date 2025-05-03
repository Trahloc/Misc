"""Tests for the `zlt tools sync` command."""

import pytest
import sys
import json
import zlib
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import shutil
import time
import os

from click.testing import CliRunner

# --- Corrected import for CLI group --- #
from zeroth_law.cli import create_cli_group

zlt_cli = create_cli_group()

# --- Import the command function directly --- #
from zeroth_law.common import path_utils
from zeroth_law.common.config_loader import load_config
from zeroth_law.common.git_utils import find_git_root
from zeroth_law.subcommands._tools.sync import sync as sync_command

# --- Import hierarchical utils --- #
from zeroth_law.common.hierarchical_utils import (
    parse_to_nested_dict,
    ParsedHierarchy,
    check_list_conflicts,
    get_effective_status,
)

# --- Import tooling utils --- #
from zeroth_law.lib.tooling.tools_dir_scanner import scan_whitelisted_sequences

# Default config structure for pyproject.toml
DEFAULT_PYPROJECT_CONTENT = """
[tool.zerothlaw]
project_name = "zeroth_law"

[tool.zerothlaw.managed-tools]
whitelist = [
    "toolA",
    "toolB:sub1",
    "python", # Essential for python script testing
]
blacklist = [
    "toolC",
]
"""

# Default tool index content
DEFAULT_TOOL_INDEX = {
    "toolA": {"crc": hex(zlib.crc32(b"toolA help")), "checked_timestamp": 1.0, "updated_timestamp": 1.0},
    "toolB": {
        "crc": None,
        "checked_timestamp": 1.0,
        "updated_timestamp": 1.0,
        "subcommands": {
            "sub1": {"crc": hex(zlib.crc32(b"toolB sub1 help")), "checked_timestamp": 1.0, "updated_timestamp": 1.0}
        },
    },
}


@pytest.fixture
def mock_sync_env(tmp_path):
    """Fixture to set up a mocked environment for sync tests."""
    project_root = tmp_path
    mock_venv = project_root / ".venv"
    mock_venv_bin = mock_venv / "bin"
    mock_venv_bin.mkdir(parents=True)
    mock_tools_dir = project_root / "src" / "zeroth_law" / "tools"
    mock_tools_dir.mkdir(parents=True)
    mock_index_path = mock_tools_dir / "tool_index.json"

    # Create mock executables
    (mock_venv_bin / "toolA").touch(mode=0o755)
    (mock_venv_bin / "toolB").touch(mode=0o755)
    (mock_venv_bin / "toolC").touch(mode=0o755)  # Blacklisted
    (mock_venv_bin / "toolD").touch(mode=0o755)  # Unclassified
    (mock_venv_bin / "python").touch(mode=0o755)  # Whitelisted

    # Create mock pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(DEFAULT_PYPROJECT_CONTENT)

    # Create mock tool dirs based on whitelist initially
    (mock_tools_dir / "toolA").mkdir()
    (mock_tools_dir / "toolB" / "sub1").mkdir(parents=True)
    (mock_tools_dir / "python").mkdir()

    # Mock initial index state
    mock_index_path.write_text(json.dumps(DEFAULT_TOOL_INDEX, indent=2))

    # Mock baseline files corresponding to index
    (mock_tools_dir / "toolA" / "toolA.txt").write_text("toolA help")
    (mock_tools_dir / "toolB" / "sub1" / "sub1.txt").write_text("toolB sub1 help")

    mocks = {
        "sys.prefix": patch("sys.prefix", str(mock_venv)),
        # Patch config loading to return our default structure
        "config_loader": patch(
            "zeroth_law.subcommands.tools.sync.load_config",
            return_value={
                "managed-tools": {
                    "whitelist": ["toolA", "toolB:sub1", "python"],
                    "blacklist": ["toolC"],
                }
            },
        ),
        # Patch index utils
        "load_index": patch(
            "zeroth_law.subcommands.tools.sync.load_tool_index", return_value=json.loads(json.dumps(DEFAULT_TOOL_INDEX))
        ),  # Deep copy
        "save_index": patch("zeroth_law.subcommands.tools.sync.save_tool_index"),
        "get_index_entry": patch(
            "zeroth_law.subcommands.tools.sync.get_index_entry",
            side_effect=lambda data, seq: get_index_entry(data, seq),
        ),  # Use real logic with mocked data
        "update_index_entry": patch(
            "zeroth_law.subcommands.tools.sync.update_index_entry",
            side_effect=lambda data, seq, **kw: update_index_entry(data, seq, **kw),
        ),
        # Patch Podman functions
        "start_podman": patch(
            "zeroth_law.subcommands.tools.sync._start_podman_runner", return_value=True
        ),  # Assume success
        "stop_podman": patch("zeroth_law.subcommands.tools.sync._stop_podman_runner"),
        "capture_output": patch("zeroth_law.subcommands.tools.sync._capture_command_output"),  # Configure per test
        # Patch filesystem checks
        "os_access": patch("os.access", return_value=True),  # Assume all files in mock bin are executable
        "path_exists": patch("pathlib.Path.exists", wraps=Path.exists),  # Use real exists but allow override
        "path_is_file": patch("pathlib.Path.is_file", wraps=Path.is_file),
        "path_is_dir": patch("pathlib.Path.is_dir", wraps=Path.is_dir),
        "path_iterdir": patch("pathlib.Path.iterdir", wraps=Path.iterdir),
        "os_makedirs": patch("os.makedirs", wraps=os.makedirs),
        # Patch hierarchical utils (use real ones, they are tested)
        "parse_hierarchical": patch(
            "zeroth_law.subcommands.tools.sync.parse_to_nested_dict", wraps=parse_to_nested_dict
        ),
        "check_conflicts": patch("zeroth_law.subcommands.tools.sync.check_list_conflicts", wraps=check_list_conflicts),
        "get_status": patch("zeroth_law.subcommands.tools.sync.get_effective_status", wraps=get_effective_status),
        # Patch sequence scanner (use real one)
        "scan_sequences": patch(
            "zeroth_law.subcommands.tools.sync.scan_whitelisted_sequences", wraps=scan_whitelisted_sequences
        ),
    }

    # Enter all patches
    for m in mocks.values():
        m.start()

    # Yield context: runner and paths/mocks
    yield {
        "runner": CliRunner(),
        "project_root": project_root,
        "venv_bin": mock_venv_bin,
        "tools_dir": mock_tools_dir,
        "index_path": mock_index_path,
        "mocks": mocks,
    }

    # Exit all patches
    for m in mocks.values():
        m.stop()


# Placeholder test using the fixture
# def test_sync_placeholder_invocation(mock_sync_env):
#     """Test that the sync command can be invoked without crashing."""
#     runner = mock_sync_env["runner"]
#     # A basic run without flags that should hit some initial checks
#     result = runner.invoke(zlt_cli, ["tools", "sync"], catch_exceptions=False)
#     # We expect this to fail because toolD is unclassified, but it shouldn't crash
#     assert result.exit_code != 0
#     assert "Unclassified executables found" in result.output
#     assert "toolD" in result.output

# --- Add Specific Integration Tests Below --- #


def test_sync_fails_on_unclassified_tool(mock_sync_env):
    """Test Step 3 Failure: Sync fails if an executable in venv is not in whitelist or blacklist."""
    runner = mock_sync_env["runner"]
    result = runner.invoke(zlt_cli, ["tools", "sync"], catch_exceptions=False)

    assert result.exit_code != 0  # Expect failure
    assert "Unclassified executables found in venv" in result.output
    assert "- toolD" in result.output  # Check specific tool listed
    assert "Please add them to the whitelist or blacklist" in result.output


def test_sync_fails_on_orphan_tool_dir(mock_sync_env):
    """Test Step 4 Failure: Sync fails if a dir exists in tools/ that isn't whitelisted."""
    runner = mock_sync_env["runner"]
    tools_dir = mock_sync_env["tools_dir"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Create an orphan directory in tools/
    orphan_dir_name = "toolX"
    (tools_dir / orphan_dir_name).mkdir()

    result = runner.invoke(zlt_cli, ["tools", "sync"], catch_exceptions=False)

    assert result.exit_code != 0  # Expect failure
    assert "Orphan tool directories found" in result.output
    assert f"- {orphan_dir_name}" in result.output
    assert "Whitelist the corresponding tool or remove the directory" in result.output


def test_sync_success_no_changes(mock_sync_env):
    """Test Step 6 Success (No Change): Run sync --generate with consistent data."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    index_path = mock_sync_env["index_path"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Configure mock capture output to return consistent data
    # Key: sequence tuple, Value: (stdout_bytes, stderr_bytes, returncode)
    capture_results = {
        ("toolA", "--help"): (b"toolA help", b"", 0),
        ("toolB", "sub1", "--help"): (b"toolB sub1 help", b"", 0),
        # python tool is whitelisted but might not have baseline/index entry yet
        # Let's assume it gets called and returns something
        ("python", "--help"): (b"Python help", b"", 0),
    }

    def mock_capture_side_effect(cmd_seq, *args, **kwargs):
        # Convert list from sync.py back to tuple for dict key
        key = tuple(cmd_seq[-len(cmd_seq) :])  # Extract relevant sequence parts
        # Simplistic match for testing, might need refinement
        if key == ("toolA",):
            lookup_key = ("toolA", "--help")
        elif key == ("toolB", "sub1"):
            lookup_key = ("toolB", "sub1", "--help")
        elif key == ("python",):
            lookup_key = ("python", "--help")
        else:
            return (b"Unexpected call", b"Error", 1)  # Fail test if unexpected call
        return capture_results.get(lookup_key, (b"Default output", b"", 0))

    mocks["capture_output"].side_effect = mock_capture_side_effect

    # Mock time to control timestamp checks
    with patch("time.time", return_value=1000.0):
        result = runner.invoke(zlt_cli, ["tools", "sync", "--generate"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "Sync process complete" in result.output

    # Verify Podman start/stop called
    mocks["start_podman"].assert_called_once()
    mocks["stop_podman"].assert_called_once()

    # Verify capture was called for whitelisted items (toolA, toolB:sub1, python)
    assert mocks["capture_output"].call_count >= 3  # May include python
    # Check calls more specifically if needed

    # Verify index save was called (even if only timestamps updated)
    mocks["save_index"].assert_called_once()
    # Check saved data - should have updated checked_timestamp to 1000.0
    saved_data = mocks["save_index"].call_args[0][1]
    assert saved_data["toolA"]["checked_timestamp"] == 1000.0
    assert saved_data["toolB"]["subcommands"]["sub1"]["checked_timestamp"] == 1000.0
    # Check python entry was added/updated if capture was mocked for it
    assert "python" in saved_data
    assert saved_data["python"]["checked_timestamp"] == 1000.0

    # Verify no unexpected errors or messages
    assert "Orphan" not in result.output
    assert "Unclassified" not in result.output
    assert "needs interpretation" not in result.output
    assert "New subcommand sequences were added" not in result.output


def test_sync_success_baseline_update(mock_sync_env):
    """Test Step 6 Success (Baseline Update): Run sync --generate with CRC mismatch."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]
    index_path = mock_sync_env["index_path"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Simulate podman returning NEW help text for toolA
    new_toolA_help = b"toolA help v2"
    new_toolA_crc = hex(zlib.crc32(new_toolA_help))

    # Configure mock capture output
    capture_results = {
        ("toolA", "--help"): (new_toolA_help, b"", 0),
        ("toolB", "sub1", "--help"): (b"toolB sub1 help", b"", 0),  # Consistent
        ("python", "--help"): (b"Python help", b"", 0),
    }

    def mock_capture_side_effect(cmd_seq, *args, **kwargs):
        key = tuple(cmd_seq[-len(cmd_seq) :])
        if key == ("toolA",):
            lookup_key = ("toolA", "--help")
        elif key == ("toolB", "sub1"):
            lookup_key = ("toolB", "sub1", "--help")
        elif key == ("python",):
            lookup_key = ("python", "--help")
        else:
            return (b"Unexpected call", b"Error", 1)
        return capture_results.get(lookup_key, (b"Default output", b"", 0))

    mocks["capture_output"].side_effect = mock_capture_side_effect

    # Mock time
    with patch("time.time", return_value=2000.0):
        result = runner.invoke(zlt_cli, ["tools", "sync", "--generate"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "Sync process complete" in result.output

    # Verify Podman start/stop called
    mocks["start_podman"].assert_called_once()
    mocks["stop_podman"].assert_called_once()

    # Verify capture was called
    assert mocks["capture_output"].call_count >= 3

    # Verify baseline .txt file was updated for toolA
    toolA_txt_path = tools_dir / "toolA" / "toolA.txt"
    assert toolA_txt_path.read_text() == new_toolA_help.decode()

    # Verify index save was called
    mocks["save_index"].assert_called_once()
    # Check saved data - toolA should have new crc and timestamp
    saved_data = mocks["save_index"].call_args[0][1]
    assert saved_data["toolA"]["crc"] == new_toolA_crc
    assert saved_data["toolA"]["checked_timestamp"] == 2000.0
    assert saved_data["toolA"]["updated_timestamp"] == 2000.0
    # Check toolB sub1 only had checked_timestamp updated
    assert (
        saved_data["toolB"]["subcommands"]["sub1"]["crc"] == DEFAULT_TOOL_INDEX["toolB"]["subcommands"]["sub1"]["crc"]
    )
    assert saved_data["toolB"]["subcommands"]["sub1"]["checked_timestamp"] == 2000.0
    assert saved_data["toolB"]["subcommands"]["sub1"]["updated_timestamp"] == 1.0  # Original timestamp
    # Check python entry
    assert saved_data["python"]["checked_timestamp"] == 2000.0

    # Verify no unexpected errors
    assert "Orphan" not in result.output
    assert "Unclassified" not in result.output


@pytest.mark.parametrize(
    "current_time, cli_args, expect_capture_call, expect_txt_update, expected_check_ts, expected_update_ts",
    [
        # Scenario 1: Recently checked, default skip (168h), should skip update
        (10.0, ["tools", "sync", "--generate"], False, False, 1.0, 1.0),
        # Scenario 2: Not recently checked, default skip (168h), should process and update
        (170 * 3600.0, ["tools", "sync", "--generate"], True, True, 170 * 3600.0, 170 * 3600.0),
        # Scenario 3: Recently checked, but --force used, should process and update
        (10.0, ["tools", "sync", "--generate", "--force"], True, True, 10.0, 10.0),
        # Scenario 4: Within custom skip hours (10h), should skip
        (9 * 3600.0, ["tools", "sync", "--generate", "--skip-hours", "10"], False, False, 1.0, 1.0),
        # Scenario 5: Outside custom skip hours (10h), should process
        (11 * 3600.0, ["tools", "sync", "--generate", "--skip-hours", "10"], True, True, 11 * 3600.0, 11 * 3600.0),
    ],
    ids=["skip_default", "process_default", "force", "skip_custom", "process_custom"],
)
def test_sync_timestamp_logic(
    mock_sync_env, current_time, cli_args, expect_capture_call, expect_txt_update, expected_check_ts, expected_update_ts
):
    """Test Step 6 Timestamp Logic: --force and --skip-hours (--check-since-hours)."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]
    toolA_txt_path = tools_dir / "toolA" / "toolA.txt"
    original_toolA_txt = toolA_txt_path.read_text()

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Simulate podman returning NEW help text for toolA if called
    new_toolA_help = b"toolA help v2 timestamp test"
    new_toolA_crc = hex(zlib.crc32(new_toolA_help))

    # Reset mock before each parametrized run
    mocks["capture_output"].reset_mock()
    mocks["save_index"].reset_mock()

    # Configure mock capture output
    capture_results = {
        ("toolA", "--help"): (new_toolA_help, b"", 0),
        ("toolB", "sub1", "--help"): (b"toolB sub1 help", b"", 0),  # Consistent
        ("python", "--help"): (b"Python help", b"", 0),
    }

    def mock_capture_side_effect(cmd_seq, *args, **kwargs):
        key = tuple(cmd_seq[-len(cmd_seq) :])
        if key == ("toolA",):
            lookup_key = ("toolA", "--help")
        elif key == ("toolB", "sub1"):
            lookup_key = ("toolB", "sub1", "--help")
        elif key == ("python",):
            lookup_key = ("python", "--help")
        else:
            # Use print for debugging paramatrized tests if needed
            # print(f"UNEXPECTED CAPTURE CALL: {key}")
            return (b"Unexpected call", b"Error", 1)
        return capture_results.get(lookup_key, (b"Default output", b"", 0))

    mocks["capture_output"].side_effect = mock_capture_side_effect

    # Mock time.time() for the duration of this invoke call
    with patch("time.time", return_value=current_time):
        result = runner.invoke(zlt_cli, cli_args, catch_exceptions=False)

    assert result.exit_code == 0  # Expect successful completion overall

    # Check if capture was called for toolA specifically
    toolA_capture_called = any(call_args[0][0][-1] == "toolA" for call_args in mocks["capture_output"].call_args_list)
    assert toolA_capture_called == expect_capture_call

    # Check if toolA.txt was updated
    toolA_txt_updated = toolA_txt_path.read_text() != original_toolA_txt
    assert toolA_txt_updated == expect_txt_update
    if expect_txt_update:
        assert toolA_txt_path.read_text() == new_toolA_help.decode()

    # Check the final saved index state for toolA
    mocks["save_index"].assert_called_once()  # Save should always be called if successful
    saved_data = mocks["save_index"].call_args[0][1]

    assert saved_data["toolA"]["checked_timestamp"] == expected_check_ts
    assert saved_data["toolA"]["updated_timestamp"] == expected_update_ts
    if expect_txt_update:
        assert saved_data["toolA"]["crc"] == new_toolA_crc
    else:
        assert saved_data["toolA"]["crc"] == DEFAULT_TOOL_INDEX["toolA"]["crc"]


def test_sync_fails_on_rapid_updates(mock_sync_env):
    """Test Step 6 Warning/Failure: Sync fails if >3 baselines change rapidly."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()
    # Add another whitelisted tool to trigger multiple updates
    (mock_sync_env["venv_bin"] / "toolE_whitelisted").touch(mode=0o755)
    (mock_sync_env["venv_bin"] / "toolF_whitelisted").touch(mode=0o755)
    (mock_sync_env["venv_bin"] / "toolG_whitelisted").touch(mode=0o755)
    # Need to update the mocked config loader for these
    mocks["config_loader"].return_value["managed-tools"]["whitelist"].extend(
        ["toolE_whitelisted", "toolF_whitelisted", "toolG_whitelisted"]
    )
    # Add initial entries to index (checked long ago, need update)
    initial_index = json.loads(json.dumps(DEFAULT_TOOL_INDEX))
    initial_index["toolE_whitelisted"] = {"crc": "0xEEE", "checked_timestamp": 1.0, "updated_timestamp": 1.0}
    initial_index["toolF_whitelisted"] = {"crc": "0xFFF", "checked_timestamp": 1.0, "updated_timestamp": 1.0}
    initial_index["toolG_whitelisted"] = {"crc": "0xGGG", "checked_timestamp": 1.0, "updated_timestamp": 1.0}
    mocks["load_index"].return_value = initial_index

    # Simulate podman returning NEW help text for *all* tools
    capture_results = {
        ("toolA", "--help"): (b"toolA help v2 rapid", b"", 0),
        ("toolB", "sub1", "--help"): (b"toolB sub1 help v2 rapid", b"", 0),
        ("python", "--help"): (b"Python help v2 rapid", b"", 0),
        ("toolE_whitelisted", "--help"): (b"toolE help v2 rapid", b"", 0),
        ("toolF_whitelisted", "--help"): (b"toolF help v2 rapid", b"", 0),
        ("toolG_whitelisted", "--help"): (b"toolG help v2 rapid", b"", 0),
    }

    def mock_capture_side_effect(cmd_seq, *args, **kwargs):
        key = tuple(cmd_seq[-len(cmd_seq) :])
        lookup_key = (*key, "--help")  # Simplistic assumption
        return capture_results.get(lookup_key, (b"Default output", b"", 0))

    mocks["capture_output"].side_effect = mock_capture_side_effect

    # Mock time - ensure current time is within the --update-since-hours (default 48) of initial check (1.0)
    current_time = 40 * 3600.0  # 40 hours after initial check
    with patch("time.time", return_value=current_time):
        # Run with default update-since-hours (48)
        result = runner.invoke(zlt_cli, ["tools", "sync", "--generate"], catch_exceptions=False)

    # Expect failure because 4+ tools updated within 48 hours of initial check
    assert result.exit_code != 0
    assert "Rapid Update Threshold Exceeded" in result.output
    assert "baselines changed within the 48 hour threshold" in result.output

    # Verify index was *not* saved in this failure case
    mocks["save_index"].assert_not_called()


def test_sync_fails_missing_json(mock_sync_env):
    """Test Step 7 Failure: Sync fails if a .txt exists but its .json is missing."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Ensure toolA.txt exists but toolA.json does NOT
    toolA_json_path = tools_dir / "toolA" / "toolA.json"
    if toolA_json_path.exists():
        toolA_json_path.unlink()
    assert (tools_dir / "toolA" / "toolA.txt").exists()  # Precondition

    # Configure mock capture output (should not be called if generate=False)
    mocks["capture_output"].side_effect = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("Capture should not be called")
    )

    # Run sync WITHOUT --generate
    result = runner.invoke(zlt_cli, ["tools", "sync"], catch_exceptions=False)

    # Expect failure at Step 7
    assert result.exit_code != 0
    assert "Missing or inconsistent JSON definition found" in result.output
    assert "toolA" in result.output  # Sequence ID
    assert (
        str(toolA_json_path.relative_to(mock_sync_env["project_root"])).replace("\\", "/") in result.output
    )  # Relative path
    assert "Reason: JSON file missing" in result.output
    assert "Run AI interpretation (Step 8)" in result.output

    # Verify Podman was NOT started
    mocks["start_podman"].assert_not_called()
    mocks["stop_podman"].assert_not_called()
    # Verify index was NOT saved
    mocks["save_index"].assert_not_called()


def test_sync_fails_outdated_json(mock_sync_env):
    """Test Step 7 Failure: Sync fails if .json CRC doesn't match index CRC."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Ensure toolA.txt and toolA.json exist
    toolA_json_path = tools_dir / "toolA" / "toolA.json"
    toolA_json_content = {
        "metadata": {"ground_truth_crc": "0xOLDCRC"},  # Mismatched CRC
        "command": ["toolA"],
    }
    toolA_json_path.write_text(json.dumps(toolA_json_content, indent=4))
    assert (tools_dir / "toolA" / "toolA.txt").exists()  # Precondition

    # Mock capture output (should not be called)
    mocks["capture_output"].side_effect = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("Capture should not be called")
    )

    # Run sync WITHOUT --generate
    result = runner.invoke(zlt_cli, ["tools", "sync"], catch_exceptions=False)

    # Expect failure at Step 7
    assert result.exit_code != 0
    assert "Missing or inconsistent JSON definition found" in result.output
    assert "toolA" in result.output  # Sequence ID
    assert (
        str(toolA_json_path.relative_to(mock_sync_env["project_root"])).replace("\\", "/") in result.output
    )  # Relative path
    assert "Reason: JSON metadata.ground_truth_crc mismatch" in result.output
    assert "0xOLDCRC" in result.output  # Show the bad CRC
    assert DEFAULT_TOOL_INDEX["toolA"]["crc"] in result.output  # Show expected CRC
    assert "Run AI interpretation (Step 8)" in result.output

    # Verify Podman was NOT started
    mocks["start_podman"].assert_not_called()
    mocks["stop_podman"].assert_not_called()
    # Verify index was NOT saved
    mocks["save_index"].assert_not_called()


def test_sync_step9_subcommand_discovery(mock_sync_env):
    """Test Step 9 Discovery: Run sync, discover new subcommand from consistent parent JSON."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Ensure toolA.txt and toolA.json exist AND are consistent
    toolA_json_path = tools_dir / "toolA" / "toolA.json"
    toolA_crc = DEFAULT_TOOL_INDEX["toolA"]["crc"]
    toolA_json_content = {
        "metadata": {"ground_truth_crc": toolA_crc},  # Consistent CRC
        "command": ["toolA"],
        "subcommands_detail": {"new_sub": {"description": "A newly discovered subcommand"}},
    }
    toolA_json_path.write_text(json.dumps(toolA_json_content, indent=4))
    assert (tools_dir / "toolA" / "toolA.txt").exists()  # Precondition

    # Add new_sub to whitelist so it gets picked up
    mocks["config_loader"].return_value["managed-tools"]["whitelist"].append("toolA:new_sub")
    # Need to regenerate the parsed trees used internally
    wl_tree = parse_to_nested_dict(mocks["config_loader"].return_value["managed-tools"]["whitelist"])
    bl_tree = parse_to_nested_dict(mocks["config_loader"].return_value["managed-tools"]["blacklist"])
    mocks["parse_hierarchical"].side_effect = [wl_tree, bl_tree]  # First call in sync
    mocks["get_status"].side_effect = lambda seq, *args: get_effective_status(seq, wl_tree, bl_tree)

    # Define a helper function to raise the assertion
    def _raise_capture_error(*args, **kwargs):
        raise AssertionError("Capture should not be called")

    mocks["capture_output"].side_effect = _raise_capture_error

    result = runner.invoke(zlt_cli, ["tools", "sync"], catch_exceptions=False)

    # Expect success (exit code 0) but message indicates new sequences added
    assert result.exit_code == 0
    assert "New subcommand sequences were added to the index" in result.output
    assert "toolA_new_sub" in result.output
    assert "Please re-run `zlt tools sync --generate`" in result.output

    # Verify Podman was NOT started
    mocks["start_podman"].assert_not_called()
    mocks["stop_podman"].assert_not_called()

    # Verify index WAS saved with the new entry
    mocks["save_index"].assert_called_once()
    saved_data = mocks["save_index"].call_args[0][1]
    assert "toolA" in saved_data
    assert "subcommands" in saved_data["toolA"]
    assert "new_sub" in saved_data["toolA"]["subcommands"]
    assert saved_data["toolA"]["subcommands"]["new_sub"]["crc"] is None  # New entry has no CRC yet
    assert "checked_timestamp" in saved_data["toolA"]["subcommands"]["new_sub"]
    assert "updated_timestamp" in saved_data["toolA"]["subcommands"]["new_sub"]

    # Verify the new directory was created
    new_sub_dir = tools_dir / "toolA" / "new_sub"
    assert new_sub_dir.is_dir()


def test_sync_step10_completion(mock_sync_env):
    """Test Step 10 Completion: Run sync where Steps 7 & 9 find nothing to do."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Ensure toolA.txt and toolA.json exist AND are consistent
    toolA_json_path = tools_dir / "toolA" / "toolA.json"
    toolA_crc = DEFAULT_TOOL_INDEX["toolA"]["crc"]
    toolA_json_content = {
        "metadata": {"ground_truth_crc": toolA_crc},  # Consistent CRC
        "command": ["toolA"],
        # NO subcommands_detail defined here
    }
    toolA_json_path.write_text(json.dumps(toolA_json_content, indent=4))
    assert (tools_dir / "toolA" / "toolA.txt").exists()  # Precondition

    # Ensure toolB sub1.txt and sub1.json exist AND are consistent
    toolB_sub1_json_path = tools_dir / "toolB" / "sub1" / "sub1.json"
    toolB_sub1_crc = DEFAULT_TOOL_INDEX["toolB"]["subcommands"]["sub1"]["crc"]
    toolB_sub1_json_content = {
        "metadata": {"ground_truth_crc": toolB_sub1_crc},  # Consistent CRC
        "command": ["toolB", "sub1"],
    }
    toolB_sub1_json_path.write_text(json.dumps(toolB_sub1_json_content, indent=4))
    assert (tools_dir / "toolB" / "sub1" / "sub1.txt").exists()  # Precondition

    # Ensure python dir exists but has no json (so step 7 passes for it)
    python_json_path = tools_dir / "python" / "python.json"
    if python_json_path.exists():
        python_json_path.unlink()
    # Assume python.txt doesn't exist, so step 7 skips it
    python_txt_path = tools_dir / "python" / "python.txt"
    if python_txt_path.exists():
        python_txt_path.unlink()

    # Configure mock capture output (should not be called)
    mocks["capture_output"].side_effect = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("Capture should not be called")
    )

    # Run sync WITHOUT --generate
    result = runner.invoke(zlt_cli, ["tools", "sync"], catch_exceptions=False)

    # Expect success (exit code 0) and completion message
    assert result.exit_code == 0
    assert "Sync process complete" in result.output
    assert "Tool index and definitions appear consistent" in result.output

    # Verify Podman was NOT started
    mocks["start_podman"].assert_not_called()
    mocks["stop_podman"].assert_not_called()
    # Verify index was NOT saved (no changes needed)
    mocks["save_index"].assert_not_called()


def test_sync_step10_iteration(mock_sync_env):
    """Test Step 10 Iteration: Run sync after Step 9 added a sequence, expect re-run message."""
    # This is identical to the Step 9 test setup and expected outcome
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Ensure toolA.txt and toolA.json exist AND are consistent
    toolA_json_path = tools_dir / "toolA" / "toolA.json"
    toolA_crc = DEFAULT_TOOL_INDEX["toolA"]["crc"]
    toolA_json_content = {
        "metadata": {"ground_truth_crc": toolA_crc},  # Consistent CRC
        "command": ["toolA"],
        "subcommands_detail": {"new_sub": {"description": "A newly discovered subcommand"}},
    }
    toolA_json_path.write_text(json.dumps(toolA_json_content, indent=4))
    assert (tools_dir / "toolA" / "toolA.txt").exists()  # Precondition

    # Add new_sub to whitelist so it gets picked up
    mocks["config_loader"].return_value["managed-tools"]["whitelist"].append("toolA:new_sub")
    wl_tree = parse_to_nested_dict(mocks["config_loader"].return_value["managed-tools"]["whitelist"])
    bl_tree = parse_to_nested_dict(mocks["config_loader"].return_value["managed-tools"]["blacklist"])
    mocks["parse_hierarchical"].side_effect = [wl_tree, bl_tree]
    mocks["get_status"].side_effect = lambda seq, *args: get_effective_status(seq, wl_tree, bl_tree)

    # Define a helper function to raise the assertion
    def _raise_capture_error(*args, **kwargs):
        raise AssertionError("Capture should not be called")

    mocks["capture_output"].side_effect = _raise_capture_error

    result = runner.invoke(zlt_cli, ["tools", "sync"], catch_exceptions=False)

    # Expect success (exit code 0) but message indicates new sequences added
    assert result.exit_code == 0
    assert "New subcommand sequences were added to the index" in result.output
    assert "Please re-run `zlt tools sync --generate`" in result.output
    # Verify index WAS saved with the new entry
    mocks["save_index"].assert_called_once()


def test_sync_dry_run(mock_sync_env):
    """Test --dry-run prevents actual changes."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]
    toolA_txt_path = tools_dir / "toolA" / "toolA.txt"
    original_toolA_txt = toolA_txt_path.read_text()

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Simulate podman returning NEW help text for toolA
    new_toolA_help = b"toolA help v2 dry run"
    mocks["capture_output"].side_effect = (
        lambda cmd_seq, *args, **kwargs: (new_toolA_help, b"", 0)
        if tuple(cmd_seq[-1:]) == ("toolA",)
        else (b"Default", b"", 0)
    )

    # Run sync with --generate and --dry-run
    with patch("time.time", return_value=3000.0):
        result = runner.invoke(zlt_cli, ["tools", "sync", "--generate", "--dry-run"], catch_exceptions=False)

    # Should complete successfully, indicating what *would* happen
    assert result.exit_code == 0
    assert "[Dry Run]" in result.output
    assert "Would update baseline file" in result.output
    assert "toolA.txt" in result.output
    assert "Would update index entry for toolA" in result.output
    assert "Sync process complete" in result.output  # Or similar dry-run completion message

    # Verify Podman was started/stopped (setup still happens)
    mocks["start_podman"].assert_called_once()
    mocks["stop_podman"].assert_called_once()
    # Verify capture WAS called
    assert mocks["capture_output"].called

    # Verify NO files were changed
    assert toolA_txt_path.read_text() == original_toolA_txt
    # Verify index was NOT saved
    mocks["save_index"].assert_not_called()

    # Verify no subcommands discovered / reported as added in dry run (unless implemented)
    assert "New subcommand sequences were added" not in result.output


@patch("shutil.rmtree")
def test_sync_prune(mock_rmtree, mock_sync_env):
    """Test --prune removes orphan directories."""
    runner = mock_sync_env["runner"]
    mocks = mock_sync_env["mocks"]
    tools_dir = mock_sync_env["tools_dir"]

    # Remove the unclassified tool from venv/bin to pass Step 3
    (mock_sync_env["venv_bin"] / "toolD").unlink()

    # Create an orphan directory in tools/
    orphan_dir_name = "toolX"
    orphan_dir_path = tools_dir / orphan_dir_name
    orphan_dir_path.mkdir()
    assert orphan_dir_path.is_dir()  # Precondition

    # Configure mock capture output (consistent data, shouldn't matter for prune)
    mocks["capture_output"].side_effect = lambda *args, **kwargs: (b"Default", b"", 0)

    # Run sync with --prune
    result = runner.invoke(zlt_cli, ["tools", "sync", "--prune"], catch_exceptions=False)

    # Should complete successfully after pruning
    assert result.exit_code == 0
    assert "Pruning orphan tool directory: toolX" in result.output
    assert "Sync process complete" in result.output

    # Verify rmtree was called on the orphan directory
    mock_rmtree.assert_called_once_with(orphan_dir_path)

    # Verify Podman was NOT started (prune happens before baseline generation)
    mocks["start_podman"].assert_not_called()
    mocks["stop_podman"].assert_not_called()
    # Verify index was NOT saved (pruning doesn't modify index)
    mocks["save_index"].assert_not_called()
