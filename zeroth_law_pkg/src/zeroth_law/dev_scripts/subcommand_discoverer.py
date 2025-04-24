"""Extracts subcommand details from a tool's JSON definition file."""

import json
import logging
from pathlib import Path
from typing import Dict, Any

log = logging.getLogger(__name__)


def get_subcommands_from_json(json_path: Path) -> Dict[str, Any]:
    """Safely loads a tool's JSON definition and extracts the subcommands_detail.

    Args:
        json_path: The path to the tool's JSON definition file.

    Returns:
        A dictionary containing the subcommand details (from the
        'subcommands_detail' key in the JSON), or an empty dictionary if
        the file doesn't exist, is invalid JSON, the key is missing,
        or the value is not a dictionary.
    """
    if not json_path.is_file():
        log.debug(f"JSON definition file not found: {json_path}")
        return {}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        log.warning(f"Failed to decode JSON file {json_path}: {e}")
        return {}
    except Exception as e:
        log.error(f"Failed to read JSON file {json_path}: {e}")
        return {}

    # Get the subcommands_detail value, default to None if missing
    subcommands_detail = data.get("subcommands_detail", None)

    # Check if it's a dictionary
    if isinstance(subcommands_detail, dict):
        return subcommands_detail
    else:
        if subcommands_detail is not None:
            log.warning(
                f"Expected 'subcommands_detail' to be a dict in {json_path}, "
                f"but got {type(subcommands_detail).__name__}."
            )
        # Return empty dict if missing, null, or wrong type
        return {}
