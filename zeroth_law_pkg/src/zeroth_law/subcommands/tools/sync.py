# FILE: src/zeroth_law/subcommands/tools/sync.py
"""Implements the 'zlt tools sync' subcommand."""

import click
import structlog
import time
import sys
import shutil
import itertools
import subprocess
import hashlib
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Imports from other modules --- #

# Need reconciliation logic to determine managed tools
from .reconcile import _perform_reconciliation_logic, ReconciliationError, ToolStatus

# Need baseline generation logic
# TODO: Move baseline_generator to a shared location
from ...lib.tooling.baseline_generator import (
    generate_or_verify_ground_truth_txt,
    BaselineStatus,
)

# Import the Podman helper function
from ...lib.tooling.podman_utils import _prepare_command_for_container  # noqa: F401 - Used indirectly by baseline_generator?

# --- Import _run_podman_command as well --- #
from ...lib.tooling.podman_utils import _run_podman_command

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

log = structlog.get_logger()

# Define spinner characters
# SPINNER = itertools.cycle(["-", "\\\\", "|", "/"])

# --- Podman Helper Functions ---

# REMOVED _run_podman_command - Moved to podman_utils.py


def _get_container_name(project_root: Path) -> str:
    """Generate a deterministic container name for the project."""
    # Use a short hash of the project root path
    project_hash = hashlib.sha1(str(project_root).encode()).hexdigest()[:12]
    return f"zlt-baseline-runner-{project_hash}"


def _start_podman_runner(container_name: str, project_root: Path, venv_path: Path) -> bool:
    """Starts the podman container, creates internal venv, and installs deps."""
    log.info(f"Attempting to start Podman baseline runner: {container_name}")

    # --- Ensure host venv exists (to get uv) --- #
    host_uv_path = venv_path / "bin" / "uv"
    if not host_uv_path.is_file():
        log.error(f"Host `uv` executable not found at: {host_uv_path}. Cannot proceed.")
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

    python_image = "docker.io/library/python:3.13-slim"
    log.info(f"Using Podman image: {python_image}")

    try:
        # Mount project root read-only.
        _run_podman_command(
            [
                "run",
                "--rm",
                "-d",
                "--name",
                container_name,
                f"--volume={str(project_root.resolve())}:/app:ro",  # Mount project root read-only
                # Venv mount removed
                python_image,
                "sleep",
                "infinity",
            ]
        )
        log.info(f"Successfully executed podman run command for {container_name}. Container warming up...")
        time.sleep(3)  # Give container a moment to start

        # --- Create internal venv --- #
        log.info(f"Creating virtual environment inside {container_name} at /venv...")
        _run_podman_command(["exec", container_name, "python", "-m", "venv", "/venv"], check=True)
        log.info("Internal venv created.")

        # --- Install dependencies using host uv targeting internal venv --- #
        # We need the requirements file path relative to the project root
        # Assuming standard locations like requirements.txt or using pyproject.toml
        # For simplicity, let's assume pyproject.toml is the source via uv pip sync
        log.info(f"Installing dependencies from /app/pyproject.toml into internal /venv using host uv...")
        # Command needs to execute uv from host mount to target internal python
        # This is tricky. Let's try executing uv directly inside.
        # First, check if uv exists in the base image (it might)
        uv_check_result = _run_podman_command(["exec", container_name, "which", "uv"], check=False, capture=True)
        internal_uv_path = "uv"  # Assume it's on PATH
        if uv_check_result.returncode != 0:
            log.warning("uv not found in base image PATH. Trying /app/.venv/bin/uv from mount...")
            # This requires /app mount, which we have. Use absolute path from host perspective mapped to container.
            # This is getting complex. Let's INSTALL uv first using pip if needed.
            log.info("Installing uv inside the container using pip...")
            _run_podman_command(["exec", container_name, "/venv/bin/pip", "install", "uv"], check=True)
            log.info("`uv` installed inside container.")
            internal_uv_path = "/venv/bin/uv"
        else:
            log.info("`uv` found in container PATH.")
            internal_uv_path = uv_check_result.stdout.strip() if uv_check_result.stdout else "uv"

        # Now run uv pip sync using the container's uv and python
        sync_cmd = [
            "exec",
            "-w",
            "/app",  # Run from project root within container
            container_name,
            internal_uv_path,  # Use the uv inside the container
            "pip",
            "sync",
            "--python",
            "/venv/bin/python",  # Target the internal venv python
            "/app/pyproject.toml",  # Sync using pyproject.toml (will implicitly use lockfile if present)
        ]
        log.info(f"Running uv pip sync from pyproject.toml: {' '.join(sync_cmd)}")
        _run_podman_command(sync_cmd, check=True)
        log.info("Dependencies installed in internal venv from pyproject.toml.")

        # --- DEBUG: Poll container status until 'Up' or timeout ---
        log.info(f"Polling status of container {container_name}...")
        start_time = time.time()
        timeout_seconds = 20  # Max wait time
        is_running = False
        while time.time() - start_time < timeout_seconds:
            try:
                status_check_cmd = ["podman", "ps", "-f", f"name={container_name}", "--format", "{{.Status}}"]
                log.debug(f"DEBUG: Running command: {' '.join(status_check_cmd)}")
                sys.stdout.flush()
                sys.stderr.flush()
                status_check_result = subprocess.run(
                    status_check_cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=5,  # Short timeout for the ps command itself
                )
                status_output = status_check_result.stdout.strip()
                log.debug(
                    f"DEBUG: `podman ps` poll output: '{status_output}' (Exit: {status_check_result.returncode}) Stderr: {status_check_result.stderr.strip()}"
                )
                sys.stdout.flush()
                sys.stderr.flush()

                if status_check_result.returncode == 0 and status_output and "Up" in status_output:
                    log.info(f"DEBUG: Container {container_name} is Up.")
                    is_running = True
                    break  # Exit loop successfully

                # Add a check for container exiting unexpectedly
                if "Exited" in status_output:
                    log.error(f"DEBUG: Container {container_name} exited unexpectedly during startup check.")
                    is_running = False
                    break  # Exit loop as it has failed

            except Exception as status_e:
                log.error(f"DEBUG: Error checking podman status during poll: {status_e}")
                # Continue polling unless timeout is reached
            finally:
                sys.stdout.flush()
                sys.stderr.flush()

            log.debug(f"DEBUG: Container not Up yet, sleeping... (Elapsed: {time.time() - start_time:.1f}s)")
            time.sleep(0.5)  # Wait before next poll

        if not is_running:
            log.error(f"DEBUG: Container {container_name} did not become 'Up' within {timeout_seconds} seconds.")
            return False
        # --- END DEBUG ---

        log.info(f"Successfully started and provisioned Podman container: {container_name}")
        return True
    except Exception as e:
        log.error(f"Failed to start or provision Podman container {container_name}: {e}")
        # Attempt cleanup even on failure
        _stop_podman_runner(container_name)
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


