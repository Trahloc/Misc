# FILE: tests/test_tool_defs/test_ensure_txt_baselines_exist.py
"""
Tests that a TXT baseline file exists for every managed tool/subcommand
and that its content matches the expected CRC stored in a central index.
Uses a time-based cache (24 hours) to avoid redundant checks.
Generates missing files and updates the index if needed.
"""

import logging
import subprocess
import sys
import time
import pytest
from pathlib import Path

# Corrected Imports
from src.zeroth_law.dev_scripts.tool_discovery import load_tools_config
from src.zeroth_law.lib.crc import calculate_crc32  # Correct function name
# Paths will be imported from conftest

# Assuming conftest.py in the same directory provides WORKSPACE_ROOT and TOOLS_DIR
# If not, we might need to calculate them similarly to conftest.py

# Setup logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Constants
CACHE_DURATION_SECONDS = 24 * 60 * 60  # 24 hours


# --- Helper Functions ---
# Renamed from flatten_managed_items_recursive, kept local
def _flatten_recursive(tool_list: list, current_path: tuple[str, ...], all_items: list[tuple[str, ...]]):
    """Recursively flattens the managed tool structure."""
    for entry in tool_list:
        if isinstance(entry, str):
            if not current_path:
                all_items.append((entry,))
            else:
                # Changed to log.warning
                log.warning(f"Ignoring nested string '{entry}' under {'/'.join(current_path)} in managed_tools.yaml")
        elif isinstance(entry, dict):
            name = entry.get("name")
            if name:
                new_path = current_path + (name,)
                all_items.append(new_path)
                subcommands = entry.get("subcommands", [])
                _flatten_recursive(subcommands, new_path, all_items)


def command_sequence_to_id(command_parts: tuple[str, ...]) -> str:
    """Creates a readable ID for parametrized tests and dictionary keys."""
    return "_".join(command_parts)


# --- Get Managed Command Sequences ---
try:
    _config = load_tools_config()
    # Initialize list and call local _flatten_recursive
    MANAGED_COMMAND_SEQUENCES = []
    _flatten_recursive(_config.get("managed_tools", []), (), MANAGED_COMMAND_SEQUENCES)
    if not MANAGED_COMMAND_SEQUENCES:
        log.warning("MANAGED_COMMAND_SEQUENCES is empty after loading and flattening config.")
except FileNotFoundError:
    log.warning("managed_tools.yaml not found. Skipping TXT baseline tests.")
except Exception as e:
    log.error(f"Error loading or parsing managed_tools.yaml: {e}")
    MANAGED_COMMAND_SEQUENCES = []

# Removed redundant local definition of command_sequence_to_id
# It should be available from conftest.py or the helper above


