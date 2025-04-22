#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/baseline_generator.py
"""
Core logic for generating/verifying baseline files (TXT, index entry, skeleton JSON).
Called by tests (e.g., test_ensure_txt_baselines_exist.py) and potentially CLI wrappers.
"""

import logging
import subprocess
import time
import json
import zlib  # For CRC32 calculation
from pathlib import Path
from enum import Enum, auto
from typing import Tuple, Dict, Any, Optional, Sequence
import sys

# Assuming sibling imports work due to path adjustments in callers
from src.zeroth_law.lib.crc import calculate_crc32
from src.zeroth_law.dev_scripts.tool_index_utils import (
    get_index_entry,
    load_update_and_save_entry,
    TOOL_INDEX_PATH,
    TOOLS_DIR_ROOT,
    load_tool_index,
)

log = logging.getLogger(__name__)


class BaselineStatus(Enum):
    UP_TO_DATE = auto()
    UPDATED = auto()
    FAILED_CAPTURE = auto()
    FAILED_WRITE_TXT = auto()
    FAILED_LOAD_INDEX = auto()
    FAILED_SAVE_INDEX = auto()
    FAILED_SKELETON_ENSURE = auto()  # Changed from WRITE to ENSURE
    FAILED_INDEX_ACCESS = auto()  # Error finding/updating specific entry
    UNEXPECTED_ERROR = auto()
    CAPTURE_SUCCESS = auto()  # Status when capture and CRC calc succeed, before index comparison


def _capture_command_output(command_sequence: Tuple[str, ...]) -> Tuple[bytes | None, int]:
    """Captures the raw byte output of command --help | cat."""
    is_python_script_override = (
        len(command_sequence) > 1 and command_sequence[0] == sys.executable and command_sequence[1].endswith(".py")
    )

    command_list = list(command_sequence)
    shell_command = ""

    # Only add --help if it's NOT a python script override AND --help isn't already there
    if not is_python_script_override and not any(arg == "--help" for arg in command_sequence):
        command_list.append("--help")

    # Prepare command for execution
    if is_python_script_override:
        log.debug("Detected python script override, executing directly.")
        # command_list is already set correctly
    else:
        # Construct the shell command: uv run -- command ... [--help] | cat
        shell_command = f"uv run -- {' '.join(command_list)} | cat"
        log.info(f"Executing capture: {shell_command}")

    try:
        if is_python_script_override:
            log.debug(f"Executing command list directly: {command_list}")
            result = subprocess.run(
                command_list,  # Execute the list directly
                capture_output=True,
                check=False,  # Check manually based on 'cat' behavior
                timeout=30,  # Increased timeout for potentially slow help outputs
            )
        else:
            # Execute using shell=True with the constructed shell_command
            assert shell_command is not None  # Ensure shell_command was set
            result = subprocess.run(
                shell_command,
                capture_output=True,
                check=False,  # Check manually based on 'cat' behavior
                shell=True,
                timeout=30,  # Increased timeout for potentially slow help outputs
            )
        # `cat` usually exits 0 unless input pipe is broken. Rely on output presence.
        if result.returncode != 0:
            log.warning(
                f"Capture command exited with {result.returncode}. Stderr: {result.stderr.decode(errors='ignore')}"
            )
            # Don't necessarily fail yet, maybe some output was captured

        # Use ' '.join(command_list) for consistent logging regardless of execution path
        log_cmd_str = " ".join(command_list)

        if not result.stdout and result.returncode != 0:
            log.error(
                f"Failed to capture any output for {log_cmd_str}. Stderr: {result.stderr.decode(errors='ignore')}"
            )
            return None, result.returncode
        elif not result.stdout:
            log.warning(
                f"Captured empty stdout for {log_cmd_str}, but command exited 0. Proceeding with empty content."
            )
            return b"", 0  # Treat as empty output

        return result.stdout, 0  # Success or partial success with output

    except subprocess.TimeoutExpired:
        log_cmd_str = " ".join(command_list)  # Ensure log_cmd_str is defined
        log.error(f"Timeout expired capturing output for {log_cmd_str}")
        return None, -1  # Use a distinct code for timeout
    except Exception as e:
        log_cmd_str = " ".join(command_list)  # Ensure log_cmd_str is defined
        log.exception(f"Unexpected error capturing output for {log_cmd_str}: {e}")
        return None, -2  # Use a distinct code for other errors


def _ensure_skeleton_json(json_path: Path, command_sequence_str: str):
    """Creates a minimal skeleton JSON if it doesn't exist."""
    if json_path.exists():
        log.debug(f"Skeleton check: JSON file already exists: {json_path}")
        return True  # Nothing to do

    log.info(f"Skeleton check: JSON file missing, creating skeleton: {json_path}")
    skeleton_content = {
        "command_sequence": command_sequence_str,
        "description": "",
        "usage": "",
        "options": {},
        "arguments": {},
        "subcommands": [],
        "metadata": {
            "ground_truth_crc": "0x00000000",  # Placeholder CRC
            "schema_version": "1.0",  # Example metadata
        },
    }
    try:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(skeleton_content, f, indent=2)
        log.info(f"Successfully created skeleton JSON: {json_path}")
        return True
    except OSError as e:
        log.error(f"Failed to create skeleton JSON file {json_path}: {e}")
        return False
    except Exception as e:
        log.exception(f"Unexpected error creating skeleton JSON {json_path}: {e}")
        return False


