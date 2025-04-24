# FILE: tests/test_tool_defs/test_ensure_txt_baselines_exist.py
"""
Orchestrates the discovery, reconciliation, and baseline generation/verification
for managed tools.
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
import concurrent.futures
from typing import Tuple, Dict, Any, List, Optional, Set
import warnings

# --- Import New Components (Assume standard imports work) ---
from zeroth_law.dev_scripts.config_reader import load_tool_lists_from_toml
from zeroth_law.dev_scripts.environment_scanner import get_executables_from_env
from zeroth_law.dev_scripts.tools_dir_scanner import get_tool_dirs
from zeroth_law.dev_scripts.tool_reconciler import reconcile_tools, ToolStatus
from zeroth_law.dev_scripts.subcommand_discoverer import get_subcommands_from_json
from zeroth_law.dev_scripts.sequence_generator import generate_sequences_for_tool
from zeroth_law.dev_scripts.baseline_generator import (
    generate_or_verify_baseline,
    BaselineStatus as GeneratorBaselineStatus,
)
from .conftest import command_sequence_to_id  # Import from local conftest
from src.zeroth_law.lib.tool_index_handler import ToolIndexHandler
from src.zeroth_law.dev_scripts.reconciliation_logic import perform_tool_reconciliation, ReconciliationError

# Import test fixtures if needed (WORKSPACE_ROOT, TOOLS_DIR, etc.)
# Assuming these are provided by the root conftest.py

# Setup logging
log = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO) # Configure globally or in pytest.ini

# Constants
MAX_WORKERS = os.cpu_count() or 4

# --- REMOVE Old get_managed_sequences and related logic ---
# (The old function and the global MANAGED_COMMAND_SEQUENCES calculation are removed)


# --- Worker Function for Baseline Management (Modified) ---
def _manage_single_baseline_worker(
    command_sequence: Tuple[str, ...], workspace_root: Path, tools_dir: Path
) -> Dict[str, Any]:
    """Worker function to process a single command sequence baseline using baseline_manager."""
    tool_id = command_sequence_to_id(command_sequence)
    result_data = {"tool_id": tool_id, "command_sequence": command_sequence}
    base_tools_dir_for_worker = tools_dir  # Pass the specific tools dir

    try:
        # Call the refactored baseline manager function
        status, calculated_crc_hex, timestamp = generate_or_verify_baseline(
            " ".join(command_sequence), root_dir=base_tools_dir_for_worker
        )

        result_data["status_code"] = status
        result_data["status"] = status.name
        result_data["calculated_crc"] = calculated_crc_hex
        result_data["timestamp"] = timestamp

        # Post-generation verification (TXT existence)
        if status in [GeneratorBaselineStatus.CAPTURE_SUCCESS, GeneratorBaselineStatus.UP_TO_DATE]:
            tool_name = command_sequence[0]
            tool_dir_path = tools_dir / tool_name
            txt_file = tool_dir_path / f"{tool_id}.txt"
            if not txt_file.is_file():
                result_data["status"] = "ERROR_TXT_MISSING_POST_RUN"
                result_data["error_message"] = f"TXT file missing after baseline manager ran: {txt_file}"
                log.error(f"[{tool_id}] {result_data['error_message']}")
            else:
                log.info(f"[{tool_id}] Baseline worker completed ({status.name}). CRC: {calculated_crc_hex or 'N/A'}")
        elif status != GeneratorBaselineStatus.CAPTURE_SUCCESS:
            log.error(f"[{tool_id}] Baseline worker reported failure status: {status.name}")
            result_data["error_message"] = f"Baseline management failed with status {status.name}"

    except Exception as e:
        log.exception(f"[{tool_id}] Unexpected error in baseline worker: {e}")
        result_data["status"] = "ERROR_UNEXPECTED_WORKER"
        result_data["error_message"] = f"Unexpected worker error: {e}"

    return result_data


# --- Main Orchestrating Test Function (Refactored) ---
def test_tool_discovery_reconciliation_and_baselines(WORKSPACE_ROOT: Path, TOOLS_DIR: Path):
    """Discovers, reconciles tools, and generates/verifies baselines for managed sequences."""

    log.info("=== Starting Tool Discovery & Reconciliation Phase ===")
    config_path = WORKSPACE_ROOT / "pyproject.toml"

    # 1. Gather Inputs
    try:
        whitelist, blacklist = load_tool_lists_from_toml(config_path)
        log.info(f"Loaded whitelist ({len(whitelist)}) and blacklist ({len(blacklist)}) from {config_path.name}")
    except FileNotFoundError:
        pytest.fail(f"Configuration file not found: {config_path}")
    except (toml.TomlDecodeError, ValueError, IOError) as e:
        pytest.fail(f"Error loading configuration from {config_path}: {e}")

    env_tools = get_executables_from_env()
    log.info(f"Found {len(env_tools)} potential executables in environment.")

    dir_tools = get_tool_dirs(TOOLS_DIR)
    log.info(f"Found {len(dir_tools)} tool directories in {TOOLS_DIR.relative_to(WORKSPACE_ROOT)}.")

    # 2. Reconcile Tools
    reconciliation_results = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)

    # 3. Report Reconciliation Errors and Identify Managed Tools
    errors = []
    managed_tools_for_sequencing: Set[str] = set()

    for tool, status in reconciliation_results.items():
        if status == ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR:
            errors.append(
                f"Error: Tool '{tool}' is blacklisted but has a directory in {TOOLS_DIR.relative_to(WORKSPACE_ROOT)}."
            )
        elif status == ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR:
            errors.append(
                f"Error: Tool '{tool}' has a directory in {TOOLS_DIR.relative_to(WORKSPACE_ROOT)} but is not in whitelist or blacklist."
            )
        elif status == ToolStatus.ERROR_MISSING_WHITELISTED:
            errors.append(
                f"Error: Tool '{tool}' is whitelisted but not found in environment or {TOOLS_DIR.relative_to(WORKSPACE_ROOT)}."
            )
        elif status == ToolStatus.NEW_ENV_TOOL:
            # Log new tools found in env but don't treat as error for this test
            log.warning(
                f"Discovered new potential tool in environment: '{tool}'. Add to whitelist or blacklist in {config_path.name}."
            )
        elif status in [ToolStatus.MANAGED_OK, ToolStatus.MANAGED_MISSING_ENV, ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR]:
            # These statuses indicate tools that require further processing (sequence generation, baseline checks)
            managed_tools_for_sequencing.add(tool)

    if errors:
        pytest.fail("Reconciliation Errors Found:\n" + "\n".join(errors), pytrace=False)

    log.info(f"Identified {len(managed_tools_for_sequencing)} tools for sequence generation and baseline checks.")
    if not managed_tools_for_sequencing:
        pytest.skip("No managed tools identified for baseline processing.")

    # 4. Generate All Sequences for Managed Tools
    all_managed_sequences: List[Tuple[str, ...]] = []
    for tool_name in sorted(list(managed_tools_for_sequencing)):
        tool_json_path = TOOLS_DIR / tool_name / f"{tool_name}.json"
        subcommands = get_subcommands_from_json(tool_json_path)
        # Pass the overall blacklist to filter sequences
        sequences = generate_sequences_for_tool(tool_name, subcommands, blacklist)
        all_managed_sequences.extend(sequences)

    log.info(f"Generated a total of {len(all_managed_sequences)} command sequences across all managed tools.")
    if not all_managed_sequences:
        pytest.skip("No command sequences generated for managed tools.")

    # --- Pass sequences to the existing concurrent baseline check logic ---
    log.info(f"=== Starting Concurrent Baseline Checks for {len(all_managed_sequences)} Sequences ===")
    start_time = time.monotonic()
    baseline_results = []
    futures = []

    # Use ThreadPoolExecutor for I/O-bound tasks (running subprocesses, file ops)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for command_parts in all_managed_sequences:
            if not command_parts:
                continue  # Should not happen with new generator, but keep safeguard
            futures.append(executor.submit(_manage_single_baseline_worker, command_parts, WORKSPACE_ROOT, TOOLS_DIR))

        # Optional: Add tqdm progress bar if installed
        try:
            from tqdm import tqdm

            futures_iterator = tqdm(
                concurrent.futures.as_completed(futures), total=len(futures), desc="Checking Baselines"
            )
        except ImportError:
            log.info("tqdm not installed, skipping progress bar.")
            futures_iterator = concurrent.futures.as_completed(futures)

        for future in futures_iterator:
            try:
                result = future.result()
                baseline_results.append(result)
            except Exception as exc:
                # Log errors from the future itself (though worker should catch most)
                log.error(f"Error retrieving result from baseline worker future: {exc}")
                # You might want to create a dummy error result here
                # to ensure it gets counted as a failure later.
                baseline_results.append(
                    {"tool_id": "unknown_future_error", "status": "ERROR_FUTURE_EXCEPTION", "error_message": str(exc)}
                )

    end_time = time.monotonic()
    log.info(f"Concurrent baseline checks completed in {end_time - start_time:.2f} seconds.")

    # 5. Aggregate and Report Baseline Check Results
    failures = []
    success_count = 0
    for result in baseline_results:
        status = result.get("status", "ERROR_UNKNOWN_WORKER_STATE")
        tool_id = result.get("tool_id", "unknown")
        if status not in [GeneratorBaselineStatus.CAPTURE_SUCCESS.name, GeneratorBaselineStatus.UP_TO_DATE.name]:
            error_msg = result.get("error_message", f"Worker failed with status {status}")
            failures.append(f" - {tool_id}: {error_msg}")
        else:
            success_count += 1

    log.info(f"Baseline Check Summary: Success = {success_count}, Failures = {len(failures)}")

    if failures:
        fail_summary = "\n".join(failures)
        pytest.fail(
            f"Baseline generation/verification failed for {len(failures)} sequence(s):\n{fail_summary}", pytrace=False
        )

    log.info("All baseline checks passed.")


# Note: The tests for CRC consistency and schema validation should be handled
# in their respective files (test_txt_json_consistency.py, test_json_schema_validation.py)
# They will need modification to get the list of sequences generated here,
# potentially by using a session-scoped fixture or recalculating.


def test_ensure_baselines_and_index_updated(
    MANAGED_COMMAND_SEQUENCES: List[Tuple[str, ...]],
    tool_index_handler: ToolIndexHandler,
    TOOLS_DIR: Path,  # Assuming this fixture provides the correct baseline root
    WORKSPACE_ROOT: Path,
):
    """Test that generates/verifies baselines and updates the index."""
    log.info(f"Starting baseline verification/generation for {len(MANAGED_COMMAND_SEQUENCES)} sequences...")
    if not MANAGED_COMMAND_SEQUENCES:
        pytest.skip("No managed command sequences found to test baselines.")

    updates_made = False
    failures = []

    for sequence_tuple in MANAGED_COMMAND_SEQUENCES:
        sequence_str = " ".join(sequence_tuple)
        tool_id = command_sequence_to_id(sequence_tuple)
        log.debug(f"Processing sequence: {sequence_str} (ID: {tool_id})")

        # Use the imported baseline generator function
        # Pass TOOLS_DIR as the root_dir where baselines should be written/checked
        gen_status, calc_crc, check_time = generate_or_verify_baseline(sequence_str, root_dir=TOOLS_DIR)

        if gen_status not in (GeneratorBaselineStatus.CAPTURE_SUCCESS, GeneratorBaselineStatus.UP_TO_DATE):
            # Handle generation/verification failures
            failures.append(
                f"Baseline generation/verification failed for '{sequence_str}' with status {gen_status.name}"
            )
            continue  # Skip index update if generation failed

        if calc_crc is None or check_time is None:
            failures.append(f"Baseline generation succeeded for '{sequence_str}' but CRC or timestamp was None.")
            continue

        # --- Index Update Logic --- #
        # This logic was previously assumed to be in manage_baseline_for_sequence
        try:
            # Get current entry using the handler
            raw_data = tool_index_handler.get_raw_index_data()
            current_entry = get_index_entry(raw_data, sequence_tuple)  # Assumes get_index_entry is available
            stored_crc = current_entry.get("crc") if current_entry else None

            entry_update_data = {"checked_timestamp": check_time}
            needs_index_update = False

            if stored_crc != calc_crc:
                log.info(f"Index update needed for {tool_id}: Stored CRC '{stored_crc}', New CRC '{calc_crc}'.")
                entry_update_data["crc"] = calc_crc
                entry_update_data["updated_timestamp"] = check_time
                needs_index_update = True
            else:
                log.debug(f"Index CRC matches for {tool_id}. Updating checked_timestamp only.")
                # checked_timestamp already in entry_update_data

            if needs_index_update:
                # Use the handler to update the entry
                if tool_index_handler.update_entry(sequence_tuple, entry_update_data):
                    log.info(f"Successfully updated index for {tool_id}.")
                    updates_made = True
                else:
                    failures.append(f"Failed to update index entry for '{sequence_str}' via handler.")
            else:
                # Even if CRC matches, update checked_timestamp via handler if necessary (handler might optimize this)
                if not tool_index_handler.update_entry(sequence_tuple, entry_update_data):
                    log.warning(f"Failed to update checked_timestamp for '{sequence_str}' via handler.")

        except Exception as e:
            log.exception(f"Unexpected error during index update for '{sequence_str}': {e}")
            failures.append(f"Index update process failed for '{sequence_str}': {e}")

    # --- Assertions and Warnings --- #
    if failures:
        pytest.fail("Baseline/Index update failures occurred:\n" + "\n".join(failures), pytrace=False)

    if updates_made:
        warnings.warn("One or more baselines/index entries were updated. Review changes.", pytest.PytestWarning)
    else:
        log.info("All baselines and index entries appear up-to-date.")


# --- Utility function placeholder (might be needed by tests above) ---
# This needs to be imported from somewhere reliable (e.g., tool_index_utils?)
# Or defined here if truly local.
# def get_index_entry(index_data: Dict, command_sequence: Tuple[str, ...]) -> Optional[Dict]:
#     log.warning("Using placeholder get_index_entry")
#     return index_data.get("_".join(command_sequence))
