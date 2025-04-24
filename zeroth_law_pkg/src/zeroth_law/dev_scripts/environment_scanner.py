"""Scans the active uv-managed environment for executable files."""

import subprocess
import sys
import logging
from pathlib import Path
from typing import Set

log = logging.getLogger(__name__)

# Default timeout for the subprocess call
DEFAULT_TIMEOUT = 15


def get_executables_from_env() -> Set[str]:
    """Gets a set of executable base names from the active uv environment's bin/Scripts dir.

    Uses 'uv run which python' to find the interpreter and deduce the bin directory.

    Returns:
        A set of strings representing the base names of found executables (e.g., 'ruff').
        Returns an empty set if errors occur (uv not found, python not found, bin dir missing).
    """
    command = ["uv", "run", "--quiet", "--", "which", "python"]
    python_path_str: str | None = None

    try:
        # Run 'uv run which python' to find the interpreter
        log.debug(f"Running command to find python: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False, # Check return code manually
            timeout=DEFAULT_TIMEOUT,
        )

        if result.returncode != 0:
            log.error(
                f"Command '{" ".join(command)}' failed with code {result.returncode}. "
                f"Cannot determine environment bin path. Stderr: {result.stderr.strip()}"
            )
            return set()

        python_path_str = result.stdout.strip()
        if not python_path_str:
            log.error(f"Command '{" ".join(command)}' succeeded but returned empty path.")
            return set()
        log.debug(f"Found python interpreter via uv: {python_path_str}")

    except FileNotFoundError:
        log.error(f"Command 'uv' not found. Is uv installed and in PATH?")
        return set()
    except subprocess.TimeoutExpired:
        log.error(f"Command '{" ".join(command)}' timed out after {DEFAULT_TIMEOUT}s.")
        return set()
    except Exception as e:
        log.exception(f"Unexpected error finding python via uv: {e}") # Use log.exception
        return set()

    # Deduce bin/Scripts path
    try:
        python_path = Path(python_path_str).resolve()
        # Check if parent exists before accessing its parent
        if not python_path.parent.exists():
             log.error(f"Parent directory of Python interpreter does not exist: {python_path.parent}")
             return set()

        bin_path = python_path.parent
        log.debug(f"Deduced environment executable path: {bin_path}")

        if not bin_path.is_dir():
            log.error(f"Deduced executable path is not a directory: {bin_path}")
            return set()

    except Exception as e:
        log.exception(f"Error resolving Python path or finding bin directory: {e}")
        return set()

    # Scan the bin/Scripts directory
    found_executables: Set[str] = set()
    try:
        for item in bin_path.iterdir():
            # Check if it's a file and consider executable status (tricky cross-platform)
            # For simplicity, we might just check if it's a file initially.
            # A more robust check might involve os.access(item, os.X_OK) on Unix,
            # or checking extensions like .exe, .bat, .cmd on Windows.
            # For now, just list files and get base names.
            if item.is_file():
                # Use Path.stem to get the name without the final suffix (e.g., .exe)
                found_executables.add(item.stem)
        log.debug(f"Found {len(found_executables)} potential executables in {bin_path}.")
        return found_executables

    except Exception as e:
        log.exception(f"Error scanning executable directory {bin_path}: {e}")
        return set()