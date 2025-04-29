# New file: src/zeroth_law/file_processor.py
"""
Handles finding and filtering files based on CLI input and configuration.
"""

import fnmatch
import structlog
import sys
from pathlib import Path
from typing import Any, List, Set, Generator, Tuple
from zeroth_law.common.file_finder import find_python_files
from zeroth_law.common.config_loader import load_config
from zeroth_law.analyzer.python.analyzer import analyze_file_compliance

log = structlog.get_logger()


# --- Core File Finding Logic ---
def find_files_to_audit(paths_to_check: list[Path], recursive: bool, config: dict[str, Any]) -> list[Path]:
    """Finds all Python files to be audited based on input paths and config."""
    # Get exclusion patterns from config
    exclude_dirs = config.get("exclude_dirs", [])
    exclude_files = config.get("exclude_files", [])
    exclude_dirs_set = set(exclude_dirs)
    exclude_files_set = set(exclude_files)
    log.debug(f"Excluding dirs: {exclude_dirs_set}")
    log.debug(f"Excluding files: {exclude_files_set}")

    all_python_files: list[Path] = []
    for path in paths_to_check:
        if not path.exists():
            log.warning(f"Path does not exist, skipping: {path}")
            continue  # Skip non-existent paths

        if path.is_file():
            # Check exclusion for explicitly passed files
            if path.name in exclude_files_set:
                log.debug(f"Excluding explicitly provided file due to config: {path}")
                continue
            # Check if it's a Python file (simple check for now, align with find_python_files later if needed)
            if path.suffix == ".py":
                all_python_files.append(path)
            else:
                log.debug(f"Skipping non-Python file provided directly: {path}")
        elif path.is_dir():
            if not recursive:
                log.warning(f"Directory found but recursive search is off, skipping: {path}")
                continue
            # Avoid recursing into excluded dirs top-level check
            if path.name in exclude_dirs_set:
                log.debug(f"Skipping excluded directory at top level: {path}")
                continue
            try:
                # Find Python files in the directory
                found = find_python_files(
                    path,  # Pass the directory path
                    exclude_dirs=exclude_dirs_set,
                    exclude_files=exclude_files_set,
                )
                all_python_files.extend(found)
            except Exception as e:
                log.error(f"Error finding files in directory {path}: {e}")
        else:
            log.warning(f"Path is not a file or directory, skipping: {path}")

    # Remove duplicates and sort
    unique_python_files = sorted(list(set(all_python_files)))
    log.info("Found %d unique Python files to analyze.", len(unique_python_files))

    return unique_python_files
