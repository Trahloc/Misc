# FILE: src/zeroth_law/file_finder.py
"""Provides functions for finding relevant source files within a project.

CONTEXT:
  Developed via TDD. Initial focus is finding all Python files recursively,
  excluding common directories like virtual environments.
"""

from pathlib import Path

# import typing # Removed as unused for now


# Default directories/patterns to exclude during file search
DEFAULT_EXCLUDE_DIRS = {".git", ".hg", ".svn", ".tox", ".nox", "__pycache__", ".venv", "venv", "build", "dist"}
# We might want to make excludes configurable later

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


def find_python_files(start_path: str | Path, exclude_dirs: set[str] | None = None) -> list[Path]:
    """Find all Python (*.py) files recursively from a start path, excluding specified directories.

    PURPOSE:
      Identify target source files for analysis or other processing.

    PARAMS:
      start_path (str | Path): The directory to start searching from.
      exclude_dirs (set[str] | None): A set of directory names to exclude. Defaults to DEFAULT_EXCLUDE_DIRS.

    Returns
    -------
      list[Path]: A list of Path objects for found Python files.

    EXCEPTIONS:
      FileNotFoundError: If start_path does not exist or is not a directory.

    USAGE EXAMPLES:
      >>> # Assuming a structure like:
      >>> # project/
      >>> #   main.py
      >>> #   lib/
      >>> #     utils.py
      >>> #   .venv/
      >>> #     ... (stuff)
      >>> find_python_files("project") # doctest: +SKIP
      [PosixPath('project/main.py'), PosixPath('project/lib/utils.py')]

    """
    root_path = Path(start_path).resolve()
    if not root_path.is_dir():
        msg = f"Start path must be a valid directory: {start_path}"
        raise FileNotFoundError(msg)

    # Use ternary for default excludes (SIM108)
    excludes = DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs

    found_files: list[Path] = []
    for item in root_path.rglob("*.py"):
        # Check if any part of the path relative to the root is in the exclude set
        relative_parts = item.relative_to(root_path).parts
        # Combine checks using single if (SIM102)
        if item.is_file() and not any(part in excludes for part in relative_parts):
            found_files.append(item)

    return found_files


# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
"""
## LIMITATIONS & RISKS:
# - Exclusion logic is basic (checks if any path component matches).
# - Doesn't handle symlinks explicitly (Path.rglob might follow them depending on Python version/OS).
# - Performance for very large directories might be suboptimal.

## REFINEMENT IDEAS:
# - Implement more sophisticated exclusion patterns (e.g., globs, regex, .gitignore style).
# - Make exclusions configurable via pyproject.toml.
# - Add options to include/exclude specific file names.
# - Consider using os.walk for potentially better performance/control.

## ZEROTH LAW COMPLIANCE:
# Framework Version: 2025-04-08-tdd
# TDD Cycle: Green (test_find_python_files_simple)
# Last Check: <timestamp>
# Score: <score>
# Penalties: <penalties>
"""
