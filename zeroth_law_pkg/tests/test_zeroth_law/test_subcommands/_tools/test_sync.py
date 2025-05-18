"""Tests for the `zlt tools sync` command."""

import pytest
import sys
import json
import zlib
from pathlib import Path
from unittest.mock import patch, MagicMock, call, PropertyMock
import shutil
import time
import os
import logging
import subprocess

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

# Import the main CLI entry point and the specific sync command/logic
# from zeroth_law.cli import main as zlt_cli # Not used directly
# from zeroth_law.subcommands.tools.sync import sync as sync_command # OLD PATH
from zeroth_law.subcommands._tools.sync import sync as sync_command  # NEW PATH

# Import helpers and exceptions potentially needed for mocking/setup
# from zeroth_law.lib.tooling.tool_reconciler import ToolStatus, ReconciliationError # OLD PATH
from zeroth_law.lib.tooling.tool_reconciler import ToolStatus  # Keep this
from zeroth_law.subcommands._tools._reconcile._logic import (
    ReconciliationError,
)  # NEW PATH for exception
from zeroth_law.lib.tool_index_handler import ToolIndexHandler

# Import calculate_crc32_hex helper
from zeroth_law.lib.tool_path_utils import calculate_crc32_hex

# Default config structure for pyproject.toml
DEFAULT_PYPROJECT_CONTENT = """
[tool.zerothlaw]
project_name = "zeroth_law"

[tool.zerothlaw.managed-tools]
whitelist = [
    "toolA",
    "toolB:sub1",
]
blacklist = [
    "toolC",
    "python", # Essential for python script testing, MUST BE BLACKLISTED here
]

# Add setuptools config to find package in src/
[tool.setuptools]
package-dir = {"" = "src"}

[tool.zeroth-law]
[tool.zeroth-law.managed-tools]
"""

# Default tool index content
DEFAULT_TOOL_INDEX = {
    "toolA": {
        "crc": hex(zlib.crc32(b"toolA help")),
        "checked_timestamp": 1.0,
        "updated_timestamp": 1.0,
    },
    "toolB": {
        "crc": None,
        "checked_timestamp": 1.0,
        "updated_timestamp": 1.0,
        "subcommands": {
            "sub1": {
                "crc": hex(zlib.crc32(b"toolB sub1 help")),
                "checked_timestamp": 1.0,
                "updated_timestamp": 1.0,
            }
        },
    },
}

# Configure logging for debugging tests
logger = logging.getLogger(__name__)

# --- Test Fixtures (if needed specifically for sync tests) --- #


