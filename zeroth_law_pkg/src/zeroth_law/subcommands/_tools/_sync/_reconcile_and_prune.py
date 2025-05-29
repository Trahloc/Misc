# FILE: src/zeroth_law/subcommands/tools/sync/_reconcile_and_prune.py
"""Helper function for Stage 2: Reconciliation and pruning."""

import shutil
from pathlib import Path
from typing import Tuple, List, Dict, Set
import structlog

# --- Import project modules --- #
# Relative path needs adjustment (add one more dot)
from ..reconcile import ToolStatus  # Import from sibling command
from ....lib.tooling.tool_reconciler import reconcile_tools
from ....common.hierarchical_utils import ParsedHierarchy
from ....lib.tooling.environment_scanner import get_executables_from_env
from ....lib.tooling.tools_dir_scanner import scan_for_command_sequences

log = structlog.get_logger()


def _reconcile_and_prune(
    project_root: Path, config: Dict, tool_defs_dir: Path, prune: bool, dry_run: bool
) -> Tuple[Dict[str, ToolStatus], Set[str], ParsedHierarchy, ParsedHierarchy, List[str], int]:
    """STAGE 2: Performs reconciliation and optional pruning.

    Returns: Tuple containing reconciliation results, managed tools set,
             parsed whitelist/blacklist, sync errors, and prune count.
    """
    log.info("STAGE 2: Performing reconciliation and optional pruning...")
    sync_errors: List[str] = []
    pruned_count = 0

    # --- Call the original _perform_reconciliation_logic from reconcile.py --- #
    # This needs updating to use the modified reconcile_tools logic internally
    # For now, we adapt the call here to match the *old* signature of reconcile_tools
    # by scanning for sequences first.

    # 1. Get required inputs for the NEW reconcile_tools signature
    env_tools = set()  # Need to get this from environment scan
    defined_sequences = set()  # Need to get this from directory scan
    parsed_whitelist = config.get("parsed_whitelist", {})
    parsed_blacklist = config.get("parsed_blacklist", {})

    try:
        # Get env tools (moved logic from _load_initial_config_and_state)
        venv_path = project_root / ".venv"
        venv_bin_path = venv_path / "bin"
        if venv_bin_path.is_dir():
            env_tools = get_executables_from_env(venv_bin_path)
        else:
            log.warning(f"Venv bin path {venv_bin_path} not found during reconcile stage.")

        # Scan for defined sequences
        if not tool_defs_dir.is_dir():
            log.warning(f"Tool definitions directory not found: {tool_defs_dir}")
            # If dir doesn't exist, treat as empty sequences
        else:
            try:
                # Use the scanner that finds ALL sequences, not just whitelisted ones
                defined_sequences = set(scan_for_command_sequences(tool_defs_dir))
                log.info(f"Found {len(defined_sequences)} defined command sequences in {tool_defs_dir}.")
            except Exception as scan_e:
                log.error(f"Error scanning for command sequences: {scan_e}")
                sync_errors.append(f"Sequence Scan Error: {scan_e}")
                # Continue with empty set?

    except Exception as setup_e:
        log.error(f"Error getting env tools or scanning sequences: {setup_e}")
        sync_errors.append(f"Reconcile Setup Error: {setup_e}")
        # Return empty/error state if setup fails badly
        return {}, set(), {}, {}, sync_errors, 0

    # 2. Call the UPDATED reconcile_tools function
    try:
        reconciliation_results = reconcile_tools(
            env_tools=env_tools,
            defined_sequences=defined_sequences,
            whitelist=parsed_whitelist,
            blacklist=parsed_blacklist,
        )
    except Exception as recon_e:
        log.error(f"Error during tool reconciliation: {recon_e}")
        sync_errors.append(f"Reconciliation Logic Error: {recon_e}")
        return {}, set(), parsed_whitelist, parsed_blacklist, sync_errors, 0

    # --- DEBUG: Log reconciliation results --- #
    log.debug("Reconciliation results received", results=reconciliation_results)
    # --- END DEBUG --- #

    # === Add check for reconciliation errors ===
    reconciliation_errors = {
        tool: status for tool, status in reconciliation_results.items() if status.name.startswith("ERROR")
    }
    if reconciliation_errors:
        # Log the specific errors
        for tool, status in reconciliation_errors.items():
            log.error(f"Reconciliation error for '{tool}': {status.name}")
        # Raise an exception to be caught by the main sync function
        error_summary = ", ".join([f"{tool}({status.name})" for tool, status in reconciliation_errors.items()])
        # Use the existing ReconciliationError if suitable, or define a new one
        # Assuming ReconciliationError exists and can take a message
        from ....subcommands._tools._reconcile._logic import ReconciliationError

        raise ReconciliationError(f"Reconciliation found errors: {error_summary}")
    # === End error check ===

    # 3. Determine Managed Tools based on NEW logic (whitelisted AND has defs OR needs defs)
    managed_tools_set = {
        tool
        for tool, status in reconciliation_results.items()
        if status
        in {
            ToolStatus.MANAGED_OK,
            ToolStatus.MANAGED_MISSING_ENV,
            ToolStatus.WHITELISTED_NO_DEFS,
        }
    }
    log.info(f"Identified {len(managed_tools_set)} managed tools after reconciliation.")

    # 4. Pruning Logic (needs update based on NEW statuses)
    if prune:
        # Prune based on ERROR_BLACKLISTED_HAS_DEFS or ERROR_ORPHAN_HAS_DEFS
        dirs_to_prune = {
            tool
            for tool, status in reconciliation_results.items()
            if status in {ToolStatus.ERROR_BLACKLISTED_HAS_DEFS, ToolStatus.ERROR_ORPHAN_HAS_DEFS}
        }

        if dirs_to_prune:
            log.warning(
                f"--prune specified: {len(dirs_to_prune)} directories with definitions marked for removal: {sorted(list(dirs_to_prune))}"
            )
            for tool_name in dirs_to_prune:
                dir_path = tool_defs_dir / tool_name
                if dir_path.is_dir():  # Double-check it exists
                    try:
                        if dry_run:
                            log.info(f"[DRY RUN] Would prune directory: {dir_path}")
                        else:
                            log.info(f"Pruning directory: {dir_path}")
                            shutil.rmtree(dir_path)
                            pruned_count += 1
                    except OSError as e:
                        err_msg = f"Error pruning directory {dir_path}: {e}"
                        log.error(err_msg)
                        sync_errors.append(err_msg)
                else:
                    # This shouldn't happen if has_defs was true, but log just in case
                    log.warning(f"Requested prune for {tool_name}, but directory {dir_path} not found unexpectedly.")
        else:
            log.info(
                "--prune specified, but no directories found matching prune criteria (BLACKLISTED_HAS_DEFS or ORPHAN_HAS_DEFS)."
            )

    # 5. Collect final errors/warnings from reconciliation results (optional, if needed)
    # errors_found = any(status.name.startswith("ERROR") for status in reconciliation_results.values())

    log.info("STAGE 2: Reconciliation and pruning complete.")
    return (
        reconciliation_results,
        managed_tools_set,
        parsed_whitelist,
        parsed_blacklist,
        sync_errors,
        pruned_count,
    )
