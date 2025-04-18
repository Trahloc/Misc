# FILE: tests/test_tool_defs/test_ensure_txt_baselines_exist.py
"""
Tests that a TXT baseline file exists for every managed tool/subcommand
and that its content matches the expected CRC stored in a central index.
Uses a time-based cache (24 hours) to avoid redundant checks.
Generates missing files and updates the index if needed.
"""

import json
import logging
import subprocess
import sys
import time
import zlib  # For CRC32 calculation
import pytest

# Assuming tool_discovery.py is importable via src layout or installation
from zeroth_law.dev_scripts.tool_discovery import (
    TOOLS_DIR,
    WORKSPACE_ROOT,
    load_tools_config,
)

# Import skeleton generator and necessary file utils
# from zeroth_law.dev_scripts.generate_baseline_files import (
#     generate_json_skeleton,
#     DEFAULT_ENCODING
# )
# from zeroth_law.dev_scripts.generate_baseline_files import DEFAULT_ENCODING
# Import from one of the new utility modules

# Import the utility function

# --- Constants ---
TOOL_INDEX_PATH = TOOLS_DIR / "tool_index.json"
CACHE_DURATION_SECONDS = 24 * 60 * 60  # 24 hours
# JSON_DIR_NAME = "json"  # Define standard subdirectory name for JSON files -- REMOVED
# Define standard subdirectory name for TXT files (can be empty if stored directly in tool dir)
TXT_SUBDIR_NAME = ""

# Add basic logging for subprocess calls within tests
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


# --- Helper functions ---
def _flatten_recursive(tool_list: list, current_path: tuple[str, ...], all_items: list[tuple[str, ...]]):
    """Recursively flattens the managed tool structure."""
    for entry in tool_list:
        if isinstance(entry, str):
            if not current_path:
                all_items.append((entry,))
            else:
                print(f"Warning: Ignoring nested string '{entry}' under {'/'.join(current_path)} in managed_tools.yaml", file=sys.stderr)
        elif isinstance(entry, dict):
            name = entry.get("name")
            if name:
                new_path = current_path + (name,)
                all_items.append(new_path)
                subcommands = entry.get("subcommands", [])
                _flatten_recursive(subcommands, new_path, all_items)


def flatten_managed_items_recursive(config: dict) -> list[tuple[str, ...]]:
    """Loads and flattens the list of managed tools/subcommands from the config."""
    all_items: list[tuple[str, ...]] = []
    managed_tools_config = config.get("managed_tools", [])
    _flatten_recursive(managed_tools_config, (), all_items)
    return [item for item in all_items if item]


def command_sequence_to_id(command_parts: tuple[str, ...]) -> str:
    """Creates a readable ID for parametrized tests and dictionary keys."""
    return "_".join(command_parts)


def calculate_crc(text_content: str) -> str:
    """Calculates the CRC32 checksum of text content and returns it as a hex string."""
    # Ensure consistent encoding for CRC calculation
    crc_val = zlib.crc32(text_content.encode("utf-8"))
    return hex(crc_val)  # Return as hex string (e.g., '0xabcdef12')


# --- Fixture for Index Handling ---
@pytest.fixture(scope="module")  # Load/save index once per module run
def tool_index_handler():
    """Fixture to load, manage, and save the tool index (with CRC and timestamp)."""

    index_data = {}
    try:
        if TOOL_INDEX_PATH.is_file():
            with open(TOOL_INDEX_PATH, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            print(f"\nLoaded tool index from: {TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}")
        else:
            print(f"\nTool index not found, initializing empty: {TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}")

    except json.JSONDecodeError:
        print(f"\nWarning: Failed to decode existing tool index at {TOOL_INDEX_PATH}. Starting fresh.", file=sys.stderr)
        # Optionally back up corrupted file here
        index_data = {}  # Start with an empty index
    except Exception as e:
        print(f"\nError loading tool index {TOOL_INDEX_PATH}: {e}", file=sys.stderr)
        pytest.fail(f"Could not load tool index: {e}")

    # Ensure loaded data conforms to expected structure (dict of dicts)
    # This prevents errors later if the file exists but has the old format
    valid_index_data = {}
    for key, value in index_data.items():
        if isinstance(value, dict) and "crc" in value and "timestamp" in value:
            valid_index_data[key] = value
        else:
            print(f"\nWarning: Invalid entry format for '{key}' in tool index. Discarding.", file=sys.stderr)

    handler_state = {"data": valid_index_data, "dirty": False}

    yield handler_state  # Pass the state to the tests

    # Teardown: Save if modified
    if handler_state["dirty"]:
        try:
            # Ensure parent directory exists (though TOOLS_DIR should exist)
            TOOL_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TOOL_INDEX_PATH, "w", encoding="utf-8") as f:
                # Use indentation for readability
                json.dump(handler_state["data"], f, indent=2, sort_keys=True)
            print(f"\nSaved updated tool index to: {TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}")
        except Exception as e:
            # Don't fail the test run here, but report the error
            print(f"\nError saving tool index {TOOL_INDEX_PATH}: {e}", file=sys.stderr)