# Example fixture to set up a temporary tools structure
@pytest.fixture
def temp_tools_structure(tmp_path):
    # Create dummy src and tests dirs for project root detection
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    # Create minimal pyproject.toml for root detection
    pyproject_content = """
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "zeroth-law"
version = "0.1.0a0"
description = "Test project"
requires-python = ">=3.13"
# Add dummy scripts section for testing tool installation
[project.scripts]
managed_tool_a = "zeroth_law.dummy:main_a"
managed_tool_b = "zeroth_law.dummy:main_b"

[tool.zeroth-law]
[tool.zeroth-law.managed-tools]
whitelist = ["managed_tool_a", "managed_tool_b"]
# Fix: Correct indentation for the blacklist entry
blacklist = [
    "python",
]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    tools_root = tmp_path / "src" / "zeroth_law" / "tools"
    tools_root.mkdir(parents=True)
    (tools_root / "managed_tool_a").mkdir()
    (tools_root / "managed_tool_a" / "managed_tool_a.json").write_text("{}")
    (tools_root / "managed_tool_b").mkdir()
    (tools_root / "managed_tool_b" / "managed_tool_b.json").write_text("{}")
    (tools_root / "unmanaged_tool_c").mkdir()  # Orphan dir
    (tools_root / "unmanaged_tool_c" / "unmanaged_tool_c.json").write_text("{}")
    # Create dummy venv bin
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    # --- Create dummy EXECUTABLE python script --- #
    # python_dummy_path = venv_bin / "python"
    # python_dummy_path.write_text("#!/bin/sh\\nexit 0")  # Minimal valid executable script
    # os.chmod(python_dummy_path, 0o755)
    # # --- END --- #
    #
    # # --- Install 'build' package into the temp venv --- #
    # try:
    #     # Install build, setuptools, and wheel explicitly
    #     subprocess.run([str(python_dummy_path), "-m", "pip", "install", "build", "setuptools", "wheel"], check=True, capture_output=True)
    #     logger.debug(f"Successfully installed build tools into {venv_bin}")
    # except subprocess.CalledProcessError as e:
    #     logger.error(f"Failed to install build tools into temp venv {venv_bin}: {e}\\n{e.stderr.decode()}")
    #     pytest.fail(f"Failed to install build tools into temp venv: {e}")
    # # --- END Install --- #

    (venv_bin / "managed_tool_a").touch()  # Keep other dummies as simple files for now
    os.chmod(venv_bin / "managed_tool_a", 0o755)
    (venv_bin / "unmanaged_tool_env").touch()
    os.chmod(venv_bin / "unmanaged_tool_env", 0o755)

    # Create dummy requirements-dev.txt
    (tmp_path / "requirements-dev.txt").touch()

    return tmp_path


# --- Sync Command Tests --- #


def test_sync_fails_on_unclassified_tool(temp_tools_structure):
    """Test that sync fails if reconcile finds unclassified env tools."""
    runner = CliRunner()
    # Need to invoke via the main CLI group structure now
    from zeroth_law.cli import cli_group

    original_cwd = os.getcwd()
    os.chdir(str(temp_tools_structure))
    # Remove the orphan dir to isolate the orphan env tool error
    shutil.rmtree(
        temp_tools_structure / "src" / "zeroth_law" / "tools" / "unmanaged_tool_c",
        ignore_errors=True,
    )
    try:
        result = runner.invoke(cli_group, ["tools", "--max-workers=1", "sync"], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)
    assert result.exit_code != 0, "Sync should fail with non-zero exit code for orphan env tool"


def test_sync_fails_on_orphan_tool_dir(temp_tools_structure):
    """Test that sync fails if reconcile finds orphan tool definition dirs."""
    runner = CliRunner()
    from zeroth_law.cli import cli_group

    # Remove the env tool that causes the other error
    os.remove(temp_tools_structure / ".venv" / "bin" / "unmanaged_tool_env")
    original_cwd = os.getcwd()
    os.chdir(str(temp_tools_structure))
    try:
        result = runner.invoke(cli_group, ["tools", "--max-workers=1", "sync"], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)
    assert result.exit_code != 0, "Sync should fail with non-zero exit code for orphan tool dir"


@patch("zeroth_law.subcommands._tools._sync._stop_podman_runner")
@patch(
    "zeroth_law.subcommands._tools._sync._start_podman_runner",
    return_value="mock-container-name",
)
def test_sync_success_no_changes(mock_stop_podman, mock_start_podman, temp_tools_structure, caplog):
    """Test successful sync run with no required baseline changes."""
    caplog.set_level(logging.INFO)
    runner = CliRunner()
    from zeroth_law.cli import cli_group

    # Clean up environment and definition issues from previous tests
    os.remove(temp_tools_structure / ".venv" / "bin" / "unmanaged_tool_env")
    shutil.rmtree(temp_tools_structure / "src" / "zeroth_law" / "tools" / "unmanaged_tool_c")
    # Add missing tool B to env
    (temp_tools_structure / ".venv" / "bin" / "managed_tool_b").touch()
    os.chmod(temp_tools_structure / ".venv" / "bin" / "managed_tool_b", 0o755)
    # Create dummy baseline files that are up-to-date
    tool_a_dir = temp_tools_structure / "src" / "zeroth_law" / "tools" / "managed_tool_a"
    tool_b_dir = temp_tools_structure / "src" / "zeroth_law" / "tools" / "managed_tool_b"
    (tool_a_dir / "managed_tool_a.txt").write_text("baseline A")
    (tool_b_dir / "managed_tool_b.txt").write_text("baseline B")
    # Ensure JSON mtime is older than TXT mtime (or use force/checksum logic if implemented)
    time.sleep(0.1)  # Ensure txt is newer

    tool_a_json_path = tool_a_dir / "managed_tool_a.json"
    tool_b_json_path = tool_b_dir / "managed_tool_b.json"

    # Prepare index entries
    entry_a = {
        "command": ["managed_tool_a"],
        "json_definition_file": str(
            tool_a_json_path.relative_to(temp_tools_structure / "src" / "zeroth_law" / "tools")
        ),
        "baseline_file": str(
            (tool_a_dir / "managed_tool_a.txt").relative_to(temp_tools_structure / "src" / "zeroth_law" / "tools")
        ),  # Assuming baseline relative to tools dir
        "crc": calculate_crc32_hex(tool_a_json_path.read_bytes()) if tool_a_json_path.exists() else None,
        "updated_timestamp": time.time(),
        "checked_timestamp": time.time() - 10,  # Ensure checked is older than updated
    }
    entry_b = {
        "command": ["managed_tool_b"],
        "json_definition_file": str(
            tool_b_json_path.relative_to(temp_tools_structure / "src" / "zeroth_law" / "tools")
        ),
        "baseline_file": str(
            (tool_b_dir / "managed_tool_b.txt").relative_to(temp_tools_structure / "src" / "zeroth_law" / "tools")
        ),  # Assuming baseline relative to tools dir
        "crc": calculate_crc32_hex(tool_b_json_path.read_bytes()) if tool_b_json_path.exists() else None,
        "updated_timestamp": time.time(),
        "checked_timestamp": time.time() - 10,
    }

    index_path = temp_tools_structure / "src" / "zeroth_law" / "tools" / "tool_index.json"
    handler = ToolIndexHandler(index_path)
    # Pass the constructed dictionary and command sequence tuple
    handler.update_entry(("managed_tool_a",), entry_a)
    handler.update_entry(("managed_tool_b",), entry_b)
    handler.save_index()

    original_cwd = os.getcwd()
    os.chdir(str(temp_tools_structure))
    try:
        result = runner.invoke(cli_group, ["tools", "--max-workers=1", "sync"], catch_exceptions=False)
    finally:
        os.chdir(original_cwd)
    assert result.exit_code == 0

    # Assert based on captured logs
    # assert "Sync summary" in caplog.text
    # summary_record = next((r for r in caplog.records if r.message == "Sync summary"), None)
    # assert summary_record is not None
    # assert summary_record.processed == 0
    # assert summary_record.skipped == 2
    # assert summary_record.levelname == "INFO"


@pytest.mark.parametrize(
    "scenario",
    ["skip_default", "process_default", "force", "skip_custom", "process_custom"],
)
# Add patch decorators for podman helpers
@patch("zeroth_law.subcommands._tools._sync._stop_podman_runner")
@patch(
    "zeroth_law.subcommands._tools._sync._start_podman_runner",
    return_value="mock-container-name",
)
# --- STRATEGY: Patching save_tool_index AND _capture_command_output --- #
# --- Patch save_tool_index where it's imported/used --- #
@patch("zeroth_law.subcommands._tools._sync._update_and_save_index.save_tool_index")
# --- Patch update_index_entry where it's imported/used --- #
@patch("zeroth_law.subcommands._tools._sync._update_and_save_index.update_index_entry")
@patch("zeroth_law.lib.tooling.baseline_generator._capture_command_output")
def test_sync_timestamp_logic(
    mock_capture,
    mock_update_entry,
    mock_save_index,
    mock_start_podman,
    mock_stop_podman,
    temp_tools_structure,
    scenario,
    caplog,
):
    """Test the sync command timestamp logic with different scenarios."""
    # Test setup: Remove ToolIndexHandler usage
    runner = CliRunner()
    from zeroth_law.cli import cli_group

    caplog.set_level(logging.INFO)
    # Basic setup (remove conflicts)
    venv_bin = temp_tools_structure / ".venv" / "bin"
    tools_src = temp_tools_structure / "src" / "zeroth_law" / "tools"
    if (venv_bin / "unmanaged_tool_env").exists():
        os.remove(venv_bin / "unmanaged_tool_env")
    if (tools_src / "unmanaged_tool_c").exists():
        shutil.rmtree(tools_src / "unmanaged_tool_c")
    # Make dummy tools executable (still good practice)
    (temp_tools_structure / ".venv" / "bin" / "managed_tool_a").touch()
    os.chmod(temp_tools_structure / ".venv" / "bin" / "managed_tool_a", 0o755)
    (temp_tools_structure / ".venv" / "bin" / "managed_tool_b").touch()
    os.chmod(temp_tools_structure / ".venv" / "bin" / "managed_tool_b", 0o755)

    tool_a_dir = temp_tools_structure / "src" / "zeroth_law" / "tools" / "managed_tool_a"
    json_file = tool_a_dir / "managed_tool_a.json"
    txt_file = tool_a_dir / "managed_tool_a.txt"

    # --- Set file modification times based on scenario --- #
    json_file.touch()
    time.sleep(0.1)
    if "skip" in scenario:
        txt_file.write_text("existing baseline")
        # Pre-create index for skip scenario to ensure it gets loaded
        index_path = temp_tools_structure / "src" / "zeroth_law" / "tools" / "tool_index.json"
        initial_crc = calculate_crc32_hex(json_file.read_bytes())
        pre_index_data = {
            "managed_tool_a": {
                "crc": initial_crc,
                "checked_timestamp": time.time(),  # Recent check
                "updated_timestamp": json_file.stat().st_mtime,
                "baseline_file": str(txt_file.relative_to(tools_src)),
                "json_definition_file": str(json_file.relative_to(tools_src)),
            }
        }
        with open(index_path, "w") as f:
            json.dump(pre_index_data, f, indent=2)

    elif "process" in scenario:
        txt_file.touch()
        time.sleep(0.1)
        json_file.touch()
    elif "force" in scenario:
        txt_file.write_text("existing baseline")

    # --- Conditionally modify config for custom scenarios --- #
    if "custom" in scenario:
        config_path = temp_tools_structure / "pyproject.toml"
        config_content = config_path.read_text()
        config_content = config_content.replace(
            "#[tool.zeroth-law]", "[tool.zeroth-law]\nground_truth_txt_skip_since = 1"
        )
        config_path.write_text(config_content)

    # Index should NOT exist initially for process/force scenarios
    index_path = temp_tools_structure / "src" / "zeroth_law" / "tools" / "tool_index.json"
    if index_path.exists() and "skip" not in scenario:
        os.remove(index_path)

    # --- Configure the capture mock --- #
    mocked_output_content = b"new output"
    fixed_crc = calculate_crc32_hex(mocked_output_content)
    fixed_timestamp = time.time()
    # Calculate initial CRC only if needed for skip scenario assertion
    initial_crc = calculate_crc32_hex(json_file.read_bytes()) if "skip" in scenario and json_file.exists() else None

    def capture_side_effect(*args, **kwargs):
        # args[0] is command_sequence
        if args[0] == ("managed_tool_a",):
            if "process" in scenario or "force" in scenario:
                return mocked_output_content, None, 0  # Success with new content
            else:  # skip scenario
                # Return old content if txt_file exists (it should in skip)
                return txt_file.read_bytes() if txt_file.exists() else b"", None, 0
        else:  # managed_tool_b or others
            return b"tool b output", None, 0  # Default success

    mock_capture.side_effect = capture_side_effect

    # --- Run the sync command --- #
    cmd_args = ["tools", "sync", "--generate"]
    if "force" in scenario:
        cmd_args.append("--force")

    # --- Reset mock before invoke --- #
    mock_save_index.reset_mock()

    original_cwd = os.getcwd()
    os.chdir(str(temp_tools_structure))
    try:
        result = runner.invoke(cli_group, cmd_args, catch_exceptions=False)
    finally:
        os.chdir(original_cwd)

    # Assertions: Check exit code and data passed to save_tool_index
    if result.exception:
        import traceback

        print("\n--- Test Invocation Exception --- ")
        print(f"Exception Type: {type(result.exception).__name__}")
        print(f"Exception Value: {result.exception}")
        traceback.print_exception(*result.exc_info)
        print("--- End Exception Info ---")

    assert result.exit_code == 0, f"Scenario '{scenario}' failed with exit code {result.exit_code}"

    # Check that save_tool_index was called
    mock_save_index.assert_called_once()

    # Get the data that was passed to save_tool_index
    call_args, call_kwargs = mock_save_index.call_args
    saved_index_data = call_args[0]  # First positional arg is the index_data dict

    # Perform assertions on the captured index_data
    saved_entry_a = saved_index_data.get("managed_tool_a")

    # --- Restore scenario-dependent assertions --- #
    if "skip" in scenario:
        assert saved_entry_a is not None, f"Index entry missing in skip scenario '{scenario}'"
        assert saved_entry_a["crc"] == initial_crc, f"Index CRC changed in skip scenario '{scenario}'"
        assert (
            txt_file.read_text() == "existing baseline"
        ), f"Baseline file content changed in skip scenario '{scenario}'"
    elif "process" in scenario or "force" in scenario:
        assert (
            saved_entry_a is not None
        ), f"managed_tool_a missing from saved index in process/force scenario '{scenario}'"
        # Assert against the CRC calculated from the mocked output
        assert saved_entry_a["crc"] == fixed_crc, f"Index CRC not updated in process/force scenario '{scenario}'"
        assert "checked_timestamp" in saved_entry_a, "checked_timestamp missing"
        assert abs(saved_entry_a["checked_timestamp"] - fixed_timestamp) < 30, "checked_timestamp not updated recently"
        assert "updated_timestamp" in saved_entry_a, "updated_timestamp missing"
        assert "baseline_file" in saved_entry_a, "baseline_file missing"
        assert "json_definition_file" in saved_entry_a, "json_definition_file missing"


# Test --exit-errors flag
@patch("zeroth_law.subcommands._tools._sync._stop_podman_runner")
@patch(
    "zeroth_law.subcommands._tools._sync._start_podman_runner",
    return_value="mock-container-name",
)
def test_sync_exit_errors(mock_stop_podman, mock_start_podman, temp_tools_structure, caplog):
    runner = CliRunner()
    from zeroth_law.cli import cli_group

    caplog.set_level(logging.INFO)
    # Setup scenario where baseline generation fails for one tool
    # Clean up initial conflicts
    os.remove(temp_tools_structure / ".venv" / "bin" / "unmanaged_tool_env")
    shutil.rmtree(temp_tools_structure / "src" / "zeroth_law" / "tools" / "unmanaged_tool_c")
    (temp_tools_structure / ".venv" / "bin" / "managed_tool_b").touch()
    os.chmod(temp_tools_structure / ".venv" / "bin" / "managed_tool_b", 0o755)
    # Tool A needs update, Tool B is fine
    tool_a_dir = temp_tools_structure / "src" / "zeroth_law" / "tools" / "managed_tool_a"
    tool_b_dir = temp_tools_structure / "src" / "zeroth_law" / "tools" / "managed_tool_b"
    (tool_b_dir / "managed_tool_b.txt").write_text("baseline B")
    time.sleep(0.1)

    tool_a_json_path = tool_a_dir / "managed_tool_a.json"
    tool_b_json_path = tool_b_dir / "managed_tool_b.json"

    # Prepare index entries
    entry_a = {
        "command": ["managed_tool_a"],
        "json_definition_file": str(
            tool_a_json_path.relative_to(temp_tools_structure / "src" / "zeroth_law" / "tools")
        ),
        "baseline_file": None,  # Needs update
        "crc": calculate_crc32_hex(tool_a_json_path.read_bytes()) if tool_a_json_path.exists() else None,
        "updated_timestamp": time.time(),
        "checked_timestamp": 0.0,
    }
    entry_b = {
        "command": ["managed_tool_b"],
        "json_definition_file": str(
            tool_b_json_path.relative_to(temp_tools_structure / "src" / "zeroth_law" / "tools")
        ),
        "baseline_file": str(
            (tool_b_dir / "managed_tool_b.txt").relative_to(temp_tools_structure / "src" / "zeroth_law" / "tools")
        ),  # Up-to-date
        "crc": calculate_crc32_hex(tool_b_json_path.read_bytes()) if tool_b_json_path.exists() else None,
        "updated_timestamp": time.time() - 10,  # Older update time
        "checked_timestamp": time.time(),  # Newer check time
    }

    index_path = temp_tools_structure / "src" / "zeroth_law" / "tools" / "tool_index.json"
    handler = ToolIndexHandler(index_path)
    # Pass the constructed dictionary and command sequence tuple
    handler.update_entry(("managed_tool_a",), entry_a)
    handler.update_entry(("managed_tool_b",), entry_b)
    handler.save_index()

    # Mock capture to simulate failure for tool A
    def mock_capture_fail_a(*args, **kwargs):
        # Rough check if it's tool A being called
        if "managed_tool_a" in args[0]:  # Check command list
            return ("error output", 1)
        return ("tool b output", 0)

    original_cwd = os.getcwd()
    os.chdir(str(temp_tools_structure))
    try:
        # Patch ONLY the parallel runner to force sequential
        with patch("zeroth_law.subcommands._tools._sync._run_parallel_baseline_processing") as mock_parallel_runner:
            # Define side effect
            def sequential_runner_side_effect(*args, **kwargs):
                # Extract args needed by the sequential loop logic within the original function
                tasks_to_run = kwargs.get("tasks_to_run")
                tool_defs_dir = kwargs.get("tool_defs_dir")
                project_root = kwargs.get("project_root")
                container_name = kwargs.get("container_name")
                index_data = kwargs.get("index_data")
                force = kwargs.get("force")
                since_timestamp = kwargs.get("since_timestamp")
                ground_truth_txt_skip_hours = kwargs.get("ground_truth_txt_skip_hours")
                exit_errors_limit = kwargs.get("exit_errors_limit")

                # Mimic the sequential loop from _run_parallel_baseline_processing
                results = []
                sync_errors = []
                processed_count = 0
                error_count = 0
                for sequence in tasks_to_run:
                    command_id = command_sequence_to_id(sequence)
                    try:
                        result = _process_command_sequence(
                            sequence,
                            tool_defs_dir,
                            project_root,
                            container_name,
                            index_data,
                            force,
                            since_timestamp,
                            ground_truth_txt_skip_hours,
                        )
                        results.append(result)
                        processed_count += 1
                        is_error_status = result.get("error_message") or (
                            isinstance(result.get("status"), BaselineStatus)
                            and result["status"]
                            not in {
                                BaselineStatus.UP_TO_DATE,
                                BaselineStatus.UPDATED,
                                BaselineStatus.CAPTURE_SUCCESS,
                            }
                        )
                        if is_error_status:
                            error_count += 1
                            if exit_errors_limit is not None and error_count >= exit_errors_limit:
                                err_msg = f"Reached error limit ({exit_errors_limit}) processing {command_id}."
                                sync_errors.append(err_msg)
                                raise RuntimeError(err_msg)
                    except Exception as exc:
                        if isinstance(exc, RuntimeError) and f"Reached error limit" in str(exc):
                            raise exc
                        else:
                            err_msg = f"Task for {command_id} gen err: {exc}"
                            sync_errors.append(err_msg)
                            processed_count += 1
                            error_count += 1
                            if exit_errors_limit is not None and error_count >= exit_errors_limit:
                                err_msg_limit = f"Reached error limit ({exit_errors_limit}) due to exc in {command_id}."
                                sync_errors.append(err_msg_limit)
                                raise RuntimeError(err_msg_limit)
                    return results, sync_errors, processed_count

            mock_parallel_runner.side_effect = sequential_runner_side_effect

            # Use default catch_exceptions=True and check result.exit_code
            result_with_exit = runner.invoke(
                cli_group,
                ["tools", "--max-workers=1", "sync", "--exit-errors"],
                catch_exceptions=True,
            )

    finally:
        os.chdir(original_cwd)

    # Check exit code directly
    assert result_with_exit.exit_code != 0


# TODO: Add tests for --tools flag
# TODO: Add tests for container execution (requires more complex mocking or actual podman)
# TODO: Add tests for hostility audit integration
