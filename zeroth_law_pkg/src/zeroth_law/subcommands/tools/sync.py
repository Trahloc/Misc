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
from ...lib.tool_index_handler import ToolIndexHandler

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

        # 4. Instantiate ToolIndexHandler
        if not tool_index_path.is_file():
            log.warning(f"Tool index file not found at {tool_index_path}, creating empty index.")
            tool_index_path.write_text("{}", encoding="utf-8")
        handler = ToolIndexHandler(tool_index_path)

        # 5. Iterate and Sync
        for tool_name in sorted(list(target_tools)):
            processed_count += 1
            log.debug(f"Processing tool: {tool_name}")
            # TODO: Handle tool:subcommand hierarchy if tool_name contains ':'
            command_sequence = (tool_name,)  # Assuming simple tool name for now
            # --- Use imported helper --- #
            command_id = command_sequence_to_id(command_sequence)

            try:
                # Get paths
                # --- Use imported helper --- #
                relative_json_path, _ = command_sequence_to_filepath(command_sequence)
                json_file_path = tool_defs_dir / relative_json_path
                # Baseline path is handled internally by baseline_generator

                # Check skip condition
                current_entry = handler.get_entry(command_sequence)
                if not force and current_entry:
                    last_updated = current_entry.get("updated_timestamp", 0.0)
                    if since_timestamp and last_updated <= since_timestamp:
                        log.debug(
                            f"Skipping {command_id}: Last updated ({last_updated:.2f}) is not after --since ({since_timestamp:.2f})."
                        )
                        skipped_count += 1
                        continue
                    # Could add other time-based checks here if needed

                # --- Run Baseline Generation/Verification --- #
                log.debug(f"Running baseline generation/verification for {command_id}...")
                baseline_status = generate_or_verify_baseline(tool_name)

                if baseline_status not in {
                    BaselineStatus.UP_TO_DATE,
                    BaselineStatus.UPDATED,
                }:
                    err_msg = f"Baseline generation failed for '{tool_name}' with status: {baseline_status.name}"
                    log.error(err_msg)
                    sync_errors.append(err_msg)
                    continue  # Skip index update if baseline failed

                # --- Ensure Skeleton JSON Exists --- #
                created_json = _create_skeleton_json_if_missing(json_file_path, command_sequence)
                if created_json:
                    skeleton_created_count += 1

                # --- Update Index Entry (Adapted from conftest) --- #
                log.debug(f"Updating index entry for {command_id}...")
                # Re-fetch entry in case skeleton was created
                current_entry = handler.get_entry(command_sequence)
                relative_baseline_path = handler.get_baseline_path_for_sequence(
                    command_sequence
                )  # Get path from handler
                if not relative_baseline_path:
                    log.error(f"Failed to get baseline path from index for {command_id} after baseline generation.")
                    sync_errors.append(f"Index inconsistency for {command_id}: baseline path missing.")
                    continue

                if current_entry is None:
                    log.info(f"Index Update: No existing entry for {command_id}, creating default.")
                    current_entry = {
                        "command": list(command_sequence),
                        "baseline_file": str(relative_baseline_path),  # Use path from index
                        "json_definition_file": str(json_file_path.relative_to(tool_defs_dir)),
                        "crc": None,
                        "updated_timestamp": 0.0,
                        "checked_timestamp": 0.0,  # Baseline check covers this?
                        "source": "zlt_tools_sync",
                    }
                else:
                    # Ensure paths are up-to-date
                    current_entry["baseline_file"] = str(relative_baseline_path)
                    current_entry["json_definition_file"] = str(json_file_path.relative_to(tool_defs_dir))

                # Update timestamp
                update_time = time.time()
                current_entry["updated_timestamp"] = update_time
                # Update CRC from baseline generator (already stored in index by it)
                current_entry["crc"] = handler.get_crc_for_sequence(command_sequence)

                handler.update_entry(command_sequence, current_entry)
                log.debug(f"Index update successful for {command_id}")
                if baseline_status == BaselineStatus.UPDATED or created_json:  # Count if baseline OR JSON changed
                    updated_count += 1

            except Exception as e:
                log.exception(f"Unexpected error syncing tool {tool_name}: {e}")
                sync_errors.append(f"Unexpected error for {tool_name}: {e}")

        # 6. Save Index
        log.info("Saving tool index...")
        handler.save_index()

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
