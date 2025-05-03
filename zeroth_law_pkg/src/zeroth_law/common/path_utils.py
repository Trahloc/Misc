# File: src/zeroth_law/common/path_utils.py
"""Path-related utility functions."""

import os
import structlog
from pathlib import Path
from typing import List

log = structlog.get_logger()


# Define a custom exception for clarity
class ZLFProjectRootNotFoundError(FileNotFoundError):
    """Raised when the ZLF project root (pyproject.toml + src/ + tests/) cannot be found."""

    pass


def find_project_root(start_path: Path) -> Path:
    """Searches upwards from start_path for a ZLF project root directory.

    A ZLF project root is defined as a directory containing:
    1. A 'pyproject.toml' file.
    2. A 'src' directory.
    3. A 'tests' directory.

    Args:
        start_path: The directory to start searching from.

    Returns:
        The Path to the ZLF project root directory.

    Raises:
        ZLFProjectRootNotFoundError: If the ZLF project root cannot be found.
    """
    current_path = start_path.resolve()
    while True:
        log.debug(f"Checking for ZLF project root structure in: {current_path}")

        pyproject_path = current_path / "pyproject.toml"
        src_path = current_path / "src"
        tests_path = current_path / "tests"

        # Check if all three components exist
        has_pyproject = pyproject_path.is_file()
        has_src = src_path.is_dir()
        has_tests = tests_path.is_dir()
        log.debug(f"  - pyproject.toml exists? {has_pyproject}")
        log.debug(f"  - src/ exists? {has_src}")
        log.debug(f"  - tests/ exists? {has_tests}")

        if has_pyproject and has_src and has_tests:
            log.info(f"Found ZLF project root at: {current_path}")
            return current_path
        elif has_pyproject:
            # Found pyproject.toml but not the required ZLF structure
            log.debug(
                f"Found pyproject.toml at {current_path}, but missing 'src' ({has_src}) or 'tests' ({has_tests}). Continuing search upwards."
            )
            # Continue searching upwards without returning this path

        parent = current_path.parent
        log.debug(f"Checking parent directory: {parent}")
        if parent == current_path:
            # Reached the filesystem root
            error_msg = f"Could not find ZLF project root (pyproject.toml + src/ + tests/) starting from {start_path}"
            log.error(error_msg)
            raise ZLFProjectRootNotFoundError(error_msg)
        current_path = parent

    # If we somehow exit the loop unexpectedly (shouldn't happen with the parent check)
    # return None # This line is unreachable due to the loop structure


def list_executables_in_venv_bin(venv_bin_path: Path) -> List[str]:
    """Lists executable files within the specified virtual environment bin directory.

    Args:
        venv_bin_path: The Path to the virtual environment's bin directory.

    Returns:
        A list of filenames for executable files found in the directory.

    Raises:
        FileNotFoundError: If the provided venv_bin_path does not exist or is not a directory.
    """
    if not venv_bin_path.is_dir():
        err_msg = f"Virtual environment bin directory not found or is not a directory: {venv_bin_path}"
        log.error(err_msg)
        raise FileNotFoundError(err_msg)

    executables = []
    try:
        for item in venv_bin_path.iterdir():
            # Check if it's a file and if it has execute permission for the owner
            if item.is_file() and os.access(item, os.X_OK):
                executables.append(item.name)
    except OSError as e:
        log.exception(f"Error listing executables in {venv_bin_path}: {e}")
        # Propagate the error or return an empty list? Let's propagate for now.
        raise

    log.debug(f"Found {len(executables)} executables in {venv_bin_path}")
    return executables
