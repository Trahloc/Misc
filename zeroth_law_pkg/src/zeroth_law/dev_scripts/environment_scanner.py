"""Scans the active uv-managed environment for executable files."""

import subprocess
import sys
import logging
from pathlib import Path
from typing import Set

# Import the new helper
from zeroth_law.utils.subprocess_utils import run_subprocess_no_check

log = logging.getLogger(__name__)

# Default timeout for the subprocess call
DEFAULT_TIMEOUT = 15


def get_executables_from_env(whitelist: Set[str], dir_tools: Set[str]) -> Set[str]:
    """Gets a set of executable base names from the active uv environment's bin/Scripts dir.

    Uses 'uv run which python' to find the interpreter and deduce the bin directory.
    Filters results to include only stems that are whitelisted or match a tool directory name,
    and excludes dotfiles.

    Args:
        whitelist: Set of whitelisted tool names from configuration.
        dir_tools: Set of tool directory names found in the tools definition directory.

    Returns:
        A set of strings representing the base names of likely relevant executables.
        Returns an empty set if errors occur (uv not found, python not found, bin dir missing).
    """
    command = ["uv", "run", "--quiet", "--", "which", "python"]
    python_path_str: str | None = None

    try:
        # Run 'uv run which python' to find the interpreter
        log.debug(f"Running command to find python: {' '.join(command)}")
        result = run_subprocess_no_check(command, timeout_seconds=DEFAULT_TIMEOUT)

        if result.returncode != 0:
            log.error(
                f"Command '{' '.join(command)}' failed with code {result.returncode}. "
                f"Cannot determine environment bin path. Stderr: {result.stderr.strip() if result.stderr else '[None]'}"
            )
            return set()

        python_path_str = result.stdout.strip()
        if not python_path_str:
            log.error(f"Command '{' '.join(command)}' succeeded but returned empty path.")
            return set()
        log.debug(f"Found python interpreter via uv: {python_path_str}")

    except FileNotFoundError:
        log.error(f"Command 'uv' not found. Is uv installed and in PATH?")
        return set()
    except subprocess.TimeoutExpired:
        log.error(f"Command '{' '.join(command)}' timed out after {DEFAULT_TIMEOUT}s.")
        return set()
    except Exception as e:
        log.exception(f"Unexpected error finding python via uv: {e}")  # Use log.exception
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
    likely_executables: Set[str] = set()
    try:
        for item in bin_path.iterdir():
            # Ignore hidden files/directories (starting with .)
            if item.name.startswith("."):
                log.debug(f"Ignoring hidden item: {item.name}")
                continue

            # Basic check: is it a file?
            if item.is_file():
                stem = item.stem  # Get name without final suffix
                # --- MODIFIED FILTER --- START
                # Keep only if stem is whitelisted OR matches a tool directory
                if stem in whitelist or stem in dir_tools:
                    likely_executables.add(stem)
                    log.debug(f"Keeping likely tool executable: {stem} (from {item.name})")
                else:
                    log.debug(f"Ignoring file stem '{stem}' (from {item.name}) - not whitelisted or in dir_tools.")
                # --- MODIFIED FILTER --- END

        log.debug(f"Found {len(likely_executables)} likely tool executables in {bin_path}.")
        return likely_executables

    except Exception as e:
        log.exception(f"Error scanning executable directory {bin_path}: {e}")
        return set()
