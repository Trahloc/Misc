# FILE: src/zeroth_law/subcommands/tools/sync.py
"""Implements the 'zlt tools sync' subcommand."""

import click
import structlog
import time
import sys
import os

# import shutil # Keep if needed by sync()
# import itertools # Keep if needed by sync()
# import subprocess # Keep if needed by sync()
# import hashlib # Keep if needed by sync()
# import logging # Keep if needed by sync()
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional, Set

# from concurrent.futures import ThreadPoolExecutor, as_completed, Future # Keep if needed?
# import os # Keep if needed?
# import json as json_lib # Keep if needed?
# from ...common.config_loader import load_config # Keep if needed?
from ...common.logging_utils import setup_structlog_logging  # Correct import

# from ...utils.subprocess_utils import run_subprocess_no_check  # Keep if needed?

# === Imports from NEW Helper Modules (using _sync directory) ===
from ._sync._get_container_name import _get_container_name
from ._sync._start_podman_runner import _start_podman_runner
from ._sync._stop_podman_runner import _stop_podman_runner
from ._sync._reconcile_and_prune import _reconcile_and_prune
from ._sync._identify_target_tools import _identify_target_tools
from ._sync._generate_and_filter_sequences import _generate_and_filter_sequences
from ._sync._run_parallel_baseline_processing import _run_parallel_baseline_processing
from ._sync._update_and_save_index import _update_and_save_index
from ._sync._run_hostility_audit import _run_hostility_audit

# === End NEW Helper Imports ===

# === Imports from OTHER modules (Needed by sync() directly) ===
# Need index loading for setup
from ...dev_scripts.tool_index_utils import load_tool_index  # REMOVE save_tool_index import

# Need ToolStatus for type hints if used directly
from .reconcile import ToolStatus  # Keep if type hints needed in sync()

# Need ReconciliationError for exception handling
from ._reconcile._logic import ReconciliationError

# Need baseline status for type hints if used directly
from ...lib.tooling.baseline_generator import (
    BaselineStatus,
)  # Keep if type hints needed

# Need path utils?
# from ...lib.tool_path_utils import command_sequence_to_id # Only needed by helpers now?

# TODO: [Implement Subcommand Blacklist] Reference TODO H.14 in TODO.md - This module needs to filter command sequences based on resolved hierarchical status.

# --- REMOVED Original Imports (Assume moved to helpers unless needed by sync() directly) --- #
# from .reconcile import ReconciliationError # Check if needed by sync()
# from ...lib.tooling.tool_reconciler import reconcile_tools # Moved to helper
# from ...lib.tooling.tool_reconciler import _get_effective_status # Moved to helper
# from ...common.hierarchical_utils import ParsedHierarchy, check_list_conflicts, get_effective_status, parse_to_nested_dict # Moved to helper?
# from ...lib.tooling.environment_scanner import get_executables_from_env # Moved to helper
# from ...lib.tooling.baseline_generator import generate_or_verify_ground_truth_txt # Moved to helper
# from ...lib.tooling.podman_utils import _prepare_command_for_container # Moved to helper
# from ...lib.tooling.podman_utils import _run_podman_command # Moved to helper
# from ...dev_scripts.tool_index_utils import save_tool_index, get_index_entry, update_index_entry # Moved to helper
# from ...lib.tool_path_utils import command_sequence_to_filepath, calculate_crc32_hex # Moved to helper
# from ...lib.tooling.tools_dir_scanner import scan_for_command_sequences, scan_whitelisted_sequences # Moved to helper

log = structlog.get_logger()

# === REMOVED ALL HELPER FUNCTION DEFINITIONS ===


