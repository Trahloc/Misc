# FILE: src/zeroth_law/subcommands/tools/sync/_update_and_save_index.py
"""Helper function for Stage 6: Updating and saving the tool index."""

from pathlib import Path
from typing import Tuple, List, Dict, Any
import structlog

# --- Import project modules --- #
# Relative path needs adjustment (add one more dot)
from ....lib.tooling.baseline_generator import BaselineStatus
from ....dev_scripts.tool_index_utils import update_index_entry, save_tool_index
from ....lib.tool_path_utils import command_sequence_to_id

log = structlog.get_logger()


def _update_and_save_index(
    results: List[Dict[str, Any]],
    initial_index_data: Dict[str, Any],  # Pass initial data to update
    tool_index_path: Path,
    dry_run: bool,
) -> Tuple[Dict[str, Any], List[str], int, int]:
    """STAGE 6: Processes results and updates/saves the tool index.

    Returns: Tuple containing final index data, list of index update errors,
             count of updated items, count of skipped items.
    """
    log.info("STAGE 6: Processing results and updating index...")
    final_index_data = initial_index_data.copy()  # Work on a copy
    index_errors: List[str] = []
    updated_count = 0
    skipped_count = 0

    for result in results:
        if result.get("skipped"):
            skipped_count += 1
            continue

        status = result.get("status")
        error_message = result.get("error_message")  # Check for processing error
        command_sequence = result["command_sequence"]
        update_data = result.get("update_data")

        # Only update index if baseline processing didn't fail and no processing error occurred
        is_success_status = isinstance(status, BaselineStatus) and status in {
            BaselineStatus.UP_TO_DATE,
            BaselineStatus.UPDATED,
            BaselineStatus.CAPTURE_SUCCESS,
        }

        if update_data and is_success_status and not error_message:
            try:
                update_index_entry(final_index_data, command_sequence, update_data)
                # Count as updated if status was UPDATED or CAPTURE_SUCCESS (no longer check skeleton_created)
                if status in {BaselineStatus.UPDATED, BaselineStatus.CAPTURE_SUCCESS}:
                    updated_count += 1
            except Exception as index_e:
                err_msg = f"Failed to update index for {command_sequence_to_id(command_sequence)}: {index_e}"
                log.exception(err_msg)
                index_errors.append(err_msg)
        elif error_message:
            log.debug(f"Skipping index update for {command_sequence_to_id(command_sequence)} due to processing error.")
        elif not is_success_status:
            log.debug(
                f"Skipping index update for {command_sequence_to_id(command_sequence)} due to failure status: {status}"
            )

    # Save Final Index
    if dry_run:
        log.info(f"[DRY RUN] Would save updated tool index with {len(final_index_data)} entries to {tool_index_path}")
    else:
        log.info(f"Saving updated tool index with {len(final_index_data)} entries...")
        if not save_tool_index(final_index_data, tool_index_path=tool_index_path):
            log.error("Failed to save final tool index.")
            index_errors.append("Failed to save final tool index.")

    log.info("STAGE 6: Index update complete.")
    # Return updated count (includes skeleton creations) and skipped count
    return final_index_data, index_errors, updated_count, skipped_count
