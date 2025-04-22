# FILE: tests/test_tool_defs/test_ensure_txt_baselines_exist.py
"""
Tests that a TXT baseline file exists for every managed tool/subcommand
and that its content matches the expected CRC stored in a central index.
Uses concurrent execution for speed.
Generates missing files and updates the index if needed.
"""

import logging
import subprocess
import sys
import time
import pytest
from pathlib import Path
import json
import toml
import os
import concurrent.futures  # Added for parallel execution
from typing import Tuple, Dict, Any, List, Optional  # Added List, Optional

# Import necessary components from baseline_generator
from src.zeroth_law.dev_scripts.baseline_generator import (
    generate_or_verify_baseline,
    BaselineStatus,
)

# Corrected Imports
from src.zeroth_law.dev_scripts.tool_discovery import load_tools_config
from src.zeroth_law.lib.crc import calculate_crc32  # Correct function name

# Need index utils for post-processing
from src.zeroth_law.dev_scripts.tool_index_utils import get_index_entry, load_update_and_save_entry

# Setup logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)  # Keep level WARNING for less noise

# Constants
MAX_WORKERS = os.cpu_count() or 4  # Sensible default for thread pool

# --- Helper Functions (Keep existing helpers like command_sequence_to_id, _get_uv_bin_dir, etc.) ---


def command_sequence_to_id(command_parts: tuple[str, ...]) -> str:
    """Creates a readable ID for parametrized tests and dictionary keys."""
    return "_".join(command_parts)


