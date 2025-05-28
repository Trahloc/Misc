# FILE: src/zeroth_law/subcommands/tools/sync/_process_command_sequence.py
"""Helper function for processing a single command sequence in parallel."""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import structlog

# --- Import project modules --- #
# Relative path needs adjustment (add one more dot)
from ....lib.tooling.baseline_generator import (
    generate_or_verify_ground_truth_txt,
    BaselineStatus,
)
from ....dev_scripts.tool_index_utils import get_index_entry
from ....lib.tool_path_utils import (
    command_sequence_to_filepath,
    command_sequence_to_id,
)

log = structlog.get_logger()


def _process_command_sequence(
    command_sequence: Tuple[str, ...],
    tool_defs_dir: Path,
    project_root: Path,
    container_name: str,
    initial_index_data: Dict[str, Any],
    force: bool,
    since_timestamp: Optional[float],
    ground_truth_txt_skip_hours: int,
    executable_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Processes a single command sequence (ground truth gen, skeleton check, prep update data)."""
    log.debug(f"--->>> Worker thread processing: {command_sequence_to_id(command_sequence)}")

    command_id = command_sequence_to_id(command_sequence)
    result: Dict[str, Any] = {
        "command_sequence": command_sequence,
        "status": None,  # Will be BaselineStatus or similar indicator
        "calculated_crc": None,
        "check_timestamp": None,
        "error_message": None,
        "skipped": False,
    }
    log.info(f"Starting processing for: {command_id}")

    # Define paths early for dry-run logging
    relative_json_path, relative_baseline_path = command_sequence_to_filepath(command_sequence)
    json_file_path = tool_defs_dir / relative_json_path
    baseline_file_path = tool_defs_dir / relative_baseline_path

    # ADDED LOG: Verify the constructed baseline path
    log.info(f"Constructed baseline file path: {baseline_file_path}")

    try:
        # --- Restore getting index entry --- #
        current_index_entry = get_index_entry(initial_index_data, command_sequence)

        # --- Ensure baseline directory exists --- #
        try:
            baseline_file_path.parent.mkdir(parents=True, exist_ok=True)
            log.debug(f"Ensured baseline directory exists: {baseline_file_path.parent}")
        except OSError as mkdir_e:
            log.error(f"Failed to create baseline directory {baseline_file_path.parent}: {mkdir_e}")
            result["error_message"] = f"Failed to create baseline directory: {mkdir_e}"
            result["status"] = BaselineStatus.FAILED_WRITE_TXT  # Use appropriate error status
            # Skip the rest of the processing for this sequence
            raise mkdir_e  # Raise to be caught by outer exception handler

        # --- ADD DEBUG LOG --- Check if baseline file exists *before* calling generator
        log.debug(
            f"Checking existence before baseline gen: {baseline_file_path}. Exists? {baseline_file_path.exists()}"
        )

        # --- Restore call to baseline generator with all args --- #
        status_enum, calculated_crc, check_timestamp = generate_or_verify_ground_truth_txt(
            command_sequence=command_sequence,
            container_name=container_name,
            project_root=project_root,
            index_entry=current_index_entry,
            force=force,
            since_timestamp=since_timestamp,
            output_capture_path=baseline_file_path,
            executable_command_override=executable_override,
        )

        result["calculated_crc"] = calculated_crc
        result["check_timestamp"] = check_timestamp
        result["status"] = status_enum  # Store the actual or simulated status

        if status_enum in {
            BaselineStatus.UP_TO_DATE,
            BaselineStatus.UPDATED,
            BaselineStatus.CAPTURE_SUCCESS,
        }:
            if calculated_crc is None:  # Changed condition: CRC should exist on success
                result["error_message"] = (
                    f"Ground truth TXT generation reported success status ({status_enum.name}) "
                    f"but failed to calculate CRC for {' '.join(command_sequence)}."
                )
                log.error(result["error_message"])
                # Update status to reflect the failure despite initial report
                result["status"] = BaselineStatus.FAILED_CAPTURE  # Or a new CRC error status?
            # else: # CRC is valid, store it (already done above)
            #    pass
        elif status_enum not in {BaselineStatus.UP_TO_DATE}:  # Check if it failed or skipped
            # Only log error if it actually failed, not just UP_TO_DATE
            result["error_message"] = (
                f"Ground truth TXT generation failed for {' '.join(command_sequence)} with status: {status_enum.name}"
            )
            log.error(result["error_message"])

        # --- Prepare update_data based on status --- #
        # Only include CRC if the baseline was actually generated/updated or capture succeeded.
        # For UP_TO_DATE/SKIPPED, rely on the CRC already in the index (or None if new).
        if status_enum in {BaselineStatus.UPDATED, BaselineStatus.CAPTURE_SUCCESS}:
            update_data = {
                "crc": calculated_crc,
                "baseline_file": str(relative_baseline_path),
                "checked_timestamp": check_timestamp,
                "updated_timestamp": check_timestamp,  # Use check time as update time
                "json_definition_file": str(relative_json_path),  # Store relative path
            }
        elif status_enum == BaselineStatus.UP_TO_DATE:
            # Only update the checked timestamp if it was truly up-to-date
            update_data = {
                "checked_timestamp": check_timestamp,
                # DO NOT include crc, baseline_file, or updated_timestamp
                "json_definition_file": str(relative_json_path),  # Store relative path
            }
        else:  # SKIPPED, FAILED, or other error statuses
            update_data = {  # Still update checked time even on failure/skip
                "checked_timestamp": check_timestamp,
                # DO NOT include crc, baseline_file, or updated_timestamp
                "json_definition_file": str(relative_json_path),  # Store relative path
            }

    except Exception as e:
        err_msg = f"Unexpected error processing {command_id}: {e}"
        log.exception(err_msg)
        result["error_message"] = err_msg
        result["status"] = BaselineStatus.UNEXPECTED_ERROR

    log.info(
        f"Finished processing for: {command_id} with status: {result.get('status', 'UNKNOWN')} {'(Skipped)' if result.get('skipped') else ''}"
    )
    return result
