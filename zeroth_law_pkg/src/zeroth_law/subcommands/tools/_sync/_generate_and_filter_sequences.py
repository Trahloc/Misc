# FILE: src/zeroth_law/subcommands/tools/sync/_generate_and_filter_sequences.py
"""Helper function for Stage 4: Generating and filtering command sequences."""

from pathlib import Path
from typing import Tuple, List, Dict, Set
import structlog

# --- Import project modules --- #
# Relative path needs adjustment (add one more dot)
from ..reconcile import ToolStatus  # Import from sibling command
from ....lib.tooling.tools_dir_scanner import scan_for_command_sequences
from ....lib.tooling.tool_reconciler import _get_effective_status
from ....common.hierarchical_utils import ParsedHierarchy

log = structlog.get_logger()


def _generate_and_filter_sequences(
    tool_defs_dir: Path,
    target_tool_names: Set[str],
    reconciliation_results: Dict[str, ToolStatus],
    parsed_whitelist: ParsedHierarchy,
    parsed_blacklist: ParsedHierarchy,
) -> Tuple[List[Tuple[str, ...]], int, int]:
    """STAGE 4: Generates sequences from existing files AND synthesizes defaults for missing defs.

    Args:
        tool_defs_dir: Path to the tool definitions directory.
        target_tool_names: Set of tool names to focus on.
        reconciliation_results: Dictionary mapping tool names to their ToolStatus.
        parsed_whitelist: Parsed whitelist hierarchy.
        parsed_blacklist: Parsed blacklist hierarchy.

    Returns:
        Tuple containing the list of sequences to run, count of sequences
        skipped by scope (target tools), count skipped by blacklist.
    """
    log.info("STAGE 4: Generating and filtering command sequences...")
    final_tasks_to_run: List[Tuple[str, ...]] = []
    skipped_by_blacklist_count = 0
    skipped_by_scope_count = 0
    sequences_found_on_disk: List[Tuple[str, ...]] = []
    synthesized_sequences: List[Tuple[str, ...]] = []

    # 1. Scan for sequences defined by existing *.json files on disk
    try:
        sequences_found_on_disk = scan_for_command_sequences(tool_defs_dir)
        log.info(f"Found {len(sequences_found_on_disk)} potential command sequences defined on disk.")
    except Exception as e:
        log.error(f"Error scanning for command sequences: {e}")
        raise  # Re-raise to stop the sync process

    # --- Process sequences FOUND ON DISK FIRST (Filter by target and whitelist/blacklist) --- #
    valid_disk_sequences = []
    for sequence in sequences_found_on_disk:
        if not sequence or sequence[0] not in target_tool_names:
            skipped_by_scope_count += 1
            continue  # Skip if not targeted

        effective_status = _get_effective_status(list(sequence), parsed_whitelist, parsed_blacklist)
        if effective_status == "whitelist":
            valid_disk_sequences.append(sequence)
        else:
            skipped_by_blacklist_count += 1
            log.debug(f"Skipping disk sequence due to non-whitelist status: {sequence} (Effective: {effective_status})")

    log.info(f"Identified {len(valid_disk_sequences)} valid sequences from disk definitions after filtering.")
    final_tasks_to_run.extend(valid_disk_sequences)

    # --- Now synthesize defaults ONLY for targeted tools MISSING from valid disk sequences --- #
    tools_with_disk_defs = {seq[0] for seq in valid_disk_sequences}

    for tool_name in target_tool_names:
        # Check if the tool already has *any* valid sequence from disk
        if tool_name in tools_with_disk_defs:
            continue  # Skip synthesis if any definition was already found and processed

        # If no disk def was found, check reconciliation status for synthesis trigger
        status = reconciliation_results.get(tool_name)
        if status == ToolStatus.WHITELISTED_NO_DEFS:
            # Synthesize a task for the base tool name only.
            default_sequence = (tool_name,)
            # Double check whitelist status for the base tool itself (should be whitelist)
            base_status = _get_effective_status(list(default_sequence), parsed_whitelist, parsed_blacklist)
            if base_status == "whitelist":
                log.info(
                    f"Synthesizing default task '{' '.join(default_sequence)}' for tool '{tool_name}' (status: WHITELISTED_NO_DEFS, no valid disk defs found)."
                )
                synthesized_sequences.append(default_sequence)
            else:
                # This case should be rare if reconciliation logic is correct
                log.warning(
                    f"Skipping synthesis for '{tool_name}' because base command itself is not whitelisted (Status: {base_status})"
                )
                skipped_by_blacklist_count += 1  # Count it as skipped
        # else: No need to synthesize for other statuses

    # Add synthesized sequences to the final list
    final_tasks_to_run.extend(synthesized_sequences)
    log.info(f"Added {len(synthesized_sequences)} synthesized default sequences.")

    # Recalculate skipped_by_scope based ONLY on the initial disk scan results
    log.info(f"Final task list size after filtering and synthesis: {len(final_tasks_to_run)}")
    if skipped_by_scope_count > 0:
        log.info(f"Skipped {skipped_by_scope_count} sequences found on disk due to --tool scoping.")
    if skipped_by_blacklist_count > 0:
        log.info(
            f"Skipped {skipped_by_blacklist_count} sequences due to blacklist/unmanaged status (incl. disk & potential synthesis)."
        )

    return final_tasks_to_run, skipped_by_scope_count, skipped_by_blacklist_count
