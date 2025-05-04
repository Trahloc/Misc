# FILE: src/zeroth_law/subcommands/tools/sync/_start_podman_runner.py
"""Helper function for Stage 1: Starting the Podman baseline runner."""

import time
import shutil
import subprocess
import sys
from pathlib import Path
import structlog
import os

# --- Import project modules --- #
# Relative path needs adjustment (add one more dot)
from ....lib.tooling.podman_utils import _run_podman_command
from ._stop_podman_runner import _stop_podman_runner  # Import sibling helper

log = structlog.get_logger()


def _start_podman_runner(
    container_name: str,
    project_root: Path,
    venv_path: Path,
    read_only_app: bool = False,
) -> bool:
    """STAGE 1: Starts the podman container, creates internal venv, and installs deps."""
    log.info(f"STAGE 1: Attempting to start Podman baseline runner: {container_name} (App RO: {read_only_app})")

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
        build_result = subprocess.run(build_cmd, cwd=project_root, check=False, capture_output=True, text=True)

        # --- Always log build output --- #
        log.debug(f"Build command stdout:\n{build_result.stdout}")
        if build_result.stderr:
            log.warning(f"Build command stderr:\n{build_result.stderr}")
        # --- End Log --- #

        if build_result.returncode != 0:
            raise subprocess.CalledProcessError(
                build_result.returncode, build_cmd, output=build_result.stdout, stderr=build_result.stderr
            )

        # --- Add delay and debug logging for wheel finding --- #
        time.sleep(0.1)  # Short delay for filesystem operations
        log.debug(f"Checking for wheel file in: {wheel_dir}")
        try:
            dir_contents = os.listdir(wheel_dir)
            log.debug(f"Contents of {wheel_dir}: {dir_contents}")
        except FileNotFoundError:
            log.error(f"Wheel directory {wheel_dir} does not exist after build!")
        # --- End Debug --- #

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
        app_mount_mode = "ro" if read_only_app else "rw"
        log.debug(f"Setting /app mount mode to: {app_mount_mode}")
        _run_podman_command(
            [
                "run",
                "--rm",
                "-d",
                "--name",
                container_name,
                # --- Conditionally set RO/RW for /app --- #
                f"--volume={str(project_root.resolve())}:/app:{app_mount_mode}",
                # --- End Conditional Mount --- #
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
                _run_podman_command(
                    ["exec", container_name, "/venv/bin/pip", "install", "uv"],
                    check=True,
                )
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
            _run_podman_command(
                ["cp", str(host_req_file), f"{container_name}:{container_req_file}"],
                check=True,
            )
            log.info(f"Copying {local_wheel_path.name} to {container_name}:{container_wheel_file}...")
            _run_podman_command(
                [
                    "cp",
                    str(local_wheel_path),
                    f"{container_name}:{container_wheel_file}",
                ],
                check=True,
            )
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
                status_check_cmd = [
                    "podman",
                    "ps",
                    "-f",
                    f"name={container_name}",
                    "--format",
                    "{{.Status}}",
                ]
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
