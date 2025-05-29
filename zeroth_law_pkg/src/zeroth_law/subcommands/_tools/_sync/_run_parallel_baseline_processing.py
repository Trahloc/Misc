# FILE: src/zeroth_law/subcommands/tools/sync/_run_parallel_baseline_processing.py
"""Helper function for Stage 5: Running baseline processing in parallel."""

from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import structlog

# --- Import project modules --- #
# Relative path needs adjustment (add one more dot)
from ....lib.tooling.baseline_generator import BaselineStatus
from ....lib.tool_path_utils import command_sequence_to_id
from ._process_command_sequence import (
    _process_command_sequence,
)  # Import sibling helper

log = structlog.get_logger()


def _run_parallel_baseline_processing(
    tasks_to_run: List[Tuple[str, ...]],
    tool_defs_dir: Path,
    project_root: Path,
    container_name: str,
    index_data: Dict[str, Any],
    force: bool,
    since_timestamp: Optional[float],
    ground_truth_txt_skip_hours: int,
    max_workers: int,
    exit_errors_limit: Optional[int],
) -> Tuple[List[Dict[str, Any]], List[str], int]:
    """STAGE 5: Executes the baseline processing tasks in parallel.

    Returns: Tuple containing list of results, list of sync errors,
             and count of processed tasks.
    """
    log.info(f"STAGE 5: Starting parallel baseline processing ({len(tasks_to_run)} tasks)... ")
    results: List[Dict[str, Any]] = []
    sync_errors: List[str] = []
    processed_count = 0
    error_count = 0  # Track errors specifically for exit_errors_limit

    # --- Run Sequentially ALWAYS for Debugging --- # REMOVED
    # log.warning("DEBUG: Running baseline processing sequentially...")
    # for sequence in tasks_to_run:
    #     command_id = command_sequence_to_id(sequence)
    #     try:
    #         result = _process_command_sequence(
    #             sequence,
    #             tool_defs_dir,
    #             project_root,
    #             container_name,
    #             index_data,
    #             force,
    #             since_timestamp,
    #             ground_truth_txt_skip_hours,
    #         )
    #         results.append(result)
    #         processed_count += 1
    #         is_error_status = result.get("error_message") or (
    #             isinstance(result.get("status"), BaselineStatus)
    #             and result["status"]
    #             not in {
    #                 BaselineStatus.UP_TO_DATE,
    #                 BaselineStatus.UPDATED,
    #                 BaselineStatus.CAPTURE_SUCCESS,
    #             }
    #         )
    #         if is_error_status:
    #             error_count += 1
    #             log.warning(
    #                 f"Error encountered for {command_id} (Total errors: {error_count}) status: {result.get('status')}"
    #             )
    #             if exit_errors_limit is not None and error_count >= exit_errors_limit:
    #                 err_msg = f"Reached error limit ({exit_errors_limit}) processing {command_id}."
    #                 log.error(err_msg)
    #                 sync_errors.append(err_msg)
    #                 raise RuntimeError(err_msg)
    #
    #     except Exception as exc:
    #         if isinstance(exc, RuntimeError) and f"Reached error limit ({exit_errors_limit})" in str(exc):
    #             raise exc
    #         else:
    #             err_msg = f"Task for {command_id} generated unexpected exception: {exc}"
    #             log.exception(err_msg)
    #             sync_errors.append(err_msg)
    #             processed_count += 1  # Count as processed even if exception
    #             error_count += 1  # Count exception as an error
    #             if exit_errors_limit is not None and error_count >= exit_errors_limit:
    #                 err_msg_limit = f"Reached error limit ({exit_errors_limit}) due to exception in {command_id}."
    #                 log.error(err_msg_limit)
    #                 sync_errors.append(err_msg_limit)
    #                 raise RuntimeError(err_msg_limit)

    # --- Original Parallel Code (Restored) --- #
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_sequence = {
            executor.submit(
                _process_command_sequence,
                sequence,
                tool_defs_dir,
                project_root,
                container_name,
                index_data,
                force,
                since_timestamp,
                ground_truth_txt_skip_hours,
            ): sequence
            for sequence in tasks_to_run
        }
        log.info(f"Submitted {len(future_to_sequence)} tasks to ThreadPoolExecutor (max_workers={max_workers})...")

        for future in as_completed(future_to_sequence):
            sequence = future_to_sequence[future]
            command_id = command_sequence_to_id(sequence)
            try:
                result = future.result()
                results.append(result)
                processed_count += 1
                # Check if this result represents an error for the exit limit
                is_error_status = result.get("error_message") or (
                    isinstance(result.get("status"), BaselineStatus)
                    and result["status"]
                    not in {
                        BaselineStatus.UP_TO_DATE,
                        BaselineStatus.UPDATED,
                        BaselineStatus.CAPTURE_SUCCESS,
                    }
                )
                if is_error_status:
                    error_count += 1
                    log.warning(
                        f"Error encountered for {command_id} (Total errors: {error_count}) status: {result.get('status')}"
                    )
                    if exit_errors_limit is not None and error_count >= exit_errors_limit:
                        err_msg = f"Reached error limit ({exit_errors_limit}) processing {command_id}."
                        log.error(err_msg)
                        sync_errors.append(err_msg)
                        # Raise exception instead of break to exit early
                        raise RuntimeError(err_msg)
                        # break  # Stop processing further completed futures - REMOVED

            except Exception as exc:
                # Catch the specific RuntimeError we raised or any other future exception
                if isinstance(exc, RuntimeError) and f"Reached error limit ({exit_errors_limit})" in str(exc):
                    # Re-raise the specific error limit exception to stop processing
                    raise exc
                else:
                    # Handle other exceptions from the future/task itself
                    err_msg = f"Task for {command_id} generated unexpected exception: {exc}"
                    log.exception(err_msg)
                    sync_errors.append(err_msg)
                    processed_count += 1  # Count as processed even if exception
                    error_count += 1  # Count exception as an error
                    if exit_errors_limit is not None and error_count >= exit_errors_limit:
                        err_msg_limit = f"Reached error limit ({exit_errors_limit}) due to exception in {command_id}."
                        log.error(err_msg_limit)
                        sync_errors.append(err_msg_limit)
                        # Raise exception instead of break
                        raise RuntimeError(err_msg_limit)
                        # break - REMOVED
    # --- End Original Parallel Code ---

    # log.info(f"STAGE 5: Sequential processing finished. Processed {processed_count} tasks.")
    log.info(f"STAGE 5: Parallel processing finished. Processed {processed_count} tasks.")
    return results, sync_errors, processed_count
