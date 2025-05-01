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
import logging  # Add logging import for level names
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import os
import json as json_lib  # Alias to avoid conflict
from ...common.config_loader import load_config
from ...common.logging_utils import setup_structlog_logging  # ADD NEW IMPORT

# TODO: [Implement Subcommand Blacklist] Reference TODO H.14 in TODO.md - This module needs to filter command sequences based on resolved hierarchical status.

# --- Imports from other modules --- #

# Need reconciliation logic, status enum, and the effective status checker
from .reconcile import (
    _perform_reconciliation_logic,
    ReconciliationError,
    ToolStatus,
    # ParsedHierarchy, # Import type from common
    # _get_effective_status, # Import checker from tool_reconciler
)
from ...lib.tooling.tool_reconciler import _get_effective_status  # Import checker
from ...common.hierarchical_utils import (
    ParsedHierarchy,
    check_list_conflicts,
    get_effective_status,
    parse_to_nested_dict,
)
from ...common.path_utils import list_executables_in_venv_bin  # ADDED IMPORT

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

# Need sequence generation logic
# --- Corrected imports for sequence scanning --- #
# from ...lib.tooling.tools_dir_scanner import scan_for_command_sequences # Old scanner
from ...lib.tooling.tools_dir_scanner import scan_whitelisted_sequences  # New scanner

# Need skeleton creation logic (adapted from conftest)

log = structlog.get_logger()

# Define spinner characters
# SPINNER = itertools.cycle(["-", "\\\\", "|", "/"])

# === Stage 1: Podman Setup/Teardown ===


def _get_container_name(project_root: Path) -> str:
    """Generate a deterministic container name for the project."""
    project_hash = hashlib.sha1(str(project_root).encode()).hexdigest()[:12]
    return f"zlt-baseline-runner-{project_hash}"


