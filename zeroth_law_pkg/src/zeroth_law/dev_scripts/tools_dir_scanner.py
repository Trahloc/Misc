"""Scans the tools directory for existing tool subdirectories."""

import logging
from pathlib import Path
from typing import Set

log = logging.getLogger(__name__)

def get_tool_dirs(tools_base_path: Path) -> Set[str]:
    """Gets the names of directories present directly under the specified base path.

    Args:
        tools_base_path: The Path object representing the base directory to scan
                         (e.g., src/zeroth_law/tools).

    Returns:
        A set of strings containing the names of the subdirectories found.
        Returns an empty set if the base path doesn't exist or contains no directories.
    """
    found_dirs: Set[str] = set()
    if not tools_base_path.is_dir():
        log.debug(f"Base tools directory not found or not a directory: {tools_base_path}")
        return found_dirs

    try:
        for item in tools_base_path.iterdir():
            if item.is_dir():
                # Add the name of the directory (tool name)
                found_dirs.add(item.name)
        log.debug(f"Found {len(found_dirs)} tool directories in {tools_base_path}.")
    except Exception as e:
        log.exception(f"Error scanning tools directory {tools_base_path}: {e}")
        return set() # Return empty set on error during scan

    return found_dirs