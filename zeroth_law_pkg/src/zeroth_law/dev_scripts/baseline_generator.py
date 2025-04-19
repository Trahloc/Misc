#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/baseline_generator.py
"""
Core logic for generating or verifying a single tool's baseline files.
"""

import logging
import shlex
import sys
import time
from enum import Enum, auto
from pathlib import Path
from typing import List, Tuple, Callable

# --- Add project root to path for sibling imports ---
try:
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root))
except NameError:
    # Allow execution even if __file__ is not defined
    project_root = Path.cwd()
    # Assuming src is in the cwd or parent for direct execution needs
    if not (project_root / "src").exists():
        # A simple heuristic, might need adjustment
        project_root = project_root.parent
    sys.path.insert(0, str(project_root))


# --- Import project modules ---
try:
    from src.zeroth_law.dev_scripts.capture_txt_tty_output import capture_tty_output as default_capture_tty_output
    from src.zeroth_law.lib.crc import calculate_crc32 as calculate_hex_crc32
    from src.zeroth_law.dev_scripts.tool_index_utils import (
        load_tool_index as default_load_tool_index,
        save_tool_index as default_save_tool_index,
        TOOLS_DIR_ROOT,  # Import constant
    )
    from src.zeroth_law.dev_scripts.baseline_writers import (
        write_ground_truth_txt as default_write_ground_truth_txt,
        ensure_skeleton_json_exists as default_ensure_skeleton_json_exists,
    )
except ImportError as e:
    print(f"Error importing modules. Check PYTHONPATH and file locations. Details: {e}", file=sys.stderr)
    # Optionally, re-raise or define dummy functions if needed for basic loading
    sys.exit(1)

# --- LOGGING ---
log = logging.getLogger(__name__)

# --- CONSTANTS ---
DEFAULT_ENCODING = "utf-8"
DEFAULT_ENCODING_ERRORS = "replace"


# --- Status Enum ---
class BaselineStatus(Enum):
    UP_TO_DATE = auto()
    UPDATED = auto()
    FAILED_CAPTURE = auto()
    FAILED_DECODE = auto()
    FAILED_CRC_CALC = auto()
    FAILED_LOAD_INDEX = auto()  # Less likely with current utils, but possible
    FAILED_WRITE_TXT = auto()
    FAILED_SAVE_INDEX = auto()
    FAILED_COMMAND_SPLIT = auto()
    FAILED_DERIVE_ID = auto()
    FAILED_SKELETON_WRITE = auto()  # Added for clarity
    UNEXPECTED_ERROR = auto()


# --- Helper Functions ---


def derive_tool_and_id(original_command_list: List[str]) -> Tuple[str, str]:
    """Derives the tool name (for dir) and tool ID (for index key/filename) from the command list."""
    if not original_command_list:
        raise ValueError("Cannot derive tool name/ID from empty command list.")

    tool_name = original_command_list[0]
    command_parts = original_command_list
    # Consider removing --help here if it was added artificially before capture
    # if command_parts[-1] in ["--help", "-h"]:
    #     command_parts = command_parts[:-1]

    # Use underscore as separator for the ID
    tool_id = "_".join(command_parts).replace(" ", "_")

    # Basic sanitization for filenames/IDs
    # Allow lowercase, uppercase, numbers, underscore, hyphen
    tool_id = "".join(c for c in tool_id if c.isalnum() or c in ["_", "-"])
    # Avoid excessively long IDs (though less critical for keys)
    max_len = 60
    if len(tool_id) > max_len:
        tool_id = tool_id[:max_len]
        log.warning(f"Derived tool_id was truncated to {max_len} chars: {tool_id}")

    # Avoid potential issues with names like '.' or '..'
    if tool_id in [".", ".."] or not tool_id:
        raise ValueError(f"Derived invalid tool_id: '{tool_id}'")

    log.info(f"Derived tool_name='{tool_name}', tool_id='{tool_id}'")
    return tool_name, tool_id


# --- Core Generation/Verification Logic ---