def generate_or_verify_baseline(
    command_sequence_str: str,
    root_dir: Path | None = None,
    executable_command_override: Sequence[str] | None = None,
) -> Tuple[BaselineStatus, Optional[str], Optional[float]]:
    """Generate or verify baseline files (TXT, skeleton JSON) for a command sequence.

    This function now focuses on file generation and CRC calculation.
    It returns the status, the calculated CRC (hex string), and the timestamp,
    deferring index updates to the caller.

    Allows overriding the actual command executed for testing purposes.

    Args:
        command_sequence_str: The command sequence string to process.
        root_dir: Optional root directory for testing purposes. If None, uses TOOLS_DIR_ROOT.
        executable_command_override: Optional sequence of strings representing the actual
                                     command to execute (e.g., [sys.executable, script_path]).
                                     If None, executes command_sequence_str.

    Returns:
        Tuple[BaselineStatus, Optional[str], Optional[float]]:
            - The status of the file generation/verification.
            - The calculated CRC hex string (or None on failure).
            - The timestamp of the check (or None on failure).
    """
    command_sequence_for_id = tuple(command_sequence_str.split())
    command_id = "_".join(command_sequence_for_id)  # Used for filenames and logging
    tool_name = command_sequence_for_id[0]

    # Sequence for Execution (use override if provided)
    command_sequence_to_execute = (
        tuple(executable_command_override) if executable_command_override is not None else command_sequence_for_id
    )

    active_root_dir = root_dir if root_dir is not None else TOOLS_DIR_ROOT
    current_time = time.time()

    log.info(f"Processing baseline files for ID: {command_id}")
    if executable_command_override:
        log.info(f"Executing override command: {' '.join(command_sequence_to_execute)}")

    # Define paths
    tool_dir = active_root_dir / tool_name
    txt_path = tool_dir / f"{command_id}.txt"
    json_path = tool_dir / f"{command_id}.json"

    # 1. Capture output using the execution sequence
    captured_output_bytes, exit_code = _capture_command_output(command_sequence_to_execute)
    if captured_output_bytes is None:
        log.error(
            f"Failed to capture output for {command_id} (Exec: {' '.join(command_sequence_to_execute)}, Exit: {exit_code})."
        )
        return BaselineStatus.FAILED_CAPTURE, None, None

    # 2. Calculate CRC
    calculated_crc_int = zlib.crc32(captured_output_bytes) & 0xFFFFFFFF
    calculated_crc_hex = f"0x{calculated_crc_int:08X}"
    log.info(f"Calculated CRC for {command_id}: {calculated_crc_hex}")

    # 3. Write .txt file (always write/overwrite based on captured output)
    try:
        tool_dir.mkdir(parents=True, exist_ok=True)
        txt_path.write_bytes(captured_output_bytes)
        log.info(f"Successfully wrote/updated {txt_path}")
    except OSError as e:
        log.error(f"Failed to write {txt_path}: {e}")
        return BaselineStatus.FAILED_WRITE_TXT, calculated_crc_hex, current_time  # Return CRC even on write failure
    except Exception as e:
        log.exception(f"Unexpected error writing {txt_path}: {e}")
        return BaselineStatus.FAILED_WRITE_TXT, calculated_crc_hex, current_time

    # 4. Ensure skeleton JSON exists
    if not _ensure_skeleton_json(json_path, command_sequence_str):
        log.error(f"FAILED to ensure skeleton JSON exists at {json_path} for {command_id}.")
        return BaselineStatus.FAILED_SKELETON_ENSURE, calculated_crc_hex, current_time

    log.info(f"Successfully processed files for {command_id}.")
    # Return a success status, the CRC, and the timestamp for the caller to handle index logic
    return BaselineStatus.CAPTURE_SUCCESS, calculated_crc_hex, current_time


# Example Usage (if run directly, though intended to be imported)
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     test_command = "ruff check" # Example
#     status, crc, timestamp = generate_or_verify_baseline(test_command)
#     print(f"Baseline generation for '{test_command}' finished with status: {status.name}, CRC: {crc}, Timestamp: {timestamp}")

# <<< ZEROTH LAW FOOTER >>>
"""
## LIMITATIONS & RISKS:
- Relies on `uv run -- command --help | cat` behavior for capturing output and stripping ANSI codes. Errors in `cat` or unusual terminal behavior could affect output.
- Assumes `tool_index_utils` correctly handles loading, saving, and updating the index, including nested structures for subcommands.
- Skeleton JSON creation is minimal; subsequent AI interpretation is crucial.
- Filesystem permissions could prevent writing TXT, JSON, or updating the index.
- Concurrent runs of this script could lead to race conditions when updating `tool_index.json`. Requires external locking if parallelism is needed.

## REFINEMENT IDEAS:
- Add more specific error handling/status codes in `BaselineStatus`.
- Implement locking for `tool_index.json` updates if concurrent execution becomes a requirement.
- Enhance error reporting to provide more context (e.g., specific OS errors).
- Consider using a more robust method than `subprocess.run(shell=True)` for capturing output if complex command sequences arise, though `uv run -- ... | cat` is fairly standard.
- Add tests specifically for `baseline_generator.py`.

## ZEROTH LAW COMPLIANCE (ZLF):
# Framework Version: 2025-04-18T14:29:24+08:00
# Compliance results populated by the Zeroth Law Tool (ZLT).
# Overall Status: [PENDING]
# Score: [N/A]
# Penalties: [N/A]
# Timestamp: [YYYY-MM-DDTHH:MM:SS+ZZ:ZZ]
"""