@click.command("sync")
# @common_options # Apply common options using the decorator - RE-ENABLED -- REMOVE THIS LINE
# Manually add ALL options for debugging - REMOVED -- RESTORE THESE
@click.option(
    "--tool",
    "specific_tools",
    multiple=True,
    help="Sync only specific managed tool(s). Default is all managed tools.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force regeneration of baselines and index updates, ignoring timestamps.",
)
@click.option(
    "--prune",
    is_flag=True,
    help="Remove unmanaged or blacklisted tool directories found locally.",
)
@click.option(
    "--generate",
    "generate_baselines",
    is_flag=True,
    help="Generate ground truth baseline files. Requires Podman.",
)
@click.option(
    "--skip-hours",
    "ground_truth_txt_skip_hours",
    type=int,
    default=7 * 24,  # Default to 1 week
    help="(--check-since-hours) Skip baseline regeneration if checked within this many hours (unless --force). Default: 168 (7 days).",
    show_default=True,
)
@click.option(
    "--update-since-hours",
    type=int,
    default=48,  # Default to 2 days
    help="Issue a warning if baseline changes again within this many hours. Default: 48 (2 days).",
    show_default=True,
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what actions would be taken without actually executing them.",
)
@click.option(
    "--exit-errors",
    type=int,
    default=None,  # No limit by default
    help="Exit sync after this many baseline generation errors (FAILED_CAPTURE).",
    show_default="No limit",
)
@click.option("--debug", is_flag=True, default=False, help="Enable DEBUG level logging for sync.")
# --- Add new audit flag --- #
@click.option(
    "--audit-hostility",
    is_flag=True,
    default=False,
    help="Run commands in read-only mode to detect disallowed write attempts.",
)
# --- End new audit flag --- #
# Add back other necessary options MANUALLY if common_options added them before
# Example: Check zlt_options_definitions.json for verbose, config, quiet, color
# These are typically handled by the main CLI group and accessed via ctx
@click.pass_context
def sync(
    ctx: click.Context,
    # Manually list expected arguments from common_options and sync-specific ones -- REVERT THIS
    # Arguments from common_options (verify these match zlt_options_definitions.json) -- REMOVE
    # verbose: int, # Maps to -v count -- REMOVE
    # Arguments specific to 'sync' that were previously manually defined -- Keep these args
    specific_tools: Tuple[str, ...],
    force: bool,
    prune: bool,
    generate_baselines: bool,
    ground_truth_txt_skip_hours: int,
    update_since_hours: int,
    dry_run: bool,
    exit_errors: Optional[int],
    debug: bool,  # Add debug flag parameter
    audit_hostility: bool,  # Add audit flag parameter
) -> None:
    """Syncs the local tool definitions with the managed tools and generates baselines.

    This function acts as a facade, orchestrating the sync process by calling
    helper functions now located in the ./_sync/ subdirectory.
    """
    start_time = time.time()

    # --- Add NEW Logging Setup --- #
    if debug:
        # Simplest approach for now: reconfigure globally
        global_options = ctx.obj.get("options", {})
        color = global_options.get("color")  # Get color preference if set globally
        setup_structlog_logging("debug", color)
        log.info("DEBUG logging enabled for sync command.")
    # --- End NEW Logging Setup --- #

    # Original start message
    log.info(f"Starting zlt tools sync... (Dry Run: {dry_run}) (Audit: {audit_hostility})")

    # === Initial Setup (Get project_root and config from context) ===
    project_root = ctx.obj.get("project_root")
    if not project_root or not isinstance(project_root, Path):
        ctx.fail("Project root not found or invalid in context.")
    config = ctx.obj.get("CONFIG_DATA")  # Use correct key from cli.py
    if not config or not isinstance(config, dict):
        log.warning("Config not found or invalid in context. Proceeding with empty config?")
        config = {}

    # Derive tool_defs_dir directly
    tool_defs_dir = project_root / "src" / "zeroth_law" / "tools"
    tool_index_path = tool_defs_dir / "tool_index.json"
    # <<< REMOVE generated_outputs_dir definition >>>
    # generated_outputs_dir = project_root / "generated_command_outputs"
    # generated_outputs_dir.mkdir(parents=True, exist_ok=True)

    # === Start Main Logic Try Block ===
    try:
        # === Pre-flight Checks & Setup (Steps 1-3) ===
        # Initialize variables used throughout the function and in finally
        pruned_count = 0
        processed_count = 0
        all_errors: List[str] = []  # Ensure defined early
        exit_code = 0  # Default exit code
        container_name: Optional[str] = None
        podman_setup_successful = False
        current_index_data: Dict[str, Any] = {}  # Initialize index data
        # Initialize reporting counts used in finally block
        updated_count: int = 0
        skipped_count: int = 0

        # === Reconciliation (Moved inside its own try/except) ===
        try:
            log.info("STAGE 1 & 2: Starting tool reconciliation and target identification...")
            (
                reconciliation_results,
                managed_tools_set,
                parsed_whitelist,
                parsed_blacklist,
                prune_errors,
                pruned_count,
            ) = _reconcile_and_prune(project_root, config, tool_defs_dir, prune, dry_run)
        except ReconciliationError as recon_e:
            # Use ctx.fail to exit immediately with error message and code 1
            ctx.fail(str(recon_e))
        # --- End Reconciliation Block ---

        # Add prune errors if any occurred (even if ReconciliationError wasn't raised)
        all_errors.extend(prune_errors)
        if prune_errors:
            log.warning("Errors occurred during pruning. Continuing sync...")

        if not managed_tools_set:
            log.warning("No managed tools identified by reconciliation. Nothing to sync.")
            ctx.exit(0)

        # === Target Identification & Filtering ===
        target_tool_names = _identify_target_tools(specific_tools, reconciliation_results, managed_tools_set)
        if not target_tool_names:
            log.info("No target tools identified. Exiting.")
            ctx.exit(0)

        whitelisted_sequences, _, skipped_blacklist = _generate_and_filter_sequences(
            tool_defs_dir,
            target_tool_names,
            reconciliation_results,
            parsed_whitelist,
            parsed_blacklist,
        )
        if not whitelisted_sequences:
            log.warning("No effectively whitelisted sequences to process. Exiting.")
            ctx.exit(0)

        tasks_to_run = whitelisted_sequences  # Use whitelisted for generation

        # === Load Index (Before Podman setup) ===
        initial_index_data = load_tool_index(tool_index_path)
        current_index_data = initial_index_data.copy()
        log.info("Initial index loaded", index_size=len(initial_index_data))

        # === Podman Setup (Step 5b) === #
        # Container name and setup status are already initialized above
        if generate_baselines and not dry_run:
            log.info("STAGE 3: Setting up Podman runner...")
            # --- Restore Podman Setup Logic --- #
            venv_bin_path = project_root / ".venv" / "bin"
            if not venv_bin_path.is_dir():
                ctx.fail(f"Sync Error: Expected venv bin path not found for Podman setup: {venv_bin_path}")
            container_name = _get_container_name(project_root)
            podman_setup_successful = _start_podman_runner(
                container_name,
                project_root,
                venv_bin_path,
                read_only_app=audit_hostility,  # Use audit flag
            )
            if not podman_setup_successful:
                log.error("Podman runner setup failed. Cannot generate baselines.")
                # Attempt cleanup even if setup failed
                if container_name:
                    try:
                        _stop_podman_runner(container_name)
                    except Exception:
                        pass
                ctx.exit(1)  # Exit if setup fails
            else:
                log.info(f"Podman runner container '{container_name}' started successfully.")
            # --- End Restore Podman Setup --- #

        elif not dry_run:
            log.info("Skipping Podman setup as --generate flag was not provided.")

        # === Initialize variables used in baseline processing outside the conditional block ===
        all_results: List[Dict[str, Any]] = []
        processing_errors: List[str] = []

        # === Run Baseline Processing (Step 5c) ===
        if generate_baselines and podman_setup_successful:
            # Timestamp for --skip-hours logic
            since_timestamp = (
                time.time() - (ground_truth_txt_skip_hours * 3600) if ground_truth_txt_skip_hours > 0 else None
            )

            # === Run Baseline Processing (Step 6) === #
            log.info("STAGE 4: Starting baseline generation...")
            # --- REMOVED INNER TRY/EXCEPT/FINALLY --- #
            sync_max_workers = ctx.obj.get("MAX_WORKERS", os.cpu_count())  # Use ctx.obj
            all_results, processing_errors, processed_count = _run_parallel_baseline_processing(
                tasks_to_run=whitelisted_sequences,
                tool_defs_dir=tool_defs_dir,
                project_root=project_root,
                container_name=container_name,
                index_data=current_index_data,
                force=force,
                since_timestamp=since_timestamp,
                ground_truth_txt_skip_hours=ground_truth_txt_skip_hours,
                max_workers=sync_max_workers,  # Use variable from ctx.obj
                exit_errors_limit=exit_errors,
            )
            # Assign skipped_count from results, not just initialized zero
            skipped_count = sum(1 for r in all_results if r.get("skipped"))  # Correctly count skips
            # Add processing errors to main error list
            if processing_errors:
                all_errors.extend(processing_errors)
                if exit_errors:
                    log.error("Exiting with error code due to baseline generation failures.")
                    exit_code = 1  # Set exit code if limit reached or any error occurred

            log.info(
                "Baseline processing complete",
                results_count=len(all_results),
                errors_count=len(processing_errors),
                skipped_count=skipped_count,
            )

            # === Update and Save Index (Step 7) ===
            # --- DEBUG: Log content of all_results before update --- #
            log.debug(
                "Sync: Before _update_and_save_index", results_count=len(all_results), all_results_data=all_results
            )
            # --- DEBUG: Log the initial index data being passed --- #
            log.debug("Sync: Passing initial_index_data", index_data=current_index_data)
            # --- End DEBUG --- #
            final_index_data, index_errors, updated_count, _ = _update_and_save_index(
                results=all_results,
                initial_index_data=current_index_data,
                tool_index_path=tool_index_path,
                dry_run=dry_run,
            )
            all_errors.extend(index_errors)
            current_index_data = final_index_data
            # --- DEBUG: Log index data AFTER update call --- #
            # log.debug("Sync: After _update_and_save_index",
            #           returned_final_data=final_index_data,
            #           current_index_data=current_index_data)
            # --- End DEBUG --- #

        elif dry_run:
            log.info("[DRY RUN] Skipping baseline generation and index update.")
            processed_count = len(tasks_to_run)  # In dry run, all tasks are considered 'processed' for summary
        else:
            log.info("Skipping baseline generation as --generate was not specified.")
            processed_count = len(tasks_to_run)  # If not generating, all tasks are considered 'processed' for summary

        # === Hostility Audit (Conditional) ===
        if audit_hostility and not dry_run and not all_errors:
            # ... (existing audit logic) ...
            pass  # Placeholder

    except click.exceptions.Exit as e:
        # Allow clean exits initiated by helpers (like ctx.exit(0))
        raise e  # Re-raise for Click to handle
    except ReconciliationError as e:
        # Use ctx.fail to print the error and exit with code 1
        ctx.fail(str(e))
    except Exception as e:
        log.exception(f"Error during main sync logic: {e}")
        all_errors.append(f"Main sync error: {e}")
        exit_code = 1  # Set error exit code for unexpected exceptions
    finally:
        # === Single Finally Block ===
        log.info("Executing main finally block...")
        # === Podman Cleanup ===
        if container_name and podman_setup_successful:
            log.info(f"Attempting to stop and remove Podman container: {container_name}")
            try:
                _stop_podman_runner(container_name)
                log.info(f"Successfully stopped and removed Podman container: {container_name}")
            except Exception as cleanup_e:
                log.exception(f"Error during Podman cleanup: {cleanup_e}")
                # Optionally set exit_code = 1 here if cleanup failure is critical

        # === Final Reporting ===
        end_time = time.time()
        duration = end_time - start_time

        # Ensure counts are accurate even if baseline gen was skipped
        # `processed_count` now reflects total tasks considered.
        # `updated_count` and `skipped_count` come from `_update_and_save_index` or are 0.

        log.info(
            "Sync summary",
            duration_seconds=round(duration, 2),
            processed=processed_count,
            updated=updated_count,
            skipped=skipped_count,
            errors=len(all_errors),
            pruned=(pruned_count if prune else None),
            exit_code=exit_code,  # Log the final intended exit code
        )

        if all_errors:
            log.error("Sync finished with errors:", errors=all_errors)
            exit_code = 1  # Ensure exit code is 1 if any errors occurred
        else:
            log.info("Sync finished successfully.")

        # === Final Exit ===
        # Final exit call using the determined exit_code
        ctx.exit(exit_code)
