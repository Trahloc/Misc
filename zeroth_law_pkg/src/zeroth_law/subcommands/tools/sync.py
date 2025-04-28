# FILE: src/zeroth_law/subcommands/tools/sync.py
"""Implements the 'zlt tools sync' subcommand."""

import click
import logging
import time
import sys
from pathlib import Path
from typing import Tuple, List

# --- Imports from other modules --- #

# Need reconciliation logic to determine managed tools
from .reconcile import _perform_reconciliation_logic, ReconciliationError

# Need baseline generation logic
# TODO: Move baseline_generator to a shared location
from ...lib.tooling.baseline_generator import (
    generate_or_verify_baseline,
    BaselineStatus,
)

# Need ToolIndexHandler and related utils
# TODO: Move ToolIndexHandler and helpers to shared location if not already
# from ...lib.tool_index_handler import ToolIndexHandler # <-- REMOVE THIS
# --- Corrected imports for index utilities --- #
from ...dev_scripts.tool_index_utils import (
    load_tool_index,
    save_tool_index,
    get_index_entry,
    update_index_entry,
)

# --- Updated imports for tool path utils --- #
from ...lib.tool_path_utils import (
    command_sequence_to_filepath,
    command_sequence_to_id,
    calculate_crc32_hex,
)

# Need skeleton creation logic (adapted from conftest)
import json as json_lib  # Alias to avoid conflict

log = logging.getLogger(__name__)


# --- Helper for Skeleton Creation (Adapted from conftest) ---
def _create_skeleton_json_if_missing(json_file_path: Path, command_sequence: tuple[str, ...]) -> bool:
    """Creates a schema-compliant skeleton JSON if it doesn't exist."""
    created = False
    if not json_file_path.exists():
        command_name = command_sequence[0]
        # --- Use imported helper --- #
        command_id = command_sequence_to_id(command_sequence)
        log.info(f"Skeleton Action: Creating skeleton JSON for {command_id} at {json_file_path}")
        skeleton_data = {
            "command": list(command_sequence),
            "description": f"Tool definition for {command_name} (auto-generated skeleton)",
            "usage": f"{command_name} [options] [arguments]",
            "options": [],
            "arguments": [],
            "metadata": {
                "name": command_name,
                "version": None,
                "language": "unknown",
                "categories": [],
                "tags": ["skeleton"],
                "url": "",
                "other": {},
            },
        }
        try:
            json_file_path.parent.mkdir(parents=True, exist_ok=True)
            with json_file_path.open("w", encoding="utf-8") as f:
                json_lib.dump(skeleton_data, f, indent=4)
            log.info(f"Skeleton Action: Successfully created skeleton JSON: {json_file_path}")
            created = True
        except IOError as e:
            log.error(f"Skeleton Action Error: Failed to write skeleton JSON {json_file_path}: {e}")
            # Don't raise here, let sync command report overall failure
    return created


# --- Main Sync Command --- #


