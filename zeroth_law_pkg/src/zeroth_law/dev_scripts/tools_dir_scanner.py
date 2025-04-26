"""Scans the tools directory for existing tool subdirectories."""

import logging
from pathlib import Path
from typing import Set

log = logging.getLogger(__name__)


def get_tool_dirs(base_dir: Path) -> Set[str]:
    """
    Scans the base directory for actual tool directories.

    Handles two structures:
    1. Grouping directories (single letters like 'a', 'b', ...) containing tool directories.
    2. Tool directories placed directly under the base_dir.

    Args:
        base_dir: The base directory to scan (e.g., src/zeroth_law/tools).

    Returns:
        A set of actual tool directory names found.
    """
    actual_tool_dirs: Set[str] = set()
    print(f"DEBUG [get_tool_dirs]: Scanning base directory: {base_dir}")

    if not base_dir.is_dir():
        log.warning(f"Tools directory not found: {base_dir}")
        return actual_tool_dirs

    for item in base_dir.iterdir():
        if item.is_dir():
            item_name = item.name
            # Case 1: Grouping directory (single letter)
            if len(item_name) == 1 and item_name.isalpha():
                print(f"DEBUG [get_tool_dirs]: Found grouping directory: {item_name}")
                for sub_item in item.iterdir():
                    if sub_item.is_dir():
                        print(f"DEBUG [get_tool_dirs]: Found nested tool directory: {sub_item.name} in {item_name}")
                        actual_tool_dirs.add(sub_item.name)
                    # Optionally handle files directly inside grouping dirs if needed
            # Case 2: Potential direct tool directory (not a single letter)
            elif len(item_name) > 1:
                # Check if it looks like a tool dir (e.g., contains <dir_name>.json)
                # This check might need refinement based on exact tool dir structure rules
                if (item / f"{item_name}.json").is_file():
                    print(f"DEBUG [get_tool_dirs]: Found potential direct tool directory: {item_name}")
                    actual_tool_dirs.add(item_name)
                else:
                    print(f"DEBUG [get_tool_dirs]: Skipping direct item (not a tool dir): {item_name}")

    print(f"DEBUG [get_tool_dirs]: Final set returned: {sorted(list(actual_tool_dirs))}")
    return actual_tool_dirs
