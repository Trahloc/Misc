# FILE: tests/test_tool_defs/test_utils.py
"""Utility functions for tool definition tests."""

from typing import Any, Dict


# Moved from test_json_is_populated.py to break circular imports
def is_likely_skeleton(json_data: Dict[str, Any]) -> bool:
    """
    Checks if a loaded JSON object resembles the initial skeleton structure.
    This is a heuristic check.
    """
    # Check for presence of top-level keys expected in a populated file
    has_desc = bool(json_data.get("description"))
    has_options = bool(json_data.get("options"))
    has_args = bool(json_data.get("arguments"))
    has_subcommands = bool(json_data.get("subcommands"))

    # Check if essential metadata exists
    metadata = json_data.get("metadata", {})
    has_metadata = isinstance(metadata, dict)
    has_crc = has_metadata and "ground_truth_crc" in metadata

    # It's likely a skeleton if it has the crc metadata but lacks
    # description and either options or arguments or subcommands.
    # (Usage might be null even in populated files).
    is_skeleton = has_crc and not (has_desc or has_options or has_args or has_subcommands)

    # Handle cases where metadata itself might be missing (definitely not populated)
    if not has_metadata:
        return True  # Treat as skeleton if metadata block is missing

    return is_skeleton
