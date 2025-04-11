# FILE: src/zeroth_law/file_finder.py
"""Provides functions for finding relevant source files within a project.

CONTEXT:
  Developed via TDD. Initial focus is finding all Python files recursively,
  excluding common directories like virtual environments.
"""

from pathlib import Path

# import typing # Removed as unused for now


# Default directories/patterns to exclude during file search
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".nox",
    "__pycache__",
    ".venv",
    "venv",
    "build",
    "dist",
}
# Default file patterns to exclude
DEFAULT_EXCLUDE_FILES = {"*_flymake.py"}  # Example for flymake temp files
# We might want to make excludes configurable later

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


def find_python_files(
    start_path: str | Path,
    exclude_dirs: set[str] | None = None,
    exclude_files: set[str] | None = None,
) -> list[Path]:
    """Find all Python (*.py) files recursively, excluding specified dirs/files.

    PURPOSE:
      Identify target source files for analysis or other processing.

    PARAMS:
      start_path (str | Path): The directory to start searching from.
      exclude_dirs (set[str] | None): A set of directory names to exclude. Defaults to DEFAULT_EXCLUDE_DIRS.
      exclude_files (set[str] | None): A set of glob patterns for filenames to exclude. Defaults to DEFAULT_EXCLUDE_FILES.

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

    # Combine provided exclusions with defaults
    combined_exclude_dirs = DEFAULT_EXCLUDE_DIRS | (exclude_dirs if exclude_dirs is not None else set())
    combined_exclude_files = DEFAULT_EXCLUDE_FILES | (exclude_files if exclude_files is not None else set())

    found_files: list[Path] = []
    for item in root_path.rglob("*.py"):
        resolved_item = item.resolve()  # Resolve the path to get canonical absolute path
        if not resolved_item.is_file():
            continue  # Skip directories, broken symlinks etc.

        # Check directory exclusion based on resolved path parts relative to resolved root
        try:
            # Use resolved_item here
            relative_parts = resolved_item.relative_to(root_path).parts
            if any(part in combined_exclude_dirs for part in relative_parts):
                continue  # Skip if any part of the path is in excluded dirs
        except ValueError:
            # Handle case where resolved_item is not within root_path (e.g., complex symlinks)
            # For now, we'll just skip these files
            continue

        # Check filename exclusion using glob patterns on the resolved path's name
        if any(resolved_item.match(pattern) for pattern in combined_exclude_files):
            continue  # Skip if filename matches any exclude pattern

        found_files.append(resolved_item)  # Append the resolved path

    # Return a list of unique resolved paths
    return list(set(found_files))  # Ensure uniqueness using a set conversion


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

# <<< ZEROTH LAW FOOTER >>>