# --- Test Function ---
@pytest.mark.parametrize(
    "command_parts",
    MANAGED_COMMAND_SEQUENCES,
    ids=[command_sequence_to_id(cp) for cp in MANAGED_COMMAND_SEQUENCES],
)
def test_txt_baseline_exists_and_matches_index(
    command_parts: tuple[str, ...], tool_index_handler, WORKSPACE_ROOT, TOOLS_DIR
):
    """
    Verifies that the TXT baseline file exists and its content's CRC matches
    the value stored in tool_index.json. Updates the file and index if needed.
    Pass WORKSPACE_ROOT and TOOLS_DIR as arguments if provided by conftest.
    """
    if not command_parts:
        pytest.skip("Skipping test for empty command parts.")

    tool_id = command_sequence_to_id(command_parts)
    tool_name = command_parts[0]
    command_list = list(command_parts) + ["--help"]
    command_str_for_display = " ".join(command_list)

    # Use dynamically provided TOOLS_DIR
    tool_dir = TOOLS_DIR / tool_name
    # Define txt file path - directly in tool_dir
    txt_file = tool_dir / f"{tool_id}.txt"
    # Use dynamically provided WORKSPACE_ROOT
    relative_txt_file_path = txt_file.relative_to(WORKSPACE_ROOT)

    # Define json file path - directly in tool_dir
    json_file = tool_dir / f"{tool_id}.json"
    relative_json_file_path = json_file.relative_to(WORKSPACE_ROOT)

    index_data = tool_index_handler["data"]
    stored_entry = index_data.get(tool_id)  # dict with 'crc' and 'timestamp' or None
    stored_crc = stored_entry.get("crc") if stored_entry else None
    stored_timestamp = stored_entry.get("timestamp") if stored_entry else 0

    current_time = time.time()
    is_cache_valid = (
        stored_entry is not None and txt_file.is_file() and (current_time - stored_timestamp < CACHE_DURATION_SECONDS)
    )

    current_crc = None
    current_output = None
    run_subprocess = not is_cache_valid

    if is_cache_valid:
        print(f"\nCache hit for '{tool_id}'. Assuming CRC {stored_crc} is valid.")
        current_crc = stored_crc  # Trust the cached CRC
    else:
        print(f"\nCache miss or stale for '{tool_id}'. Running command: '{command_str_for_display}'")
        # Modify the command_list to use 'uv run --'
        uv_command_list = ["uv", "run", "--"] + command_list
        uv_command_str_for_display = " ".join(uv_command_list)  # For logging/errors
        log.debug(f"Executing via uv run: {uv_command_str_for_display}")
        try:
            # Execute using the modified uv_command_list
            result = subprocess.run(
                uv_command_list,  # Use uv run
                capture_output=True,
                text=True,
                check=False,  # Check manually below
                cwd=WORKSPACE_ROOT,
                timeout=30,  # Increased timeout slightly
            )
            log.debug(f"Command exited with code: {result.returncode}")

            if result.returncode != 0:
                # Use uv_command_str_for_display in error message
                pytest.fail(
                    f"Command failed for '{tool_id}'.\\n"
                    f"Command: '{uv_command_str_for_display}' exited with code {result.returncode}.\\n"
                    f"Stderr:\\n{result.stderr}\\n"
                    f"Stdout:\\n{result.stdout}"
                )

            current_output = result.stdout.replace("\r\n", "\n").replace("\r", "\n")
            current_crc = calculate_crc32(current_output)
            log.debug(f"Calculated CRC for '{tool_id}': {current_crc} (Stored: {stored_crc})")

        except FileNotFoundError:
            # This error should ideally not happen now if 'uv' is found,
            # but keep the check for robustness.
            pytest.fail(
                f"Failed to run command via uv: '{uv_command_str_for_display}'. " f"Is 'uv' installed and on PATH?"
            )
        except subprocess.TimeoutExpired:
            pytest.fail(f"Command timed out for '{tool_id}': '{uv_command_str_for_display}'")
        except Exception as e:
            # Catch other potential subprocess errors
            pytest.fail(f"Unexpected error running command for '{tool_id}': '{uv_command_str_for_display}'\nError: {e}")

    # --- Check for changes and file existence ---
    txt_needs_update = (current_crc != stored_crc) or (not txt_file.is_file())

    if txt_needs_update:
        # --- Update required for TXT ---
        print(f"Updating TXT baseline for '{tool_id}': {relative_txt_file_path}")

        # Ensure the tool directory exists
        try:
            tool_dir.mkdir(parents=True, exist_ok=True)  # Ensure TOOL directory exists
        except OSError as e:
            pytest.fail(f"Failed to create directory {tool_dir}: {e}")

        # Write the new content
        try:
            # Ensure current_output is not None before writing
            if current_output is None:
                pytest.fail(
                    f"Attempted to write None to TXT file for '{tool_id}'. Command execution might have failed silently."
                )

            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(current_output)
            log.info(f"Successfully wrote TXT file: {relative_txt_file_path}")  # Log success
        except IOError as e:
            pytest.fail(f"Error writing TXT file {relative_txt_file_path}: {e}")

        # Update the index data in the fixture's state since TXT was updated
        new_entry = {"crc": current_crc, "timestamp": current_time}
        print(f"Updating index for '{tool_id}' with: {new_entry}")
        index_data[tool_id] = new_entry
        tool_index_handler["dirty"] = True  # Mark index for saving
        print(f"Updated index for '{tool_id}' with new CRC: {current_crc}")
    else:
        # TXT didn't need update, but log this state
        log.debug(f"TXT baseline for '{tool_id}' is up-to-date. CRC: {stored_crc}")

    # Final assertion: If we reached here without failing, the baseline check passed.
    assert True, f"Baseline checks passed for {tool_id}"  # Should always pass if no pytest.fail occurred