def _start_podman_runner(container_name: str, project_root: Path, venv_path: Path) -> bool:
    """STAGE 1: Starts the podman container, creates internal venv, and installs deps."""
    log.info(f"STAGE 1: Attempting to start Podman baseline runner: {container_name}")

    # --- Build local project wheel --- #
    log.info("Building project wheel locally...")
    wheel_dir = project_root / "dist"
    # Ensure clean build directory
    if wheel_dir.exists():
        log.debug(f"Removing existing wheel directory: {wheel_dir}")
        shutil.rmtree(wheel_dir)
    wheel_dir.mkdir()
    try:
        # Use python -m build to build the wheel
        # Correct path construction: venv_path should already point to the bin dir
        host_python_exe = venv_path / "python"
        if not host_python_exe.is_file():
            log.error(f"Host python executable not found in venv bin: {host_python_exe}")
            return False

        build_cmd = [
            str(host_python_exe),  # Use python from host venv
            "-m",
            "build",
            "--wheel",  # Build only wheel
            f"--outdir={wheel_dir}",  # Output directory
            ".",  # Build the current directory
        ]
        log.debug(f"Running wheel build command: {' '.join(build_cmd)}")
        # Note: This runs on the HOST, not in podman. Needs error handling.
        build_result = subprocess.run(build_cmd, cwd=project_root, check=True, capture_output=True, text=True)
        log.info(f"Successfully built wheel. Build output:\n{build_result.stdout}")
        # Find the built wheel file
        built_wheels = list(wheel_dir.glob("*.whl"))
        if not built_wheels:
            raise RuntimeError("python -m build command completed but no wheel file found in dist/")
        if len(built_wheels) > 1:
            log.warning(f"Multiple wheels found in dist/, using the first one: {built_wheels[0]}")
        local_wheel_path = built_wheels[0]
        log.info(f"Using wheel: {local_wheel_path.name}")
    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError) as build_e:
        log.error(f"Failed to build local project wheel: {build_e}")
        if isinstance(build_e, subprocess.CalledProcessError):
            log.error(f"Build stderr:\n{build_e.stderr}")
        return False
    # --- End Build local project wheel --- #

    # --- Ensure host venv exists (to get python) --- #
    # Correct path construction: venv_path should already point to the bin dir
    host_python_path = venv_path / "python"
    if not host_python_path.is_file():
        log.error(f"Host `python` executable not found at: {host_python_path}. Cannot proceed.")
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

    # --- Determine host cache path ---
    host_python_cache = Path.home() / ".cache" / "python"
    host_python_cache.mkdir(parents=True, exist_ok=True)  # Ensure host cache dir exists
    container_python_cache = "/root/.cache/python"  # Standard location for root user

    try:
        # Mount project root read-only AND host python cache read-write.
        _run_podman_command(
            [
                "run",
                "--rm",
                "-d",
                "--name",
                container_name,
                f"--volume={str(project_root.resolve())}:/app:ro",  # Mount project root read-only
                f"--volume={str(host_python_cache.resolve())}:{container_python_cache}:rw",  # Mount python cache
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

        # --- Determine path to uv inside the container --- #
        internal_uv_path = "uv"  # Default assumption
        try:
            uv_check_result = _run_podman_command(["exec", container_name, "which", "uv"], check=False, capture=True)
            if uv_check_result.returncode == 0:
                internal_uv_path = uv_check_result.stdout.decode("utf-8").strip()
                log.info(f"`uv` found in container PATH: {internal_uv_path}")
            else:
                log.warning("uv not found in container PATH. Installing using pip...")
                _run_podman_command(["exec", container_name, "/venv/bin/pip", "install", "uv"], check=True)
                internal_uv_path = "/venv/bin/uv"  # Assume standard install path
                log.info(f"`uv` installed inside container at {internal_uv_path}")
        except Exception as uv_e:
            log.error(f"Failed to determine uv path inside container: {uv_e}")
            return False  # Cannot proceed without uv

        # --- Copy requirements AND wheel file into container --- #
        host_req_file = project_root / "requirements-dev.txt"
        container_req_file = "/tmp/requirements-dev.txt"
        container_wheel_file = f"/tmp/{local_wheel_path.name}"
        if host_req_file.is_file():
            log.info(f"Copying {host_req_file.name} to {container_name}:{container_req_file}...")
            _run_podman_command(["cp", str(host_req_file), f"{container_name}:{container_req_file}"], check=True)
            log.info(f"Copying {local_wheel_path.name} to {container_name}:{container_wheel_file}...")
            _run_podman_command(["cp", str(local_wheel_path), f"{container_name}:{container_wheel_file}"], check=True)
            log.info("Requirements and wheel files copied.")
        else:
            log.error(f"Host requirements file {host_req_file} not found. Cannot sync dependencies.")
            return False

        # --- Run uv pip install using the requirements file AND the wheel file --- #
        install_cmd = [
            "exec",
            "-w",
            "/app",
            container_name,
            internal_uv_path,
            "pip",
            "install",
            "--python",
            "/venv/bin/python",
            "-r",
            container_req_file,
            container_wheel_file,
        ]
        log.info(f"Running uv pip install from requirements and wheel file...")
        _run_podman_command(install_cmd, check=True)
        log.info("Dependencies and local project installed in internal venv.")

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

        log.info(f"STAGE 1: Successfully started and provisioned Podman container: {container_name}")
        return True
    except Exception as e:
        log.error(f"STAGE 1: Failed to start or provision Podman container {container_name}: {e}")
        # Attempt cleanup even on failure
        _stop_podman_runner(container_name)
        return False


def _stop_podman_runner(container_name: str) -> None:
    """STAGE 7: Stops and removes the podman container."""
    log.info(f"STAGE 7: Stopping and removing Podman container: {container_name}")
    try:
        # Use --ignore to avoid errors if container is already gone
        _run_podman_command(["stop", "--ignore", container_name], check=False)
        _run_podman_command(["rm", "--ignore", container_name], check=False)
        log.info(f"Podman container {container_name} stopped and removed.")
    except Exception as e:
        # Log error but don't prevent script exit
        log.error(f"Error stopping/removing Podman container {container_name}: {e}")


# === Stage 2: Reconciliation & Pruning ===


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

    reconciliation_results, managed_tools_set, parsed_whitelist, parsed_blacklist, errors, warnings, has_errors = (
        _perform_reconciliation_logic(project_root_dir=project_root, config_data=config)
    )

    if prune:
        blacklisted_present = {
            t for t, s in reconciliation_results.items() if s == ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR
        }
        orphaned_present = {t for t, s in reconciliation_results.items() if s == ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR}
        dirs_to_prune = blacklisted_present.union(orphaned_present)

        if dirs_to_prune:
            log.warning(
                f"--prune specified: {len(dirs_to_prune)} directories will be removed: {sorted(list(dirs_to_prune))}"
            )
            for tool_name in dirs_to_prune:
                dir_path = tool_defs_dir / tool_name
                if dir_path.is_dir():
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
                    log.warning(f"Requested prune for {tool_name}, but directory {dir_path} not found.")
        else:
            log.info("--prune specified, but no unmanaged or blacklisted directories found.")

    if sync_errors:
        log.error("Errors occurred during pruning phase.")
        # Raise exception to halt sync? Or just return errors?
        # Let's return errors for now.

    log.info("STAGE 2: Reconciliation and pruning complete.")
    return reconciliation_results, managed_tools_set, parsed_whitelist, parsed_blacklist, sync_errors, pruned_count


# === Stage 3: Target Tool Identification ===


def _identify_target_tools(
    specific_tools: Tuple[str, ...], reconciliation_results: Dict[str, ToolStatus], managed_tools_set: Set[str]
) -> Optional[Set[str]]:
    """STAGE 3: Determines the final set of tool names to target based on --tool option.

    Returns the set of target tool names, or None if no valid targets found.
    """
    log.info("STAGE 3: Identifying target tools...")
    target_tool_names: Set[str]
    if specific_tools:
        target_tool_names = set(specific_tools)
        all_known_tools = set(reconciliation_results.keys())
        missing_specified = target_tool_names - all_known_tools
        if missing_specified:
            log.warning(f"Specified tools not found in reconciliation results: {missing_specified}")
        target_tool_names = target_tool_names.intersection(all_known_tools)
        if not target_tool_names:
            log.error("None of the specified tools are known. Nothing to sync.")
            return None
    else:
        target_tool_names = managed_tools_set
        if not target_tool_names:
            log.info("No managed tools identified by reconciliation. Nothing to sync.")
            return None

    log.info(f"Targeting {len(target_tool_names)} tools for sync: {sorted(list(target_tool_names))}")
    return target_tool_names


# === Stage 4: Sequence Generation & Filtering ===


def _generate_and_filter_sequences(
    tool_defs_dir: Path,
    target_tool_names: Set[str],
    parsed_whitelist: ParsedHierarchy,
    parsed_blacklist: ParsedHierarchy,
) -> Tuple[List[Tuple[str, ...]], int, int]:
    """STAGE 4: Generates all possible sequences and filters them.

    Returns: Tuple containing the list of sequences to run, count of sequences
             skipped by scope (target tools), count skipped by blacklist.
    """
    log.info("STAGE 4: Generating and filtering command sequences...")
    tasks_to_run: List[Tuple[str, ...]] = []
    skipped_by_blacklist_count = 0
    skipped_by_scope_count = 0

    try:
        all_sequences = scan_for_command_sequences(tool_defs_dir)
        log.info(f"Generated {len(all_sequences)} potential command sequences.")
    except Exception as e:
        log.error(f"Error generating command sequences: {e}")
        raise  # Re-raise to stop the sync process

    target_sequences = [seq for seq in all_sequences if seq and seq[0] in target_tool_names]
    skipped_by_scope_count = len(all_sequences) - len(target_sequences)
    log.info(f"Filtered to {len(target_sequences)} sequences based on target tools.")

    for sequence in target_sequences:
        effective_status = _get_effective_status(list(sequence), parsed_whitelist, parsed_blacklist)
        if effective_status == "whitelist":
            tasks_to_run.append(sequence)
        else:
            skipped_by_blacklist_count += 1
            log.debug(f"Skipping sequence due to non-whitelist status: {sequence}")

    log.info(f"Final task list size after filtering: {len(tasks_to_run)}")
    if skipped_by_scope_count > 0:
        log.info(f"Skipped {skipped_by_scope_count} sequences due to --tool scoping.")
    if skipped_by_blacklist_count > 0:
        log.info(f"Skipped {skipped_by_blacklist_count} sequences due to blacklist/unmanaged status.")

    return tasks_to_run, skipped_by_scope_count, skipped_by_blacklist_count


# === Stage 5: Parallel Baseline Processing ===


# Helper for Skeleton Creation (Moved here for use by Stage 5 helper)
def _create_skeleton_json_if_missing(json_file_path: Path, command_sequence: tuple[str, ...]) -> bool:
    """Creates a schema-compliant skeleton JSON if it doesn't exist."""
    created = False
    if not json_file_path.exists():
        command_name = command_sequence[0]
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
            created = True
        except IOError as e:
            log.error(f"Skeleton Action Error: Failed to write skeleton JSON {json_file_path}: {e}")
    return created


# Helper Function for Processing a Single Command Sequence (Moved here for use by Stage 5)
def _process_command_sequence(
    command_sequence: Tuple[str, ...],
    tool_defs_dir: Path,
    project_root: Path,
    container_name: str,
    initial_index_data: Dict[str, Any],
    force: bool,
    since_timestamp: Optional[float],
    ground_truth_txt_skip_hours: int,
    generated_outputs_dir: Path,
) -> Dict[str, Any]:
    """Processes a single command sequence (ground truth gen, skeleton check, prep update data)."""
    log.debug(f"--->>> Worker thread processing: {command_sequence_to_id(command_sequence)}")

    command_id = command_sequence_to_id(command_sequence)
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

    # Define paths early for dry-run logging
    relative_json_path, relative_baseline_path = command_sequence_to_filepath(command_sequence)
    json_file_path = tool_defs_dir / relative_json_path
    baseline_dir = project_root / "generated_command_outputs"
    baseline_file_path = baseline_dir / relative_baseline_path

    # ADDED LOG: Verify the constructed baseline path
    log.info(f"Constructed baseline file path: {baseline_file_path}")

    try:
        # --- Restore getting index entry --- #
        current_index_entry = get_index_entry(initial_index_data, command_sequence)

        # --- Restore call to baseline generator with all args --- #
        status_enum, calculated_crc, check_timestamp = generate_or_verify_ground_truth_txt(
            command_sequence=command_sequence,
            container_name=container_name,
            project_root=project_root,
            index_entry=current_index_entry,
            force=force,
            since_timestamp=since_timestamp,
            skip_hours=ground_truth_txt_skip_hours,
            output_capture_path=baseline_file_path,
        )

        result["calculated_crc"] = calculated_crc
        result["check_timestamp"] = check_timestamp
        result["status"] = status_enum  # Store the actual or simulated status

        if status_enum not in {
            BaselineStatus.UP_TO_DATE,
            BaselineStatus.UPDATED,
            BaselineStatus.CAPTURE_SUCCESS,
        }:
            result["error_message"] = (
                f"Ground truth TXT generation failed for {' '.join(command_sequence)} with status: {status_enum.name}"
            )
            log.error(result["error_message"])

        # 3. Ensure Skeleton JSON exists
        skeleton_created = _create_skeleton_json_if_missing(json_file_path, command_sequence)
        result["skeleton_created"] = skeleton_created
        if not skeleton_created and not json_file_path.exists():  # Check if creation failed
            # Update error message if skeleton creation failed
            err_msg_skel = f"FAILED to ensure skeleton JSON exists at {json_file_path} for {command_id}."
            result["error_message"] = result.get("error_message", "") + f" {err_msg_skel}"
            result["status"] = BaselineStatus.FAILED_SKELETON_ENSURE  # Mark skeleton failure

        # 4. Prepare update data (always prepare, even for failures, but CRC might be None)
        relative_baseline_path_str = (
            str(baseline_file_path.relative_to(generated_outputs_dir))
            if baseline_file_path.exists()
            else None  # Set to None if baseline doesn't exist
        )
        # Use the result["calculated_crc"] which could be None on failure
        update_crc = result["calculated_crc"]
        update_timestamp = result["check_timestamp"]  # Use timestamp from result

        result["update_data"] = {
            "command": list(command_sequence),
            "baseline_file": relative_baseline_path_str,
            "json_definition_file": str(relative_json_path),
            "crc": update_crc,  # Use actual CRC (might be None)
            "updated_timestamp": update_timestamp,  # Use actual timestamp
            "checked_timestamp": update_timestamp,  # Use actual timestamp
            "source": "zlt_tools_sync",  # Removed dry_run suffix
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


def _run_parallel_baseline_processing(
    tasks_to_run: List[Tuple[str, ...]],
    tool_defs_dir: Path,
    project_root: Path,
    container_name: str,
    index_data: Dict[str, Any],
    force: bool,
    since_timestamp: Optional[float],
    ground_truth_txt_skip_hours: int,
    generated_outputs_dir: Path,
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
                generated_outputs_dir,
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
                if result.get("error_message") or (
                    isinstance(result.get("status"), BaselineStatus)
                    and result["status"]
                    not in {BaselineStatus.UP_TO_DATE, BaselineStatus.UPDATED, BaselineStatus.CAPTURE_SUCCESS}
                ):
                    error_count += 1
                    log.warning(f"Error encountered for {command_id} (Total errors: {error_count})")
                    if exit_errors_limit is not None and error_count >= exit_errors_limit:
                        log.error(f"Reached error limit ({exit_errors_limit}). Stopping processing early.")
                        # We can't easily cancel running futures, but we stop processing results
                        sync_errors.append(f"Reached error limit ({exit_errors_limit}) processing {command_id}.")
                        # TODO: Add logic to signal cancellation to running tasks if possible/needed.
                        # For now, just break the loop.
                        break  # Stop processing further completed futures

            except Exception as exc:
                err_msg = f"Task for {command_id} generated unexpected exception: {exc}"
                log.exception(err_msg)
                sync_errors.append(err_msg)
                processed_count += 1  # Count as processed even if exception
                error_count += 1  # Count exception as an error
                if exit_errors_limit is not None and error_count >= exit_errors_limit:
                    log.error(f"Reached error limit ({exit_errors_limit}) due to exception in {command_id}.")
                    break

    log.info(f"STAGE 5: Parallel processing finished. Processed {processed_count} tasks.")
    return results, sync_errors, processed_count


# === Stage 6: Index Update & Save ===


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
    skeleton_created_count = 0  # Track skeleton creation separately

    for result in results:
        if result.get("skipped"):
            skipped_count += 1
            continue

        status = result.get("status")
        error_message = result.get("error_message")  # Check for processing error
        command_sequence = result["command_sequence"]
        update_data = result.get("update_data")
        skeleton_created = result.get("skeleton_created", False)

        if skeleton_created:
            skeleton_created_count += 1

        # Only update index if baseline processing didn't fail and no processing error occurred
        is_success_status = isinstance(status, BaselineStatus) and status in {
            BaselineStatus.UP_TO_DATE,
            BaselineStatus.UPDATED,
            BaselineStatus.CAPTURE_SUCCESS,
        }

        if update_data and is_success_status and not error_message:
            try:
                update_index_entry(final_index_data, command_sequence, update_data)
                # Count as updated if status was UPDATED or if a skeleton was newly created
                if status == BaselineStatus.UPDATED or skeleton_created:
                    # Avoid double counting if skeleton was created AND baseline was updated
                    if not (status == BaselineStatus.UPDATED and skeleton_created):
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
        if not save_tool_index(final_index_data):
            log.error("Failed to save final tool index.")
            index_errors.append("Failed to save final tool index.")

    log.info("STAGE 6: Index update complete.")
    # Return updated count (includes skeleton creations) and skipped count
    return final_index_data, index_errors, updated_count, skipped_count


# === Helper Functions ===


def _load_initial_config_and_state(
    ctx: click.Context,
) -> Tuple[Path, Dict[str, Any], Path, List[str], ParsedHierarchy, ParsedHierarchy]:
    """Handles Steps 1-3: Load config, find venv, discover executables, classify."""
    log.debug("Entering _load_initial_config_and_state...")

    # --- Step 1: Project Root and Config --- #
    # Get project_root from context (assuming cli.py set it up)
    project_root = ctx.obj.get("project_root")
    if not project_root or not isinstance(project_root, Path):
        ctx.fail("Project root not found or invalid in context.")

    # --- REMOVE WORKAROUND --- #
    # config_file_path = project_root / "pyproject.toml"
    # log.debug("Attempting direct config load (simplified)", path=str(config_file_path))
    # # Simplified load_config now returns just the [tool.zeroth-law] section
    # zlt_config = load_config(config_file_path)
    # if not zlt_config:
    #     log.warning("Direct config loading returned empty dict. Proceeding with defaults.")
    #     # Handle defaults if needed, or rely on downstream .get() with defaults
    # --- END REMOVE WORKAROUND --- #

    # --- USE CONTEXT CONFIG --- #
    config = ctx.obj.get("config")
    if not config or not isinstance(config, dict):
        log.warning("Config not found or invalid in context. Proceeding with empty config.")
        config = {}
    # Add debug log for context config
    log.debug("Using config from context", config_id=id(config), config_keys=list(config.keys()))
    # --- END USE CONTEXT CONFIG --- #

    # Venv Path Determination (relative to project root)
    # TODO: Make this configurable?
    venv_bin_path = project_root / ".venv" / "bin"
    if not venv_bin_path.is_dir():
        ctx.fail(f"Virtual environment bin directory not found: {venv_bin_path}")
    log.info(f"Using virtual environment bin path: {venv_bin_path}")

    # --- Step 2: Discover Executables --- #
    log.info("Step 2: Discovering executables in venv bin...")
    try:
        all_executables = list_executables_in_venv_bin(venv_bin_path)
    except FileNotFoundError as e:
        ctx.fail(str(e))
    except OSError as e:
        ctx.fail(f"Error reading executables from {venv_bin_path}: {e}")
    log.info(f"Found {len(all_executables)} potential executables in venv bin.")
    log.debug("Raw executables found:", executables=sorted(all_executables))

    # --- Step 3: Filter based on Whitelist/Blacklist --- #
    log.info("Step 3: Filtering executables based on whitelist/blacklist...")
    managed_executables = []
    unclassified_executables = []
    blacklisted_found = []
    whitelist_tree = {}
    blacklist_tree = {}

    try:
        # Extract managed-tools section directly from the CONTEXT config
        # Note: load_config now includes managed-tools in its return dict
        managed_tools_config = config.get("managed-tools", {})
        log.debug(
            "Accessing managed-tools from CONTEXT config",
            type=type(managed_tools_config).__name__,
            value=repr(managed_tools_config),
        )

        # Get raw lists
        raw_whitelist = managed_tools_config.get("whitelist", [])
        raw_blacklist = managed_tools_config.get("blacklist", [])

        # Check for conflicts before parsing
        # Pass the PARSED trees, not the raw lists
        conflict_msg = check_list_conflicts(whitelist_tree, blacklist_tree)
        if conflict_msg:
            ctx.fail(f"Configuration Error: {conflict_msg}")

        # Parse lists into hierarchical trees
        # Need to import parse_to_nested_dict
        whitelist_tree = parse_to_nested_dict(raw_whitelist)
        blacklist_tree = parse_to_nested_dict(raw_blacklist)
        log.debug("Whitelist tree parsed", tree=whitelist_tree)
        log.debug("Blacklist tree parsed", tree=blacklist_tree)

        # Classify executables
        for exe in all_executables:
            status = get_effective_status([exe], whitelist_tree, blacklist_tree)
            if status == "WHITELISTED":
                managed_executables.append(exe)
            elif status == "BLACKLISTED":
                blacklisted_found.append(exe)
            else:  # UNSPECIFIED
                unclassified_executables.append(exe)

        # Report results
        log.info(
            "Executable classification complete.",
            whitelisted_count=len(managed_executables),
            blacklisted_count=len(blacklisted_found),
            unclassified_count=len(unclassified_executables),
        )
        if blacklisted_found:
            log.debug("Blacklisted executables found and ignored:", blacklisted=sorted(blacklisted_found))

        # Check for unclassified executables (Step 3.7 - Failure condition)
        if unclassified_executables:
            log.error(
                "Sync Failed: The following executables found in venv are not classified in whitelist or blacklist:",
                unclassified=sorted(unclassified_executables),
            )
            log.error(
                "Please classify them using `zlt tools whitelist add <tool>` or `zlt tools blacklist add <tool>`."
            )
            ctx.fail("Unclassified executables found.")  # Use ctx.fail

    except Exception as e:
        log.exception(f"Failed during whitelist/blacklist processing: {e}")
        ctx.fail(f"Failed during whitelist/blacklist processing: {e}")

    # --- Return values --- #
    # Return project_root, the CONTEXT config, venv_bin_path, managed_executables, and parsed trees
    return project_root, config, venv_bin_path, sorted(managed_executables), whitelist_tree, blacklist_tree


@click.command("sync")
# @common_options # Apply common options using the decorator - RE-ENABLED -- REMOVE THIS LINE
# Manually add ALL options for debugging - REMOVED -- RESTORE THESE
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
    "--prune",
    is_flag=True,
    help="Remove unmanaged or blacklisted tool directories found locally.",
)
@click.option(
    "--generate",
    "generate_baselines",
    is_flag=True,
    help="Generate ground truth baseline files. Requires Podman.",
)
@click.option(
    "--skip-hours",
    "ground_truth_txt_skip_hours",
    type=int,
    default=7 * 24,  # Default to 1 week
    help="(--check-since-hours) Skip baseline regeneration if checked within this many hours (unless --force). Default: 168 (7 days).",
    show_default=True,
)
@click.option(
    "--update-since-hours",
    type=int,
    default=48,  # Default to 2 days
    help="Issue a warning if baseline changes again within this many hours. Default: 48 (2 days).",
    show_default=True,
)
@click.option(
    "--dry-run", is_flag=True, default=False, help="Show what actions would be taken without actually executing them."
)
@click.option(
    "--exit-errors",
    type=int,
    default=None,  # No limit by default
    help="Exit sync after this many baseline generation errors (FAILED_CAPTURE).",
    show_default="No limit",
)
@click.option("--debug", is_flag=True, default=False, help="Enable DEBUG level logging for sync.")
# Add back other necessary options MANUALLY if common_options added them before
# Example: Check zlt_options_definitions.json for verbose, config, quiet, color
# These are typically handled by the main CLI group and accessed via ctx
@click.pass_context
def sync(
    ctx: click.Context,
    # Manually list expected arguments from common_options and sync-specific ones -- REVERT THIS
    # Arguments from common_options (verify these match zlt_options_definitions.json) -- REMOVE
    # verbose: int, # Maps to -v count -- REMOVE
    # Arguments specific to 'sync' that were previously manually defined -- Keep these args
    specific_tools: Tuple[str, ...],
    force: bool,
    prune: bool,
    generate_baselines: bool,
    ground_truth_txt_skip_hours: int,
    update_since_hours: int,
    dry_run: bool,
    exit_errors: Optional[int],
    debug: bool,  # Add debug flag parameter
) -> None:
    """Syncs the local tool definitions with the managed tools and generates baselines."""
    start_time = time.time()

    # --- Add NEW Logging Setup --- #
    if debug:
        # Simplest approach for now: reconfigure globally
        global_options = ctx.obj.get("options", {})
        color = global_options.get("color")  # Get color preference if set globally
        setup_structlog_logging("debug", color)
        log.info("DEBUG logging enabled for sync command.")
    # --- End NEW Logging Setup --- #

    # Original start message
    log.info(f"Starting zlt tools sync... (Dry Run: {dry_run})")

    # === Call new helper for Steps 1-3 ===
    project_root, config, venv_bin_path, managed_executables, whitelist_tree, blacklist_tree = (
        _load_initial_config_and_state(ctx)
    )

    # Check if managed_executables is empty after initial load
    if not managed_executables:
        log.warning("No whitelisted executables identified. Nothing further to sync.")
        ctx.exit(0)
    # === End call ===

    # Also define tool_defs_dir and tool_index_path here as they depend on project_root
    tool_defs_dir = project_root / "src" / "zeroth_law" / "tools"
    tool_index_path = tool_defs_dir / "tool_index.json"

    # --- Step 4: Reconcile tools/ Directory Structure --- (Keep inline for now)
    log.info("Step 4: Reconciling tools/ directory structure...")
    orphan_dirs = []
    try:
        # 4.1 Define tools_base_dir (done above)
        # 4.2 Get existing directories
        if not tool_defs_dir.is_dir():
            log.warning(f"Tools definition directory does not exist, creating: {tool_defs_dir}")
            tool_defs_dir.mkdir(parents=True)
        existing_tool_dirs = [d.name for d in tool_defs_dir.iterdir() if d.is_dir()]

        # 4.3 Init list (done above)
        # 4.4 Check existing dirs for orphans
        for dir_name in existing_tool_dirs:
            status = get_effective_status([dir_name], whitelist_tree, blacklist_tree)
            if status == "BLACKLISTED" or status == "UNSPECIFIED":
                orphan_dirs.append(dir_name)

        # 4.5 Fail if orphans found
        if orphan_dirs:
            log.error(
                "Sync Failed: The following directories exist in tools/ but are blacklisted or unclassified:",
                orphans=sorted(orphan_dirs),
            )
            log.error("Please add relevant tools to the whitelist or manually remove these directories.")
            ctx.fail("Orphaned/Blacklisted tool directories found.")  # Use ctx.fail

        # 4.6 Ensure directories exist for managed executables
        for tool_name in managed_executables:
            expected_dir_path = tool_defs_dir / tool_name
            if not expected_dir_path.is_dir():
                log.info(f"Creating missing tool directory: {expected_dir_path.relative_to(project_root)}")
                expected_dir_path.mkdir()

        # 4.7 Verification implicit (no failure)
        log.info("Validated tools/ directory structure against managed tools list.")

    except Exception as e:
        log.exception(f"Failed during tools/ directory reconciliation: {e}")
        ctx.fail(f"Failed during tools/ directory reconciliation: {e}")
    # --- End Step 4 --- #

    # --- Step 5: Identify Effectively Whitelisted Command Sequences --- (Keep inline for now)
    log.info("Step 5: Identifying effectively whitelisted command sequences...")
    whitelisted_sequences: List[Tuple[str, ...]] = []
    try:
        # 5.1-5.4 Call the new scanner function
        whitelisted_sequences = scan_whitelisted_sequences(
            base_tools_dir=tool_defs_dir, whitelist_tree=whitelist_tree, blacklist_tree=blacklist_tree
        )
        # 5.5 (Implicitly done by the function)
        # 5.6 Verification Log (moved inside function, but can log summary here too)
        log.info(f"Total effectively whitelisted command sequences identified: {len(whitelisted_sequences)}")
        if not whitelisted_sequences:
            log.warning("No effectively whitelisted command sequences found. Nothing further to sync.")
            ctx.exit(0)
    except Exception as e:
        log.exception(f"Failed during command sequence identification: {e}")
        ctx.fail(f"Failed during command sequence identification: {e}")
    # --- End Step 5 --- #

    # --- Podman Setup (Steps 6.3, 6.4) --- # Restore Podman Block
    container_name: Optional[str] = None  # Initialize
    podman_setup_successful = False
    if generate_baselines:
        try:
            container_name = _get_container_name(project_root)
            podman_setup_successful = _start_podman_runner(
                container_name, project_root, venv_bin_path
            )  # Pass venv_bin_path
            if not podman_setup_successful:
                log.error("Podman runner setup failed. Cannot generate baselines.")
                ctx.exit(1)
            else:
                log.info(f"Podman runner container '{container_name}' started successfully.")
        except Exception as e:
            log.exception(f"Error during Podman setup: {e}")
            if container_name:  # Attempt cleanup even if start failed midway
                try:
                    _stop_podman_runner(container_name)
                except Exception as cleanup_e:
                    log.exception(f"Error during Podman cleanup after setup failure: {cleanup_e}")
            ctx.exit(1)
    else:
        log.info("Skipping Podman setup as --generate flag was not provided.")
    # --- End Podman Setup --- #

    # --- Main Sync Logic within Podman Context --- # Restore Main Logic
    exit_code = 0
    all_errors: List[str] = []
    generated_outputs_dir = project_root / "generated_command_outputs"
    generated_outputs_dir.mkdir(parents=True, exist_ok=True)
    tool_index_path = tool_defs_dir / "tool_index.json"  # Define index path here
    initial_index_data = load_tool_index()
    final_index_data = initial_index_data.copy()
    processed_count = 0
    updated_count = 0
    skipped_count = 0

    # Timestamp for --skip-hours logic
    since_timestamp = time.time() - (ground_truth_txt_skip_hours * 3600) if ground_truth_txt_skip_hours > 0 else None

    try:
        # --- Step 6 & Parts of 7, 9, 10 (Parallel Processing) --- # Restore Parallel Processing
        if generate_baselines and not podman_setup_successful:
            log.error("Cannot proceed with baseline generation, Podman setup failed.")
            all_errors.append("Podman setup failed.")
            exit_code = 1
        elif whitelisted_sequences:
            # Only run if generate_baselines is true OR if we just need to check index/skeletons?
            # Current logic implies baseline check/gen always happens if sequences exist.
            # TODO: Revisit if sync should run without --generate to only check JSON/index.
            if not container_name and generate_baselines:
                log.error("Logic error: generate_baselines is true but container_name is not set.")
                ctx.exit(1)  # Should not happen if setup logic is correct

            # Determine max workers (e.g., based on CPU count, capped)
            # TODO: Make max_workers configurable?
            max_workers = max(1, os.cpu_count() // 2 if os.cpu_count() else 4)  # Example logic

            results, parallel_errors, processed_count = _run_parallel_baseline_processing(
                tasks_to_run=whitelisted_sequences,
                tool_defs_dir=tool_defs_dir,
                project_root=project_root,
                container_name=container_name if generate_baselines else "",  # Pass empty if not generating
                index_data=initial_index_data,
                force=force,
                since_timestamp=since_timestamp,
                ground_truth_txt_skip_hours=ground_truth_txt_skip_hours,
                generated_outputs_dir=generated_outputs_dir,
                max_workers=max_workers,
                exit_errors_limit=exit_errors,
            )
            all_errors.extend(parallel_errors)

            # Process results to update index
            final_index_data, index_errors, updated_count, skipped_count = _update_and_save_index(
                results=results,
                initial_index_data=initial_index_data,
                tool_index_path=tool_index_path,
                dry_run=dry_run,
            )
            all_errors.extend(index_errors)

            # Set exit code based on errors during parallel processing or index update
            if all_errors:
                exit_code = 1
        else:
            log.info("No whitelisted sequences to process.")
        # --- End Parallel Processing --- #

    except Exception as main_e:
        log.exception(f"Error during main sync logic: {main_e}")
        all_errors.append(f"Main sync error: {main_e}")
        exit_code = 1
    finally:
        # --- Podman Teardown (Step 6.4) --- # Restore Teardown
        if container_name:  # Only try to stop if setup was attempted/successful
            log.info(f"Attempting to stop and remove Podman container: {container_name}")
            try:
                _stop_podman_runner(container_name)
                log.info(f"Successfully stopped and removed Podman container: {container_name}")
            except Exception as cleanup_e:
                log.exception(f"Error during Podman cleanup: {cleanup_e}")
                if exit_code == 0:
                    exit_code = 1
                    all_errors.append(f"Podman cleanup error: {cleanup_e}")
        # --- End Podman Teardown --- #

    # --- Final Reporting --- # Restore Reporting
    end_time = time.time()
    duration = end_time - start_time
    log.info(
        "Sync summary",
        duration_seconds=round(duration, 2),
        processed=processed_count,
        updated=updated_count,
        skipped=skipped_count,
        errors=len(all_errors),
        exit_code=exit_code,
    )
    if all_errors:
        log.error("Sync finished with errors:", errors=all_errors)
    else:
        log.info("Sync finished successfully.")

    ctx.exit(exit_code)