# --- Get Managed Command Sequences ---
try:
    _config = load_tools_config()
    MANAGED_COMMAND_SEQUENCES = flatten_managed_items_recursive(_config)
except FileNotFoundError:
    print("Warning: managed_tools.yaml not found. Skipping TXT baseline tests.", file=sys.stderr)
    MANAGED_COMMAND_SEQUENCES = []
except Exception as e:
    print(f"Error loading or parsing managed_tools.yaml: {e}", file=sys.stderr)
    MANAGED_COMMAND_SEQUENCES = []


# --- Test Function ---
@pytest.mark.parametrize("command_parts", MANAGED_COMMAND_SEQUENCES, ids=command_sequence_to_id)
def test_txt_baseline_exists_and_matches_index(command_parts: tuple[str, ...], tool_index_handler):
    """
    Verifies that the TXT baseline file exists and its content's CRC matches
    the value stored in tool_index.json. Updates the file and index if needed.
    """
    if not command_parts:
        pytest.skip("Skipping test for empty command parts.")

    tool_id = command_sequence_to_id(command_parts)
    tool_name = command_parts[0]
    command_list = list(command_parts) + ["--help"]
    command_str_for_display = " ".join(command_list)

    tool_dir = TOOLS_DIR / tool_name
    # Define txt file path (potentially using TXT_SUBDIR_NAME)
    txt_base_dir = tool_dir / TXT_SUBDIR_NAME if TXT_SUBDIR_NAME else tool_dir
    txt_file = txt_base_dir / f"{tool_id}.txt"
    relative_txt_file_path = txt_file.relative_to(WORKSPACE_ROOT)

    # Define json file path - directly in tool_dir
    # json_dir = tool_dir / JSON_DIR_NAME # REMOVED
    json_file = tool_dir / f"{tool_id}.json"
    relative_json_file_path = json_file.relative_to(WORKSPACE_ROOT)

    index_data = tool_index_handler["data"]
    stored_entry = index_data.get(tool_id)  # dict with 'crc' and 'timestamp' or None
    stored_crc = stored_entry.get("crc") if stored_entry else None
    stored_timestamp = stored_entry.get("timestamp") if stored_entry else 0

    current_time = time.time()
    is_cache_valid = stored_entry is not None and txt_file.is_file() and (current_time - stored_timestamp < CACHE_DURATION_SECONDS)

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
            current_crc = calculate_crc(current_output)
            log.debug(f"Calculated CRC for '{tool_id}': {current_crc} (Stored: {stored_crc})")

        except FileNotFoundError:
            # This error should ideally not happen now if 'uv' is found,
            # but keep the check for robustness.
            pytest.fail(f"Failed to run command via uv: '{uv_command_str_for_display}'. " f"Is 'uv' installed and on PATH?")
        except subprocess.TimeoutExpired:
            pytest.fail(f"Command timed out for '{tool_id}': '{uv_command_str_for_display}'")
        except Exception as e:
            # Catch other potential subprocess errors
            pytest.fail(f"Unexpected error running command for '{tool_id}': '{uv_command_str_for_display}'\\nError: {e}")

    # --- Check for changes and file existence ---
    txt_needs_update = (current_crc != stored_crc) or (not txt_file.is_file())

    if txt_needs_update:
        # --- Update required for TXT ---
        print(f"Updating TXT baseline for '{tool_id}': {relative_txt_file_path}")

        # Ensure directories exist
        try:
            txt_base_dir.mkdir(parents=True, exist_ok=True)  # Ensure TXT directory exists
        except OSError as e:
            pytest.fail(f"Failed to create directory {txt_base_dir}: {e}")

        # Write the new content
        try:
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