# --- Helper Function for Processing a Single Command Sequence ---
def _process_command_sequence(
    command_sequence: Tuple[str, ...],
    tool_defs_dir: Path,
    project_root: Path,
    container_name: str,
    initial_index_data: Dict[str, Any],
    force: bool,
    since_timestamp: Optional[float],
    ground_truth_txt_skip_hours: int,
) -> Dict[str, Any]:
    """Processes a single command sequence (ground truth gen, skeleton check, prep update data)."""
    log.debug(f"--->>> Worker thread processing: {command_sequence_to_id(command_sequence)}")

    command_id = command_sequence_to_id(command_sequence)
    command_sequence_str = " ".join(command_sequence)
    tool_name = command_sequence[0]
    result: Dict[str, Any] = {
        "command_sequence": command_sequence,
        "status": None,  # Will be BaselineStatus or similar indicator
        "calculated_crc": None,
        "check_timestamp": None,
        "skeleton_created": False,
        "error_message": None,
        "skipped": False,
    }
    log.info(f"Starting processing for: {command_id}")

    try:
        # 1. Check Skip Condition
        should_skip = False
        skip_reason = ""
        current_entry = get_index_entry(initial_index_data, command_sequence)
        if not force and current_entry:
            last_updated = current_entry.get("updated_timestamp", 0.0)

            if since_timestamp is not None:
                # --since is provided, use its logic
                if (
                    last_updated > 0 and last_updated >= since_timestamp
                ):  # Corrected logic: skip if updated *after* or *at* since_timestamp
                    should_skip = True
                    skip_reason = f"last updated ({last_updated:.2f}) is not before --since ({since_timestamp:.2f})"
                else:
                    # --since is NOT provided, apply default configured hour check
                    if ground_truth_txt_skip_hours > 0:  # <-- Use renamed parameter
                        skip_threshold = time.time() - ground_truth_txt_skip_hours * 3600
                        if last_updated > 0 and last_updated > skip_threshold:
                            should_skip = True
                            skip_reason = f"last updated ({last_updated:.2f}) is within the last {ground_truth_txt_skip_hours} hours"
                    # If ground_truth_txt_skip_hours <= 0, no default skip is applied

        if should_skip:
            log.info(f"Skipping ground truth generation for {command_id}: {skip_reason}.")  # <-- Update log message
            result["skipped"] = True
            result["status"] = "SKIPPED_TIMESTAMP"  # More specific status
            return result  # Early exit if skipped

        # 2. Run Ground Truth Generation
        log.info(f"Processing {command_id} (Not skipped).")  # Updated log
        # Ensure project_root is passed correctly from the arguments of this function
        if not isinstance(project_root, Path):
            raise ValueError(f"Invalid project_root type passed to _process_command_sequence: {type(project_root)}")

        status_enum, calculated_crc, check_timestamp = generate_or_verify_ground_truth_txt(
            command_sequence_str,
            root_dir=tool_defs_dir,
            container_name=container_name,
            project_root=project_root,
        )
        result["calculated_crc"] = calculated_crc
        result["check_timestamp"] = check_timestamp
        result["status"] = status_enum  # Store the enum status

        if status_enum not in {
            BaselineStatus.UP_TO_DATE,
            BaselineStatus.UPDATED,
            BaselineStatus.CAPTURE_SUCCESS,
        }:
            result["error_message"] = (
                f"Ground truth TXT generation failed for '{command_sequence_str}' with status: {status_enum.name}"
            )
            log.error(result["error_message"])
            # Don't return early, still try to ensure skeleton exists below
            # Store the failure status

        # 3. Ensure Skeleton JSON exists
        relative_json_path, _ = command_sequence_to_filepath(command_sequence)
        json_file_path = tool_defs_dir / relative_json_path
        skeleton_created = _create_skeleton_json_if_missing(json_file_path, command_sequence)
        result["skeleton_created"] = skeleton_created

        # If skeleton creation failed after ground truth failure, update error message? Or keep original?
        # Let's keep the original ground truth failure as the primary error for now.

        # 4. Prepare update data (even if ground truth failed, we might have CRC/timestamp)
        baseline_txt_path = tool_defs_dir / tool_name / f"{command_id}.txt"
        relative_baseline_path_str = (
            str(baseline_txt_path.relative_to(tool_defs_dir))
            if baseline_txt_path.exists()  # Check if file exists *after* ground truth gen attempt
            else None
        )
        result["update_data"] = {
            "command": list(command_sequence),
            "baseline_file": relative_baseline_path_str,
            "json_definition_file": str(json_file_path.relative_to(tool_defs_dir)),
            "crc": calculated_crc,
            "updated_timestamp": check_timestamp if check_timestamp else time.time(),
            "checked_timestamp": check_timestamp if check_timestamp else time.time(),
            "source": "zlt_tools_sync",
        }

    except Exception as e:
        err_msg = f"Unexpected error processing {command_id}: {e}"
        log.exception(err_msg)
        result["error_message"] = err_msg
        result["status"] = BaselineStatus.UNEXPECTED_ERROR  # Or a new status?

    log.info(
        f"Finished processing for: {command_id} with status: {result.get('status', 'UNKNOWN')} {'(Skipped)' if result.get('skipped') else ''}"
    )
    return result


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
    """Synchronizes tool definitions, baselines, and the tool index."""
    log.critical("!!! ENTERING sync command function !!!")

    # --- Configuration & Initialization --- #
    project_root = ctx.obj.get("project_root")  # Use .get for safety
    config = ctx.obj.get("config", {})  # Use .get with default
    exit_code = 0
    sync_errors: List[str] = []
    processed_count = 0
    updated_count = 0
    skeleton_created_count = 0
    skipped_count = 0
    pruned_count = 0
    max_workers = 4  # Default number of parallel workers, adjust as needed
    # Read ground truth TXT skip hours from config, default to 24 if not set or invalid type
    try:
        ground_truth_txt_skip_hours = int(config.get("ground_truth_txt_skip_since", 24))
    except (ValueError, TypeError):
        log.warning("Invalid value for ground_truth_txt_skip_since in config, defaulting to 24 hours.")
        ground_truth_txt_skip_hours = 24

    if not project_root:
        log.error("Project root could not be determined. Cannot perform sync.")
        ctx.exit(1)

    # --- Podman Setup --- Get container name BEFORE executor
    container_name = _get_container_name(project_root)
    venv_path = project_root / ".venv"
    ctx.obj["podman_container_name"] = container_name  # Still store for potential future use/cleanup

    # Define paths consistently
    tool_defs_dir = project_root / "src" / "zeroth_law" / "tools"
    generated_outputs_dir = project_root / "generated_command_outputs"
    generated_outputs_dir.mkdir(parents=True, exist_ok=True)
    tool_index_path = tool_defs_dir / "tool_index.json"

    try:
        # --- Start Podman Runner ---
        if not _start_podman_runner(container_name, project_root, venv_path):
            log.error("Failed to initialize Podman runner. Aborting sync.")
            ctx.exit(1)
        ctx.obj["podman_container_name"] = container_name

        log.debug("Pausing briefly for container stabilization...")
        time.sleep(2)

        # --- DEBUG: Check container venv/bin --- #
        log.info("--- DEBUG: Checking /venv/bin inside container --- ")
        try:
            ls_result = _run_podman_command(
                ["exec", container_name, "ls", "-la", "/venv/bin"], check=True, capture=True
            )
            log.info(
                f"DEBUG: /venv/bin listing:\n{ls_result.stdout.decode('utf-8', errors='replace')}"
            )  # Decode stdout here
        except Exception as ls_e:
            log.error(f"--- DEBUG: Failed to list /venv/bin: {ls_e} --- ")
            # Optionally exit if this check is critical
            # ctx.exit(1)
        log.info("--- DEBUG: Container check complete --- ")
        # --- End DEBUG --- #

        # --- Reconciliation & Pruning (Sequential - Must happen before parallel sync) ---
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
            raise Exception("Pruning errors occurred")  # Use exception to jump to finally/summary

        if not managed_tools_set:
            log.info("No managed tools identified. Pruning (if requested) is complete. Exiting.")
            if not save_tool_index(load_tool_index()):
                log.error("Failed to save tool index after potential pruning.")
                exit_code = 1
            ctx.exit(exit_code)

        # --- Filter Target Tools ---
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

        # --- Parse --since ---
        since_timestamp = None
        if since:
            try:
                if since.endswith("h"):
                    since_timestamp = time.time() - int(since[:-1]) * 3600
                elif since.endswith("d"):
                    since_timestamp = time.time() - int(since[:-1]) * 86400
                else:
                    since_timestamp = float(since)  # Basic epoch assumption
                    log.info(f"Applying --since filter: {since} (Timestamp > {since_timestamp:.2f})")
            except ValueError:
                log.error(f"Invalid --since format: {since}. Expected format like '24h', '3d', or epoch timestamp.")
                ctx.exit(1)

        # --- Load Initial Index ---
        if not tool_index_path.is_file():
            log.warning(f"Tool index file not found at {tool_index_path}, creating empty index.")
            tool_index_path.write_text("{}", encoding="utf-8")
        index_data = load_tool_index()  # Load initial state for skip checks

        # --- DEBUG: Check container filesystem --- #
        log.info("--- DEBUG: Checking container filesystem before parallel execution ---")
        try:
            log.info("DEBUG: Listing /venv contents...")
            _run_podman_command(["exec", container_name, "/bin/ls", "-la", "/venv"], check=True, capture=True)
            log.info("DEBUG: Listing /venv/bin contents...")
            _run_podman_command(["exec", container_name, "/bin/ls", "-la", "/venv/bin"], check=True, capture=True)
            log.info("--- DEBUG: Filesystem check complete ---")
        except Exception as fs_check_e:
            log.error(f"--- DEBUG: Error checking container filesystem: {fs_check_e} ---")
            # Optionally exit if filesystem check fails critically
            # ctx.exit(1)

        # --- Prepare Task List ---
        tasks_to_run: List[Tuple[str, ...]] = []
        for tool_name in sorted(list(target_tools)):
            # Add base command task
            base_command_sequence = (tool_name,)
            tasks_to_run.append(base_command_sequence)

            # Check for subcommands in the base JSON definition
            relative_base_json_path, _ = command_sequence_to_filepath(base_command_sequence)
            base_json_file_path = tool_defs_dir / relative_base_json_path
            if base_json_file_path.exists():
                try:
                    with base_json_file_path.open("r", encoding="utf-8") as f_base:
                        base_definition_data = json_lib.load(f_base)
                        if isinstance(base_definition_data, dict) and "subcommands_detail" in base_definition_data:
                            subcommands_detail = base_definition_data["subcommands_detail"]
                            if isinstance(subcommands_detail, dict):
                                for sub_key in subcommands_detail.keys():
                                    sub_command_sequence = (tool_name, sub_key)
                                    tasks_to_run.append(sub_command_sequence)
                except Exception as json_e:
                    log.warning(f"Could not load or parse {base_json_file_path} to check for subcommands: {json_e}")

        log.info(f"Prepared {len(tasks_to_run)} total command sequences for parallel processing.")

        # --- Execute Tasks in Parallel ---
        results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Store future-to-sequence mapping for logging upon completion/error
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

            # Process completed futures
            for future in as_completed(future_to_sequence):
                sequence = future_to_sequence[future]
                try:
                    result = future.result()
                    results.append(result)
                    processed_count += 1  # Increment processed count here
                    # Maybe log progress like: log.info(f"Completed {processed_count}/{len(tasks_to_run)} tasks.")
                except Exception as exc:
                    command_id = command_sequence_to_id(sequence)
                    err_msg = f"Task for {command_id} generated an unexpected exception: {exc}"
                    log.exception(err_msg)  # Log traceback
                    sync_errors.append(err_msg)
                    processed_count += 1  # Still counts as processed, albeit failed

        log.info("All processing tasks completed.")

        # --- Process Results and Update Index (Serially) ---
        log.info("Processing results and updating index...")
        final_index_data = (
            load_tool_index()
        )  # Re-load index in case pruning changed it? Or assume initial load is fine? Let's use initial for now.
        # It's safer to use the initially loaded index_data, as pruning happened before parallel execution.
        final_index_data = index_data

        for result in results:
            if result.get("skipped"):
                skipped_count += 1
                continue  # Don't update index for skipped items

            status = result.get("status")
            error_message = result.get("error_message")
            command_sequence = result["command_sequence"]
            update_data = result.get("update_data")

            if error_message:
                # If there was an error during processing itself, ensure it's in sync_errors
                if error_message not in sync_errors:
                    sync_errors.append(error_message)

            # Check if ground truth generation status indicates failure
            if isinstance(status, BaselineStatus) and status not in {
                BaselineStatus.UP_TO_DATE,
                BaselineStatus.UPDATED,
                BaselineStatus.CAPTURE_SUCCESS,
            }:
                # If ground truth generation failed, ensure the error message is captured if not already present
                if not error_message:
                    err_msg_from_status = f"Ground truth TXT generation failed for '{' '.join(command_sequence)}' with status: {status.name}"  # <-- Update log message
                    if err_msg_from_status not in sync_errors:
                        sync_errors.append(err_msg_from_status)
                # Do NOT update the index entry if ground truth generation failed, but count skeleton creation
                if result.get("skeleton_created"):
                    skeleton_created_count += 1
            elif update_data and not error_message:
                # Update index only if ground truth generation was successful OR up-to-date AND no processing error occurred
                try:
                    update_index_entry(final_index_data, command_sequence, update_data)
                    # Increment update count if ground truth generation status was UPDATED or skeleton was created
                    if result.get("skeleton_created") or status == BaselineStatus.UPDATED:
                        updated_count += 1
                except Exception as index_e:
                    err_msg = f"Failed to update index for {command_sequence_to_id(command_sequence)}: {index_e}"
                    log.exception(err_msg)
                    sync_errors.append(err_msg)
            elif result.get("skeleton_created"):
                # Count skeleton creation even if index wasn't updated due to ground truth generation failure
                skeleton_created_count += 1

        # --- Save Final Index ---
        log.info("Saving updated tool index...")
        if not save_tool_index(final_index_data):
            log.error("Failed to save final tool index.")
            exit_code = 1  # Mark failure

        # --- Report Summary --- (Adjust counters based on collected results)
        log.info("-- Sync Summary --")
        log.info(f"Tools Targeted:       {len(target_tools)}")
        log.info(f"Sequences Processed:  {processed_count}")  # Total futures processed
        log.info(f"Sequences Skipped (timestamp): {skipped_count}")  # Clarify skip reason
        log.info(f"Ground Truth/JSON Updated/Created: {updated_count}")  # Rename summary line
        # log.info(f"Skeletons Created:    {skeleton_created_count}") # Can be combined with updated count or kept separate
        log.info(f"Errors Encountered:   {len(sync_errors)}")
        if prune:
            log.info(f"Directories Pruned:   {pruned_count}")
        if sync_errors:
            log.error("Sync completed with errors:")
            for err in sync_errors:
                log.error(f"- {err}")
            exit_code = 1  # Mark failure if not already set
        else:
            log.info("Synchronization completed successfully.")

    except ReconciliationError as e:
        log.error(f"Sync failed during initial reconciliation: {e}")
        exit_code = 2
    except Exception as e:
        if "Pruning errors occurred" not in str(e):
            log.exception("An unexpected error occurred during the sync command.")
            exit_code = 3
    finally:
        # --- Podman Cleanup --- Use the name determined earlier
        if container_name:
            _stop_podman_runner(container_name)

    ctx.exit(exit_code)
