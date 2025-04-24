"""Reads tool configuration (whitelist/blacklist) from pyproject.toml."""

import toml
from pathlib import Path
from typing import Set, Tuple, List, Any


def load_tool_lists_from_toml(toml_path: Path) -> Tuple[Set[str], Set[str]]:
    """Loads the tool whitelist and blacklist from the specified pyproject.toml file.

    Args:
        toml_path: The path to the pyproject.toml file.

    Returns:
        A tuple containing two sets: (whitelist, blacklist).
        Returns empty sets if the file, section, or keys are missing.

    Raises:
        FileNotFoundError: If the specified toml_path does not exist.
        toml.TomlDecodeError: If the file content is not valid TOML.
        ValueError: If 'whitelist' or 'blacklist' keys exist but are not lists of strings.
    """
    if not toml_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {toml_path}")

    try:
        with open(toml_path, "r", encoding="utf-8") as f:
            data = toml.load(f)
    except toml.TomlDecodeError as e:
        # Re-raise the specific error for the test to catch
        raise toml.TomlDecodeError(f"Error decoding TOML file {toml_path}: {e}", e.msg, e.lineno)
    except Exception as e:
        # Catch other potential file reading errors
        raise IOError(f"Error reading file {toml_path}: {e}") from e

    # Safely navigate the dictionary structure
    tools_config: dict[str, Any] = data.get("tool", {}).get("zeroth-law", {}).get("tools", {})

    # Get lists, default to empty list if key is missing
    raw_whitelist: Any = tools_config.get("whitelist", [])
    raw_blacklist: Any = tools_config.get("blacklist", [])

    # Validate types
    if not isinstance(raw_whitelist, list):
        raise ValueError(
            f"Invalid type for 'whitelist' in {toml_path}: Expected list, got {type(raw_whitelist).__name__}."
        )
    if not isinstance(raw_blacklist, list):
        raise ValueError(
            f"Invalid type for 'blacklist' in {toml_path}: Expected list, got {type(raw_blacklist).__name__}."
        )

    # Ensure list items are strings (optional, could rely on later usage)
    if not all(isinstance(item, str) for item in raw_whitelist):
        raise ValueError(f"Invalid item type found in 'whitelist' in {toml_path}: All items must be strings.")
    if not all(isinstance(item, str) for item in raw_blacklist):
        raise ValueError(f"Invalid item type found in 'blacklist' in {toml_path}: All items must be strings.")

    # Convert to sets and return
    whitelist_set = set(raw_whitelist)
    blacklist_set = set(raw_blacklist)

    return whitelist_set, blacklist_set