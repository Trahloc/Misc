# FILE: src/zeroth_law/subcommands/tools/sync/_run_hostility_audit.py
"""Helper function for the Hostility Audit workflow."""

import click
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import structlog

# --- Import project modules --- #
# Relative path needs adjustment (add one more dot)
from ....lib.tooling.podman_utils import _execute_for_hostility_check

# --- Import sibling helpers --- #
from ._reconcile_and_prune import _reconcile_and_prune
from ._generate_and_filter_sequences import _generate_and_filter_sequences
from ._get_container_name import _get_container_name
from ._start_podman_runner import _start_podman_runner
from ._stop_podman_runner import _stop_podman_runner
from ....lib.tool_path_utils import command_sequence_to_id

log = structlog.get_logger()


def _run_hostility_audit(
    ctx: click.Context,
    project_root: Path,
    config: Dict[str, Any],
    tool_defs_dir: Path,
    venv_bin_path: Path,
) -> Tuple[List[str], List[str]]:
    """Runs all whitelisted sequences in RO mode to check for hostility."""
    log.info("Starting Hostility Audit (Read-Only Execution)...")
    hostile_sequences: List[str] = []
    other_errors: List[str] = []

    # 1. Get sequences (simplified Steps 1-5, assuming config/dirs are okay for audit)
    # We might want more robust error handling here in a real implementation
    try:
        (
            reconciliation_results,  # Needs to be captured, might be needed below
            managed_tools_set,
            parsed_whitelist,
            parsed_blacklist,
            _,
            _,
        ) = _reconcile_and_prune(
            project_root=project_root,
            config=config,
            tool_defs_dir=tool_defs_dir,
            prune=False,
            dry_run=True,
        )
        if not managed_tools_set:
            log.warning("Hostility Audit: No managed tools found.")
            return [], []
        target_tool_names = managed_tools_set  # Audit all managed tools
        whitelisted_sequences, _, _ = _generate_and_filter_sequences(
            tool_defs_dir=tool_defs_dir,
            target_tool_names=target_tool_names,
            reconciliation_results=reconciliation_results,  # Pass captured results
            parsed_whitelist=parsed_whitelist,
            parsed_blacklist=parsed_blacklist,
        )
        if not whitelisted_sequences:
            log.warning("Hostility Audit: No effectively whitelisted sequences found.")
            return [], []
        log.info(f"Hostility Audit: Identified {len(whitelisted_sequences)} sequences to check.")
    except Exception as setup_e:
        log.error(f"Hostility Audit failed during setup: {setup_e}")
        return [], [f"Audit Setup Error: {setup_e}"]

    # 2. Start RO container
    container_name: Optional[str] = None
    audit_container_started = False
    try:
        container_name = _get_container_name(project_root)
        audit_container_started = _start_podman_runner(
            container_name=container_name,
            project_root=project_root,
            venv_path=venv_bin_path,
            read_only_app=True,  # <<< START READ-ONLY >>>
        )
        if not audit_container_started:
            log.error("Hostility Audit: Failed to start read-only container.")
            return [], ["Failed to start RO container"]

        # 3. Run checks in parallel (or sequentially for simplicity first?)
        # Let's use parallel for consistency
        log.info(f"Running hostility checks for {len(whitelisted_sequences)} sequences...")
        max_workers = config.get("max_sync_workers", 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sequence = {
                executor.submit(
                    _execute_for_hostility_check,
                    sequence,
                    container_name,
                    project_root,
                ): sequence
                for sequence in whitelisted_sequences
            }

            for future in as_completed(future_to_sequence):
                sequence = future_to_sequence[future]
                command_id = command_sequence_to_id(sequence)
                try:
                    is_safe, error_details = future.result()
                    if not is_safe:
                        log.error(
                            f"Hostility Audit FAILED for sequence: {command_id}",
                            details=error_details,
                        )
                        hostile_sequences.append(command_id)
                        if error_details:
                            other_errors.append(f"{command_id}: {error_details}")
                        # --- FAIL FAST --- #
                        log.warning("Detected hostile sequence. Stopping audit early.")
                        # Optionally: Try to cancel remaining futures? (Difficult with ThreadPoolExecutor)
                        # executor.shutdown(wait=False, cancel_futures=True) # Not available in stdlib
                        break  # Exit the loop immediately
                        # --- END FAIL FAST --- #
                except Exception as check_exc:
                    log.exception(f"Hostility Audit: Error checking sequence {command_id}: {check_exc}")
                    other_errors.append(f"Error checking {command_id}: {check_exc}")
                    # --- FAIL FAST on Exception too? --- #
                    log.error("Encountered exception during audit. Stopping early.")
                    break  # Also stop on unexpected errors
                    # --- END FAIL FAST --- #

    except Exception as audit_e:
        log.exception(f"Hostility Audit failed during execution: {audit_e}")
        other_errors.append(f"Audit Execution Error: {audit_e}")
    finally:
        # 4. Stop container
        if container_name and audit_container_started:
            _stop_podman_runner(container_name)

    log.info("Hostility Audit finished.")
    return hostile_sequences, other_errors