def is_tool_available(tool_name: str, workspace_root: Path) -> bool:
    """Checks if a tool is likely runnable via 'uv run -- which tool_name'."""
    command = ["uv", "run", "--", "which", tool_name]
    log.debug(f"Checking availability: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            cwd=workspace_root,
            timeout=10,  # Short timeout for a simple check
        )
        log.debug(f"'which {tool_name}' exited with {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        log.warning(f"Error checking availability for {tool_name}: {e}")
        return False


def _get_uv_bin_dir(workspace_root: Path) -> Path | None:
    """Finds the bin directory of the current uv environment."""
    try:
        # Run 'uv run which python' to find the interpreter path
        result = subprocess.run(
            ["uv", "run", "which", "python"],
            capture_output=True,
            text=True,
            check=True,  # Fail if command fails
            cwd=workspace_root,
            timeout=10,
        )
        python_path_str = result.stdout.strip()
        if not python_path_str:
            log.error("'uv run which python' did not return a path.")
            return None

        python_path = Path(python_path_str)
        bin_dir = python_path.parent
        if bin_dir.is_dir() and bin_dir.name == "bin":  # Basic sanity check
            log.info(f"Found environment bin directory: {bin_dir}")
            return bin_dir
        else:
            log.error(f"Could not reliably determine bin directory from python path: {python_path}")
            return None
    except FileNotFoundError:
        log.error("Failed to run 'uv'. Is it installed and in PATH?")
        return None
    except subprocess.CalledProcessError as e:
        log.error(f"'uv run which python' failed (return code {e.returncode}): {e.stderr}")
        return None
    except subprocess.TimeoutExpired:
        log.error("'uv run which python' timed out.")
        return None
    except Exception as e:
        log.error(f"Error finding uv bin directory: {e}")
        return None


def _get_available_commands(bin_dir: Path) -> set[str]:
    """Lists executable files in the specified bin directory."""
    available = set()
    if not bin_dir or not bin_dir.is_dir():
        return available
    try:
        for item_name in os.listdir(bin_dir):
            item_path = bin_dir / item_name
            # Check if it's a file and executable
            if item_path.is_file() and os.access(item_path, os.X_OK):
                available.add(item_name)
    except OSError as e:
        log.error(f"Error reading bin directory {bin_dir}: {e}")
    return available


def get_managed_sequences(config_path: Path, tools_dir: Path, workspace_root: Path) -> list[tuple[str, ...]]:
    """Loads managed tool sequences based on pyproject.toml, validating against available commands."""
    managed_sequences = []
    try:
        config_data = toml.load(config_path)
        zlt_config = config_data.get("tool", {}).get("zeroth-law", {})
        tools_config = zlt_config.get("tools", {})
        whitelist = set(tools_config.get("whitelist", []))  # Base tool names expected to be managed
        blacklist = set(tools_config.get("blacklist", []))  # Base tool/subcommand names to ignore
    except FileNotFoundError:
        log.error(f"Configuration file not found: {config_path}")
        pytest.fail(f"Missing configuration file: {config_path}")  # Fail hard if config missing
        return []  # Should not be reached
    except Exception as e:
        log.error(f"Error reading config file {config_path}: {e}")
        pytest.fail(f"Error reading configuration file {config_path}: {e}")  # Fail hard on config error
        return []  # Should not be reached

    # --- Step 1 & 2: Get available commands from bin ---
    bin_dir = _get_uv_bin_dir(workspace_root)
    if not bin_dir:
        pytest.fail(
            "CRITICAL: Could not determine environment bin directory ('uv run which python' failed?). Cannot proceed."
        )
        return []  # Should not be reached

    available_commands = _get_available_commands(bin_dir)
    if not available_commands:
        pytest.fail(
            f"CRITICAL: Found bin directory {bin_dir}, but no executable commands within. Check environment installation."
        )
        return []  # Should not be reached

    log.info(f"Found {len(available_commands)} available commands in {bin_dir}.")
    log.debug(f"Available commands: {sorted(list(available_commands))}")

    # --- Step 3 & 4: Apply Whitelist & Blacklist to BASE commands ---
    potential_base_tools = available_commands.difference(blacklist)
    validated_base_tools = potential_base_tools.intersection(whitelist)

    log.info(f"Derived {len(validated_base_tools)} validated base tools after applying whitelist/blacklist.")
    log.debug(f"Validated base tools: {sorted(list(validated_base_tools))}")

    # --- Step 6.5: Error on Missing Whitelisted BASE Tools ---
    missing_whitelisted = whitelist.difference(available_commands)
    if missing_whitelisted:
        fail_message = (
            f"Found {len(missing_whitelisted)} tool(s) listed in the pyproject.toml whitelist "
            f"that were NOT found as executable commands in the environment bin directory ({bin_dir}):\n"
            f"  - {', '.join(sorted(list(missing_whitelisted)))}\n"
            f"Action Required: Ensure these tools are correctly installed in the 'uv' environment "
            f"OR remove them from the 'whitelist' in pyproject.toml ([tool.zeroth-law.tools])."
        )
        pytest.fail(fail_message)  # Fail the test run early
        return []  # Should not be reached

    # --- Log Blacklist issues detected (Informational) ---
    found_blacklist = available_commands.intersection(blacklist)
    if found_blacklist:
        log.info(
            f"The following blacklisted tools were found in the environment bin and correctly ignored: {sorted(list(found_blacklist))}"
        )

    # --- Step 7: Generate Sequences for Validated Base Tools and their Subcommands ---
    for tool_name in sorted(list(validated_base_tools)):
        if tool_name in blacklist:
            log.info(f"Ignoring base tool sequence '{tool_name}' because it is explicitly blacklisted.")
            continue
        managed_sequences.append((tool_name,))
        tool_json_path = tools_dir / tool_name / f"{tool_name}.json"
        if tool_json_path.is_file():
            try:
                with open(tool_json_path, "r", encoding="utf-8") as f:
                    tool_data = json.load(f)
                subcommands_list = tool_data.get("subcommands_detail", {})
                if isinstance(subcommands_list, dict):
                    for sub_name, sub_details in subcommands_list.items():
                        if sub_name:
                            subcommand_tool_id = command_sequence_to_id((tool_name, sub_name))
                            if subcommand_tool_id in blacklist:
                                log.info(
                                    f"Ignoring subcommand sequence '{subcommand_tool_id}' because it is blacklisted."
                                )
                            else:
                                managed_sequences.append((tool_name, sub_name))
                                log.debug(
                                    f"Adding managed sequence: ({tool_name}, {sub_name}) -> ID: {subcommand_tool_id}"
                                )
                                # Correctly indented block starts here:
                                if isinstance(sub_details, dict) and "subcommands_detail" in sub_details:
                                    nested_subcommands = sub_details.get("subcommands_detail", {})
                                    if isinstance(nested_subcommands, dict):
                                        for nested_sub_name, nested_sub_details in nested_subcommands.items():
                                            if nested_sub_name:
                                                nested_subcommand_tool_id = command_sequence_to_id(
                                                    (tool_name, sub_name, nested_sub_name)
                                                )
                                                if nested_subcommand_tool_id in blacklist:
                                                    log.info(
                                                        f"Ignoring subsubcommand sequence '{nested_subcommand_tool_id}' because it is blacklisted."
                                                    )
                                                else:
                                                    managed_sequences.append((tool_name, sub_name, nested_sub_name))
                                                    log.debug(
                                                        f"Adding managed sequence: ({tool_name}, {sub_name}, {nested_sub_name}) -> ID: {nested_subcommand_tool_id}"
                                                    )
            except json.JSONDecodeError:
                log.warning(
                    f"Could not decode JSON for tool '{tool_name}' at {tool_json_path} to discover subcommands."
                )
            except Exception as e:
                log.error(f"Error reading JSON for '{tool_name}' subcommands: {e}")
        else:
            log.debug(
                f"No JSON definition found for base tool '{tool_name}' at {tool_json_path}, cannot discover subcommands."
            )

    log.info(f"Generated {len(managed_sequences)} managed command sequences for testing.")
    log.debug(f"Final managed sequences: {managed_sequences}")
    return managed_sequences


# --- Global Definition of Managed Sequences ---
# Calculate this once at module load time
_current_file_dir_for_managed = Path(__file__).resolve().parent
_workspace_root_for_managed = _current_file_dir_for_managed.parent.parent
_config_path_for_managed = _workspace_root_for_managed / "pyproject.toml"
_tools_dir_for_managed = _workspace_root_for_managed / "src/zeroth_law/tools"
MANAGED_COMMAND_SEQUENCES = get_managed_sequences(
    _config_path_for_managed, _tools_dir_for_managed, _workspace_root_for_managed
)

if not MANAGED_COMMAND_SEQUENCES:
    log.warning("MANAGED_COMMAND_SEQUENCES is empty after loading from pyproject.toml and checking environment.")


# --- Worker Function for Concurrent Execution ---
def _check_single_baseline_worker(
    command_sequence: Tuple[str, ...], workspace_root: Path, tools_dir: Path
) -> Dict[str, Any]:
    """Worker function to process a single command sequence baseline (no index interaction)."""
    tool_id = command_sequence_to_id(command_sequence)
    command_sequence_str = " ".join(command_sequence)
    # Pass the base tools dir (e.g., src/zeroth_law/tools) to generate_or_verify_baseline
    base_tools_dir_for_worker = workspace_root / "src/zeroth_law/tools"
    result_data = {"tool_id": tool_id, "command_sequence": command_sequence}

    try:
        status, calculated_crc_hex, timestamp = generate_or_verify_baseline(
            command_sequence_str,
            root_dir=base_tools_dir_for_worker,  # Pass correct base tools dir
        )

        result_data["status_code"] = status
        result_data["status"] = status.name
        result_data["calculated_crc"] = calculated_crc_hex
        result_data["timestamp"] = timestamp

        # Post-generation verification (TXT existence)
        if status in [BaselineStatus.CAPTURE_SUCCESS]:  # Only check if generation step reported success
            tool_name = command_sequence[0]
            # Use the tools_dir passed to the worker (derived from fixture)
            tool_dir_path = tools_dir / tool_name
            txt_file = tool_dir_path / f"{tool_id}.txt"
            if not txt_file.is_file():
                result_data["status"] = "ERROR_TXT_MISSING_POST_GEN"
                result_data["error_message"] = f"TXT file missing after successful generation attempt: {txt_file}"
                log.error(f"[{tool_id}] {result_data['error_message']}")
            else:
                log.info(f"[{tool_id}] Worker completed successfully ({status.name}). CRC: {calculated_crc_hex}")
        elif status != BaselineStatus.CAPTURE_SUCCESS:
            log.error(f"[{tool_id}] Worker reported failure status: {status.name}")
            result_data["error_message"] = f"Baseline generation failed with status {status.name}"

    except Exception as e:
        log.exception(f"[{tool_id}] Unexpected error in worker: {e}")
        result_data["status"] = "ERROR_UNEXPECTED_WORKER"
        result_data["error_message"] = f"Unexpected worker error: {e}"

    return result_data


# --- Main Test Function (Concurrent Execution) ---
def test_all_txt_baselines_concurrently(WORKSPACE_ROOT, TOOLS_DIR, tool_index_handler):  # No parametrize
    """
    Ensures TXT baselines are generated/verified concurrently and the index
    is updated sequentially based on the results.
    """
    if not MANAGED_COMMAND_SEQUENCES:
        pytest.skip("Skipping test: No managed command sequences found.")

    log.info(
        f"Starting concurrent baseline checks for {len(MANAGED_COMMAND_SEQUENCES)} sequences using {MAX_WORKERS} workers..."
    )
    start_time = time.monotonic()
    results = []
    futures = []

    # Use ThreadPoolExecutor for I/O-bound tasks (running subprocesses, file ops)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for command_parts in MANAGED_COMMAND_SEQUENCES:
            if not command_parts:
                continue  # Skip empty sequences if any
            futures.append(executor.submit(_check_single_baseline_worker, command_parts, WORKSPACE_ROOT, TOOLS_DIR))

        # Use tqdm for progress bar if installed (optional enhancement)
        try:
            from tqdm import tqdm

            futures_iterator = tqdm(
                concurrent.futures.as_completed(futures), total=len(futures), desc="Checking Baselines"
            )
        except ImportError:
            futures_iterator = concurrent.futures.as_completed(futures)

        for future in futures_iterator:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                log.exception(f"Error retrieving result from future: {e}")
                results.append(
                    {
                        "tool_id": "unknown",
                        "status": "ERROR_FUTURE_EXCEPTION",
                        "error_message": f"Future raised exception: {e}",
                    }
                )

    execution_duration = time.monotonic() - start_time
    log.info(f"Concurrent baseline checks completed in {execution_duration:.2f} seconds.")

    # --- Post-Processing: Index Update and Verification (Sequential) ---
    log.info("Starting sequential index update and final verification...")
    failures = []
    index_updates_performed = 0

    # Load index *once* before processing results
    tool_index_handler.reload()  # Ensure we have the latest index state
    raw_index_data = tool_index_handler.get_raw_index_data()

    for result in results:
        tool_id = result.get("tool_id", "unknown")
        status = result.get("status", "ERROR_UNKNOWN")
        status_code = result.get("status_code")
        calculated_crc = result.get("calculated_crc")
        timestamp = result.get("timestamp")
        command_sequence = result.get("command_sequence")
        error_message = result.get("error_message")

        # Check for worker errors first
        if "ERROR" in status:
            failures.append(f"{tool_id}: Worker failed - {status} ({error_message or 'No details'})")
            continue

        # Check if baseline generation step succeeded
        if status_code != BaselineStatus.CAPTURE_SUCCESS:
            failures.append(f"{tool_id}: Baseline generation failed - {status} ({error_message or 'No details'})")
            continue

        # Generation succeeded, now check/update index
        if not command_sequence or calculated_crc is None or timestamp is None:
            failures.append(
                f"{tool_id}: Worker succeeded but returned incomplete data (Seq: {command_sequence}, CRC: {calculated_crc}, TS: {timestamp})"
            )
            continue

        # Get current index entry
        current_entry = get_index_entry(raw_index_data, command_sequence)
        stored_crc = current_entry.get("crc") if current_entry else None

        entry_update_data = {}
        needs_update = False

        if stored_crc != calculated_crc:
            log.info(
                f"[{tool_id}] Index Update: CRC mismatch (Stored: {stored_crc}, Calculated: {calculated_crc}). Queuing update."
            )
            entry_update_data["crc"] = calculated_crc
            entry_update_data["updated_timestamp"] = timestamp
            entry_update_data["checked_timestamp"] = timestamp
            needs_update = True
        else:
            # CRCs match, just update checked_timestamp if it's significantly different
            stored_checked = current_entry.get("checked_timestamp")
            if stored_checked is None or abs(stored_checked - timestamp) > 1:  # Update if missing or differs > 1 sec
                log.debug(f"[{tool_id}] Index Check: CRC matches ({stored_crc}). Queuing checked_timestamp update.")
                entry_update_data["checked_timestamp"] = timestamp
                needs_update = True
            # else: # CRC matches and timestamp is recent, no update needed
            #     log.debug(f"[{tool_id}] Index Check: CRC matches and checked_timestamp is recent.")

        # Perform the update using the locked utility function if needed
        if needs_update:
            if not load_update_and_save_entry(command_sequence, entry_update_data):
                error_msg = f"Failed to update index entry for {tool_id} with data: {entry_update_data}"
                log.error(error_msg)
                failures.append(f"{tool_id}: Index Update Failed - {error_msg}")
            else:
                index_updates_performed += 1
                # IMPORTANT: Reload index data *after* a successful update
                # to ensure subsequent checks use the updated state, especially for nested structures.
                raw_index_data = tool_index_handler.get_raw_index_data()

    # --- Final Assertion ---
    # Save index explicitly at the end (the handler fixture might also do this) - REMOVED as handler should manage saves
    # tool_index_handler.save_if_dirty()

    if failures:
        fail_msg = f"Baseline checks failed for {len(failures)} sequence(s):\n" + "\\n".join(f"- {f}" for f in failures)
        pytest.fail(fail_msg, pytrace=False)
    else:
        log.info(
            f"All {len(MANAGED_COMMAND_SEQUENCES)} baseline checks passed. {index_updates_performed} index update(s) performed."
        )