def generate_or_verify_baseline(
    command_str: str,
    # Add dependencies as arguments with defaults
    load_tool_index_func: Callable = default_load_tool_index,
    save_tool_index_func: Callable = default_save_tool_index,
    capture_tty_output_func: Callable = default_capture_tty_output,
    write_ground_truth_txt_func: Callable = default_write_ground_truth_txt,
    ensure_skeleton_json_exists_func: Callable = default_ensure_skeleton_json_exists,
) -> BaselineStatus:
    """Orchestrates the baseline generation/verification for a single command."""
    log.info(f"--- Processing command: '{command_str}' ---")

    # 1. Preparation
    try:
        original_command_list = shlex.split(command_str)
        if not original_command_list:
            log.error("Empty command provided.")
            return BaselineStatus.FAILED_COMMAND_SPLIT
    except ValueError as e:
        log.error(f"Error splitting command '{command_str}': {e}")
        return BaselineStatus.FAILED_COMMAND_SPLIT

    try:
        tool_name, tool_id = derive_tool_and_id(original_command_list)
        tool_dir = TOOLS_DIR_ROOT / tool_name
    except ValueError as e:
        log.error(f"Failed to derive tool name/id for '{command_str}': {e}")
        return BaselineStatus.FAILED_DERIVE_ID

    # 2. Capture & Calculate
    command_to_execute_str = f"{command_str} --help | cat"
    log.info(f"Executing: {command_to_execute_str}")
    try:
        capture_cmd_list = ["sh", "-c", command_to_execute_str]
        # Use the injected function
        output_bytes, exit_code = capture_tty_output_func(capture_cmd_list)
        if exit_code != 0:
            log.warning(
                f"Capture command for '{command_str}' exited with code {exit_code}. Output may be incomplete or error message."
            )
        log.info(f"Captured {len(output_bytes)} bytes for '{tool_id}'.")
    except Exception as e:
        log.exception(f"Failed to capture output for '{command_to_execute_str}': {e}")
        return BaselineStatus.FAILED_CAPTURE

    try:
        output_string = output_bytes.decode(DEFAULT_ENCODING, errors=DEFAULT_ENCODING_ERRORS)
        # Basic normalization (replace Windows newlines, strip trailing whitespace)
        output_string = output_string.replace("\r\n", "\n").replace("\r", "\n").rstrip()
        log.info(f"Decoded output for '{tool_id}'.")
    except Exception as e:
        log.exception(f"Failed to decode captured bytes for '{tool_id}': {e}")
        return BaselineStatus.FAILED_DECODE

    try:
        new_crc = calculate_hex_crc32(output_string)
        log.info(f"Calculated new CRC for '{tool_id}': {new_crc}")
    except Exception as e:
        log.exception(f"Failed to calculate CRC for '{tool_id}': {e}")
        return BaselineStatus.FAILED_CRC_CALC

    # 3. Load Index
    try:
        # Use the injected function
        index_data = load_tool_index_func()
        existing_index_entry = index_data.get(tool_id)
        existing_index_crc = None
        if existing_index_entry and isinstance(existing_index_entry, dict):
            existing_index_crc = existing_index_entry.get("crc")  # Using 'crc' key
        log.info(f"Loaded index. Existing CRC for '{tool_id}': {existing_index_crc}")
    except Exception as e:
        # load_tool_index handles most errors, but catch unexpected ones
        log.exception(f"Unexpected error loading tool index: {e}")
        return BaselineStatus.FAILED_LOAD_INDEX

    # 4. Compare CRCs
    crc_match = existing_index_crc is not None and new_crc.lower() == existing_index_crc.lower()

    # 5. Action based on Comparison
    if crc_match:
        log.info(f"CRC match for '{tool_id}'. Baseline TXT is up-to-date.")
        # Use the injected function
        skel_success = ensure_skeleton_json_exists_func(tool_dir, tool_id, original_command_list)
        if not skel_success:
            log.warning(f"Although TXT is up-to-date, failed to ensure skeleton JSON exists for '{tool_id}'.")
            # Decide if this should be a failure state or just a warning.
            # For now, treat as success since primary goal (TXT/Index) is met.
        return BaselineStatus.UP_TO_DATE
    else:
        if existing_index_crc:
            log.info(
                f"CRC mismatch for '{tool_id}' (Index: {existing_index_crc}, New: {new_crc}). Updating baseline..."
            )
        else:
            log.info(f"New tool '{tool_id}'. Creating baseline...")

        # Write TXT (Overwrite)
        # Use the injected function
        if not write_ground_truth_txt_func(tool_dir, tool_id, output_string):
            log.error(f"Failed to write ground truth TXT for '{tool_id}'. Aborting update.")
            return BaselineStatus.FAILED_WRITE_TXT

        # Update Index Data (In Memory)
        index_data[tool_id] = {"crc": new_crc, "timestamp": time.time()}
        # Preserve subcommands if they existed (simple approach)
        if existing_index_entry and "subcommands" in existing_index_entry:
            index_data[tool_id]["subcommands"] = existing_index_entry["subcommands"]

        # Save Index
        try:
            # Use the injected function
            save_tool_index_func(index_data)
            log.info(f"Successfully updated index for '{tool_id}' with CRC {new_crc}.")
        except Exception as e:
            log.error(f"Failed to save updated index after writing TXT for '{tool_id}': {e}")
            # TXT is written, but index is inconsistent!
            return BaselineStatus.FAILED_SAVE_INDEX

        # Ensure Skeleton JSON
        # Use the injected function
        skel_success = ensure_skeleton_json_exists_func(tool_dir, tool_id, original_command_list)
        if not skel_success:
            log.error(f"Failed to write skeleton JSON for '{tool_id}' after updating TXT and index.")
            # TXT and Index are updated, but skeleton failed. This is still problematic.
            return BaselineStatus.FAILED_SKELETON_WRITE

        log.info(f"Baseline update complete for '{tool_id}'.")
        return BaselineStatus.UPDATED


# Example usage (for testing this module directly)
if __name__ == "__main__":
    # Setup basic logging for direct execution test
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    log.info("Testing baseline_generator...")

    # --- Test Cases ---
    test_commands = [
        "ruff --help",  # Ruff help often changes slightly, good for testing UPDATED
        "ls --help",  # A standard command, likely UP_TO_DATE on second run
        "nonexistent_command_xyz",  # Should fail capture
        # Add more commands as needed
    ]

    results = {}
    for cmd in test_commands:
        # Remove --help if present, as generate_or_verify_baseline adds it
        cmd_base = cmd.replace(" --help", "").replace(" -h", "")
        log.info(f"\n>>> Testing command: '{cmd_base}'")
        try:
            status = generate_or_verify_baseline(cmd_base)
            log.info(f"<<< Status for '{cmd_base}': {status.name}")
            results[cmd_base] = status.name
        except Exception as e:
            log.exception(f"!!! Unexpected exception during test for '{cmd_base}': {e}")
            results[cmd_base] = "UNEXPECTED_EXCEPTION"

    print("\n--- Test Summary ---")
    for cmd, result in results.items():
        print(f"- {cmd}: {result}")

    log.info("Testing finished.")