@click.command("sync")
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
    "--since",
    help="Only update items not updated since <TIMESPEC> (e.g., '24h', '3d', 'YYYY-MM-DDTHH:MM:SSZ').",
)
@click.pass_context
def sync(ctx: click.Context, specific_tools: Tuple[str, ...], force: bool, since: str | None) -> None:
    """Generates/updates baselines, JSON defs, and index for managed tools."""
    config = ctx.obj["config"]
    project_root = ctx.obj.get("project_root")
    log.info("Starting tool synchronization...")
    exit_code = 0
    sync_errors: List[str] = []
    processed_count = 0
    updated_count = 0
    skeleton_created_count = 0
    skipped_count = 0

    if not project_root:
        log.error("Project root could not be determined. Cannot perform sync.")
        ctx.exit(1)

    # Define paths consistently
    tool_defs_dir = project_root / "src" / "zeroth_law" / "tools"
    generated_outputs_dir = project_root / "generated_command_outputs"
    generated_outputs_dir.mkdir(parents=True, exist_ok=True)  # Ensure baseline dir exists
    tool_index_path = tool_defs_dir / "tool_index.json"

    try:
        # 1. Perform reconciliation to get managed tools
        log.debug("Performing reconciliation to identify managed tools...")
        _, managed_tools_set, _, _, _, _ = _perform_reconciliation_logic(
            project_root_dir=project_root, config_data=config
        )

        if not managed_tools_set:
            log.info("No managed tools identified by reconciliation. Nothing to sync.")
            ctx.exit(0)

        # 2. Filter target tools
        target_tools = managed_tools_set
        if specific_tools:
            target_tools = {tool for tool in specific_tools if tool in managed_tools_set}
            missing_specified = set(specific_tools) - target_tools
            if missing_specified:
                log.warning(f"Specified tools not found in managed set: {missing_specified}")
            if not target_tools:
                log.error("None of the specified tools are in the managed set. Nothing to sync.")
                ctx.exit(1)
        log.info(f"Targeting {len(target_tools)} tools for sync: {sorted(list(target_tools))}")

        # 3. Parse --since (Basic implementation - TODO: Add robust parsing)
        since_timestamp = None
        if since:
            # VERY basic parsing - Needs improvement!
            try:
                if since.endswith("h"):
                    since_timestamp = time.time() - int(since[:-1]) * 3600
                elif since.endswith("d"):
                    since_timestamp = time.time() - int(since[:-1]) * 86400
                else:
                    # Attempt ISO format or epoch?
                    since_timestamp = float(since)  # Basic epoch assumption
                log.info(f"Applying --since filter: {since} (Timestamp > {since_timestamp:.2f})")
            except ValueError:
                log.error(f"Invalid --since format: {since}. Expected format like '24h', '3d', or epoch timestamp.")
                ctx.exit(1)

        # 4. Instantiate ToolIndexHandler --> Load index data directly
        if not tool_index_path.is_file():
            log.warning(f"Tool index file not found at {tool_index_path}, creating empty index.")
            tool_index_path.write_text("{}", encoding="utf-8")
        # handler = ToolIndexHandler(tool_index_path) # <-- REMOVE THIS
        index_data = load_tool_index()  # <-- ADD THIS LINE BACK

        # 5. Iterate and Sync
        for tool_name in sorted(list(target_tools)):
            processed_count += 1
            log.info(f"--- Processing Tool: {tool_name} ---")

            # --- Process Base Command --- #
            base_command_sequence = (tool_name,)
            base_command_id = command_sequence_to_id(base_command_sequence)
            log.debug(f"Processing BASE command: {base_command_id}")

            try:
                # Get paths for base command
                relative_base_json_path, _ = command_sequence_to_filepath(base_command_sequence)
                base_json_file_path = tool_defs_dir / relative_base_json_path

                # Check skip condition for base command
                current_base_entry = get_index_entry(index_data, base_command_sequence)
                should_skip_base = False
                if not force and current_base_entry:
                    last_updated = current_base_entry.get("updated_timestamp", 0.0)
                    if since_timestamp and last_updated <= since_timestamp:
                        log.debug(
                            f"Skipping BASE {base_command_id}: Last updated ({last_updated:.2f}) is not after --since ({since_timestamp:.2f})."
                        )
                        should_skip_base = True
                        skipped_count += 1
                    # Could add other time-based checks here if needed

                if not should_skip_base:
                    # Run Baseline Generation for BASE command
                    log.debug(f"Running baseline generation/verification for BASE {base_command_id}...")
                    base_status_enum, base_calculated_crc, base_check_timestamp = generate_or_verify_baseline(tool_name)

                    if base_status_enum not in {
                        BaselineStatus.UP_TO_DATE,
                        BaselineStatus.UPDATED,
                        BaselineStatus.CAPTURE_SUCCESS,
                    }:
                        err_msg = (
                            f"Baseline generation failed for BASE '{tool_name}' with status: {base_status_enum.name}"
                        )
                        log.error(err_msg)
                        sync_errors.append(err_msg)
                    else:
                        # Ensure Skeleton JSON exists for BASE command
                        created_base_json = _create_skeleton_json_if_missing(base_json_file_path, base_command_sequence)
                        if created_base_json:
                            skeleton_created_count += 1

                        # Update Index Entry for BASE command
                        log.debug(f"Updating index entry for BASE {base_command_id}...")
                        base_baseline_txt_path = tool_defs_dir / tool_name / f"{base_command_id}.txt"
                        relative_base_baseline_path_str = (
                            str(base_baseline_txt_path.relative_to(tool_defs_dir))
                            if base_baseline_txt_path.exists()
                            else None
                        )

                        base_update_data = {
                            "command": list(base_command_sequence),
                            "baseline_file": relative_base_baseline_path_str,
                            "json_definition_file": str(base_json_file_path.relative_to(tool_defs_dir)),
                            "crc": base_calculated_crc,
                            "updated_timestamp": base_check_timestamp if base_check_timestamp else time.time(),
                            "checked_timestamp": base_check_timestamp if base_check_timestamp else time.time(),
                            "source": "zlt_tools_sync",
                        }
                        update_index_entry(index_data, base_command_sequence, base_update_data)
                        log.debug(f"Index update successful for BASE {base_command_id}")
                        if base_status_enum == BaselineStatus.UPDATED or created_base_json:
                            updated_count += 1
            except Exception as e:
                err_msg = f"Unexpected error syncing BASE {base_command_id}: {e}"
                log.exception(err_msg)  # Log traceback
                sync_errors.append(err_msg)

            # --- Process Subcommands (if defined) --- #
            base_definition_data = None
            if base_json_file_path.exists():
                try:
                    with base_json_file_path.open("r", encoding="utf-8") as f_base:
                        base_definition_data = json_lib.load(f_base)
                except Exception as json_e:
                    log.warning(
                        f"Could not load base JSON definition {base_json_file_path} to check for subcommands: {json_e}"
                    )

            if isinstance(base_definition_data, dict) and "subcommands_detail" in base_definition_data:
                subcommands_detail = base_definition_data["subcommands_detail"]
                if isinstance(subcommands_detail, dict):
                    log.info(f"Found {len(subcommands_detail)} subcommands for {tool_name}. Processing...")
                    for sub_key in sorted(subcommands_detail.keys()):
                        log.debug(f"Processing SUBCOMMAND: {tool_name} {sub_key}")
                        sub_command_sequence = (tool_name, sub_key)
                        sub_command_id = command_sequence_to_id(sub_command_sequence)
                        sub_command_sequence_str = f"{tool_name} {sub_key}"

                        try:
                            # Get paths for subcommand
                            relative_sub_json_path, _ = command_sequence_to_filepath(sub_command_sequence)
                            sub_json_file_path = tool_defs_dir / relative_sub_json_path

                            # Check skip condition for subcommand
                            current_sub_entry = get_index_entry(index_data, sub_command_sequence)
                            should_skip_sub = False
                            if not force and current_sub_entry:
                                last_updated_sub = current_sub_entry.get("updated_timestamp", 0.0)
                                if since_timestamp and last_updated_sub <= since_timestamp:
                                    log.debug(
                                        f"Skipping SUBCOMMAND {sub_command_id}: Last updated ({last_updated_sub:.2f}) is not after --since ({since_timestamp:.2f})."
                                    )
                                    should_skip_sub = True
                                    skipped_count += 1
                                # Could add other time-based checks here

                            if not should_skip_sub:
                                # Run Baseline Generation for SUBCOMMAND
                                log.debug(
                                    f"Running baseline generation/verification for SUBCOMMAND {sub_command_id}..."
                                )
                                sub_status_enum, sub_calculated_crc, sub_check_timestamp = generate_or_verify_baseline(
                                    sub_command_sequence_str
                                )

                                if sub_status_enum not in {
                                    BaselineStatus.UP_TO_DATE,
                                    BaselineStatus.UPDATED,
                                    BaselineStatus.CAPTURE_SUCCESS,
                                }:
                                    err_msg = f"Baseline generation failed for SUBCOMMAND '{sub_command_sequence_str}' with status: {sub_status_enum.name}"
                                    log.error(err_msg)
                                    sync_errors.append(err_msg)
                                else:
                                    # Ensure Skeleton JSON exists for SUBCOMMAND
                                    created_sub_json = _create_skeleton_json_if_missing(
                                        sub_json_file_path, sub_command_sequence
                                    )
                                    if created_sub_json:
                                        skeleton_created_count += 1

                                    # Update Index Entry for SUBCOMMAND
                                    log.debug(f"Updating index entry for SUBCOMMAND {sub_command_id}...")
                                    sub_baseline_txt_path = tool_defs_dir / tool_name / f"{sub_command_id}.txt"
                                    relative_sub_baseline_path_str = (
                                        str(sub_baseline_txt_path.relative_to(tool_defs_dir))
                                        if sub_baseline_txt_path.exists()
                                        else None
                                    )

                                    sub_update_data = {
                                        "command": list(sub_command_sequence),
                                        "baseline_file": relative_sub_baseline_path_str,
                                        "json_definition_file": str(sub_json_file_path.relative_to(tool_defs_dir)),
                                        "crc": sub_calculated_crc,
                                        "updated_timestamp": sub_check_timestamp
                                        if sub_check_timestamp
                                        else time.time(),
                                        "checked_timestamp": sub_check_timestamp
                                        if sub_check_timestamp
                                        else time.time(),
                                        "source": "zlt_tools_sync",
                                    }
                                    update_index_entry(index_data, sub_command_sequence, sub_update_data)
                                    log.debug(f"Index update successful for SUBCOMMAND {sub_command_id}")
                                    if sub_status_enum == BaselineStatus.UPDATED or created_sub_json:
                                        updated_count += 1  # Still counts towards overall updates
                        except Exception as sub_e:
                            err_msg = f"Unexpected error syncing SUBCOMMAND {sub_command_id}: {sub_e}"
                            log.exception(err_msg)  # Log traceback
                            sync_errors.append(err_msg)
                else:
                    log.debug(f"No 'subcommands_detail' dictionary found in {base_json_file_path} for {tool_name}.")
            else:
                log.debug(
                    f"Base definition {base_json_file_path} not found or not a dictionary for {tool_name}, cannot check for subcommands."
                )

        # 6. Save Index
        log.info("Saving updated tool index...")
        if not save_tool_index(index_data):
            log.error("Failed to save tool index.")
            exit_code = 1

        # 7. Report Summary
        log.info("-- Sync Summary --")
        log.info(f"Tools Targeted:   {len(target_tools)}")
        log.info(f"Tools Processed:  {processed_count}")
        log.info(f"Baselines/Index Updated: {updated_count}")
        log.info(f"Skeletons Created:{skeleton_created_count}")
        log.info(f"Skipped (recent): {skipped_count}")
        log.info(f"Errors:           {len(sync_errors)}")
        if sync_errors:
            log.error("Sync completed with errors:")
            for err in sync_errors:
                log.error(f"- {err}")
            exit_code = 1
        else:
            log.info("Synchronization completed successfully.")

    except ReconciliationError as e:
        log.error(f"Sync failed during initial reconciliation: {e}")
        exit_code = 2
    except Exception as e:
        log.exception("An unexpected error occurred during the sync command.")
        exit_code = 3

    ctx.exit(exit_code)
