# FILE: src/zeroth_law/subcommands/tools/sync.py
"""Implements the 'zlt tools sync' subcommand."""

import click
import logging
import time
import sys
import shutil
import itertools
import subprocess
import hashlib
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

# Define spinner characters
SPINNER = itertools.cycle(["-", "\\\\", "|", "/"])

# --- Podman Helper Functions ---


def _run_podman_command(args: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Helper to run a podman command."""
    command = ["podman"] + args
    log.debug(f"Executing Podman command: {' '.join(command)}")
    try:
        return subprocess.run(
            command,
            check=check,
            capture_output=capture,
            text=True,  # Decode output as text
            encoding="utf-8",
        )
    except FileNotFoundError:
        log.error("`podman` command not found. Please ensure Podman is installed and in your PATH.")
        raise
    except subprocess.CalledProcessError as e:
        log.error(f"Podman command failed: {' '.join(command)}")
        log.error(f"Stderr: {e.stderr}")
        raise


def _get_container_name(project_root: Path) -> str:
    """Generate a deterministic container name for the project."""
    # Use a short hash of the project root path
    project_hash = hashlib.sha1(str(project_root).encode()).hexdigest()[:12]
    return f"zlt-baseline-runner-{project_hash}"


def _start_podman_runner(container_name: str, project_root: Path, venv_path: Path) -> bool:
    """Starts the podman container for baseline generation."""
    log.info(f"Attempting to start Podman baseline runner: {container_name}")
    # Ensure venv exists
    if not venv_path.is_dir():
        log.error(f"Virtual environment not found at: {venv_path}")
        return False

    # Check if container exists, remove if it does (ensures clean start)
    try:
        result = _run_podman_command(["inspect", container_name], check=False)
        if result.returncode == 0:
            log.warning(f"Container {container_name} already exists. Stopping and removing.")
            _run_podman_command(["stop", container_name], check=False)
            _run_podman_command(["rm", container_name], check=False)
    except Exception as e:
        log.error(f"Error checking/removing existing container {container_name}: {e}")
        return False

    # TODO: Determine python version/image automatically? For now, hardcode python:3.13-slim
    # This MUST match the python version used in the project's venv
    python_image = "docker.io/library/python:3.13-slim"
    log.info(f"Using Podman image: {python_image}")

    try:
        # Mount project root and venv read-only
        # Mount project root to allow running scripts from within the project
        # Mount venv to provide access to installed tools
        _run_podman_command(
            [
                "run",
                "--rm",  # Automatically remove container on exit (though we also stop/rm explicitly)
                "-d",  # Run detached
                "--name",
                container_name,
                f"--volume={str(project_root.resolve())}:/app:ro",  # Mount project root
                f"--volume={str(venv_path.resolve())}:/venv:ro",  # Mount venv
                python_image,
                "sleep",
                "infinity",  # Keep container running
            ]
        )
        log.info(f"Successfully started Podman container: {container_name}")
        return True
    except Exception as e:
        log.error(f"Failed to start Podman container {container_name}: {e}")
        return False


def _stop_podman_runner(container_name: str) -> None:
    """Stops and removes the podman container."""
    log.info(f"Stopping and removing Podman container: {container_name}")
    try:
        # Use --ignore to avoid errors if container is already gone
        _run_podman_command(["stop", "--ignore", container_name], check=False)
        _run_podman_command(["rm", "--ignore", container_name], check=False)
        log.info(f"Podman container {container_name} stopped and removed.")
    except Exception as e:
        # Log error but don't prevent script exit
        log.error(f"Error stopping/removing Podman container {container_name}: {e}")


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
@click.option(
    "--prune",
    is_flag=True,
    help="Remove unmanaged or blacklisted tool directories found locally.",
)
@click.pass_context
def sync(ctx: click.Context, specific_tools: Tuple[str, ...], force: bool, since: str | None, prune: bool) -> None:
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
    pruned_count = 0

    if not project_root:
        log.error("Project root could not be determined. Cannot perform sync.")
        ctx.exit(1)

    # --- Podman Setup ---
    container_name = _get_container_name(project_root)
    venv_path = project_root / ".venv"  # Assuming standard venv location
    ctx.obj["podman_container_name"] = None  # Initialize in context

    # Define paths consistently
    tool_defs_dir = project_root / "src" / "zeroth_law" / "tools"
    generated_outputs_dir = project_root / "generated_command_outputs"
    generated_outputs_dir.mkdir(parents=True, exist_ok=True)
    tool_index_path = tool_defs_dir / "tool_index.json"

    try:
        # Start Podman runner BEFORE any baseline generation might occur
        if not _start_podman_runner(container_name, project_root, venv_path):
            log.error("Failed to initialize Podman runner. Aborting sync.")
            ctx.exit(1)
        ctx.obj["podman_container_name"] = container_name  # Store name for baseline generator

        # 1. Perform reconciliation to get managed tools
        log.debug("Performing reconciliation to identify managed tools...")
        reconciliation_results, managed_tools_set, blacklist, errors, warnings, has_errors = (
            _perform_reconciliation_logic(project_root_dir=project_root, config_data=config)
        )

        if not managed_tools_set and not prune:
            log.info("No managed tools identified by reconciliation. Nothing to sync or prune.")
            ctx.exit(0)

        # 1b. Identify directories to prune (if requested)
        dirs_to_prune = set()
        if prune:
            # Find tools marked as blacklisted or orphan in reconciliation results
            blacklisted_present = {
                tool
                for tool, status in reconciliation_results.items()
                if status == ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR
            }
            orphaned_present = {
                tool
                for tool, status in reconciliation_results.items()
                if status == ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR
            }
            dirs_to_prune = blacklisted_present.union(orphaned_present)

            if dirs_to_prune:
                log.warning(
                    f"--prune specified: The following {len(dirs_to_prune)} directories will be removed: {sorted(list(dirs_to_prune))}"
                )
                # Perform pruning BEFORE main sync loop
                for tool_name in dirs_to_prune:
                    dir_path = tool_defs_dir / tool_name
                    if dir_path.is_dir():  # Check if it actually exists
                        try:
                            log.info(f"Pruning directory: {dir_path}")
                            shutil.rmtree(dir_path)
                            pruned_count += 1
                        except OSError as e:
                            err_msg = f"Error pruning directory {dir_path}: {e}"
                            log.error(err_msg)
                            sync_errors.append(err_msg)
                    else:
                        log.warning(f"Requested prune for {tool_name}, but directory {dir_path} not found.")
            else:
                log.info("--prune specified, but no unmanaged or blacklisted directories found to remove.")

        # Exit if errors occurred during pruning
        if sync_errors:
            log.error("Errors occurred during pruning phase. Aborting sync.")
            exit_code = 1
            # Jump to summary reporting
            raise Exception("Pruning errors occurred")  # Use exception to jump to finally/summary

        if not managed_tools_set:
            log.info("No managed tools identified. Pruning (if requested) is complete. Exiting.")
            # Save index even if no tools were synced, in case pruning happened
            if not save_tool_index(load_tool_index()):  # Reload index in case it changed
                log.error("Failed to save tool index after potential pruning.")
                exit_code = 1
            ctx.exit(exit_code)

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
        total_tools = len(target_tools)  # Add counter
        for i, tool_name in enumerate(sorted(list(target_tools)), 1):  # Add counter
            processed_count += 1
            # Add progress message here - Initial print for the tool
            # click.echo(f"[{i}/{total_tools}] Processing Tool: {tool_name}...", file=sys.stderr, nl=False)
            current_spinner = next(SPINNER)
            base_msg = f"[{i}/{total_tools}] {current_spinner} Processing Tool: {tool_name}"
            click.echo(f"{base_msg}...", file=sys.stderr, nl=False)

            log.info(f"--- Processing Tool: {tool_name} [{i}/{total_tools}] ---")

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
                    base_status_enum, base_calculated_crc, base_check_timestamp = generate_or_verify_baseline(
                        tool_name,
                        root_dir=tool_defs_dir,  # Pass tool_defs_dir as root? Or project_root? Check generator usage
                        ctx=ctx,  # Pass context
                    )

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
                        # Update spinner for subcommand
                        current_spinner = next(SPINNER)
                        sub_msg = f"{base_msg} -> {sub_key}"
                        # Use \r to overwrite previous line part
                        click.echo(
                            f"\r[{i}/{total_tools}] {current_spinner} Processing {tool_name} -> {sub_key}... ".ljust(
                                80
                            ),
                            file=sys.stderr,
                            nl=False,
                        )

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
                                    sub_command_sequence_str,
                                    root_dir=tool_defs_dir,  # Pass tool_defs_dir as root? Or project_root? Check generator usage
                                    ctx=ctx,  # Pass context
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
                    log.debug(
                        f"Base definition {base_json_file_path} not found or not a dictionary for {tool_name}, cannot check for subcommands."
                    )
            else:
                log.debug(
                    f"Base definition {base_json_file_path} not found or not a dictionary for {tool_name}, cannot check for subcommands."
                )

            # After processing a tool and its subcommands, clear the line and move to the next
            click.echo("\r" + " " * 80 + "\r", file=sys.stderr, nl=False)  # Clear the line
            click.echo(
                f"[{i}/{total_tools}] ✓ Finished: {tool_name}", file=sys.stderr
            )  # Print final status for the tool

        # 6. Save Index
        log.info("Saving updated tool index...")
        if not save_tool_index(index_data):
            log.error("Failed to save tool index.")
            exit_code = 1

        # 7. Report Summary
        log.info("-- Sync Summary --")
        log.info(f"Tools Targeted:   {len(target_tools)}")
        log.info(f"Tools Processed:  {processed_count}")
        log.info(f"Baseline/Index Updated: {updated_count}")
        log.info(f"Skeletons Created:  {skeleton_created_count}")
        log.info(f"Skipped (recent):   {skipped_count}")
        log.info(f"Errors:             {len(sync_errors)}")
        if prune:
            log.info(f"Directories Pruned: {pruned_count}")
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
        # Check if it was the pruning exception
        if "Pruning errors occurred" not in str(e):
            log.exception("An unexpected error occurred during the sync command.")
            exit_code = 3
        # Otherwise, exit_code should already be set to 1 from pruning block
    finally:
        # --- Podman Cleanup ---
        if ctx.obj.get("podman_container_name"):
            _stop_podman_runner(ctx.obj["podman_container_name"])

    ctx.exit(exit_code)
