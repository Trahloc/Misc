# File: src/zeroth_law/common/config_loader.py
"""Configuration handling for Zeroth Law.

This module loads and validates project configuration for Zeroth Law auditing.
It handles finding, parsing TOML files, and extracting the relevant config section.

The module supports both tomllib (Python 3.11+) and tomli (for older versions)
for parsing TOML configuration files.
"""

# import logging # Remove standard logging import
import os
import tomllib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List, Union, Set
import copy
import sys

import structlog  # Import structlog
import tomlkit
from .config_validation import validate_config
from pydantic import ValidationError

# Import the new parser
from .hierarchical_utils import parse_to_nested_dict, ParsedHierarchy, check_list_conflicts

# Import defaults from shared module
from zeroth_law.config_defaults import DEFAULT_CONFIG

# Import from path_utils (ensure these are available)
from zeroth_law.common.path_utils import find_project_root, ZLFProjectRootNotFoundError

# Setup logging
log = structlog.get_logger()  # Use structlog

# Constants
_CONFIG_SECTION = "tool.zeroth-law"
_CONFIG_PATH_ENV_VAR = "ZEROTH_LAW_CONFIG_PATH"
_XDG_CONFIG_HOME_ENV_VAR = "XDG_CONFIG_HOME"
_DEFAULT_XDG_CONFIG_HOME = "~/.config"
_PYPROJECT_FILENAME = "pyproject.toml"
_TOOL_SECTION_PATH = "tool.zeroth-law"

# Use built-in TOML parser directly
_TOML_LOADER = tomllib
_TOMLLIB = tomllib

# TODO: [Implement Subcommand Blacklist] Reference TODO H.14 in TODO.md - This module may need updates to parse/validate the hierarchical blacklist/whitelist syntax.


# Define base exception for type hinting/fallback
class TomlDecodeError(Exception):
    """Base exception class for TOML decoding errors."""


def _parse_hierarchical_list(raw_list: List[str]) -> Dict[str, Set[str]]:
    """Parses a list of strings with potential hierarchy into a structured dict.

    Handles entries like "tool", "tool:sub1", "tool:sub1,sub2".
    Using {"*"} to represent the entire tool being listed.
    Currently assumes only one level of subcommand hierarchy (tool:sub).
    """
    parsed_dict: Dict[str, Set[str]] = {}
    if not isinstance(raw_list, list):
        log.warning(
            "Managed tools list is not a valid list. Returning empty structure.", received_type=type(raw_list).__name__
        )
        return {}

    for entry in raw_list:
        if not isinstance(entry, str):  # Basic validation
            log.warning("Ignoring non-string entry in managed tools list.", entry=entry)
            continue

        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split(":", 1)
        tool_name = parts[0].strip()
        if not tool_name:  # Skip entries starting with ':' or empty
            continue

        if len(parts) == 1:
            # Entry is just a tool name (e.g., "pip")
            # Mark the entire tool using "*". Listing the whole tool overrides specific subs.
            log.debug("Parsed whole tool entry", tool=tool_name)
            parsed_dict[tool_name] = {"*"}  # Overwrite previous entries for this tool
        else:
            # Entry has subcommands (e.g., "safety:alert,check")
            subcommands_str = parts[1]
            # Split by comma, strip whitespace, filter out empty strings
            subcommands = {sub.strip() for sub in subcommands_str.split(",") if sub.strip()}

            if not subcommands:
                log.warning("Entry specified tool with ':' but no valid subcommands followed.", entry=entry)
                continue

            # TODO: Handle deeper nesting like tool:sub:subsub? Needs further parsing logic.
            # Current limitation: Handles only tool:sub1,sub2

            if tool_name in parsed_dict and parsed_dict[tool_name] == {"*"}:
                # Whole tool is already listed, ignore specific subcommand entries for it.
                log.debug("Ignoring subcommand entry as whole tool is listed.", tool=tool_name, subcommands=subcommands)
                continue
            else:
                # Add/update subcommands.
                if tool_name in parsed_dict:
                    parsed_dict[tool_name].update(subcommands)
                    log.debug("Updated subcommands for tool", tool=tool_name, added_subcommands=subcommands)
                else:
                    parsed_dict[tool_name] = subcommands
                    log.debug("Added new tool with subcommands", tool=tool_name, subcommands=subcommands)

    return parsed_dict


def find_pyproject_toml() -> Path | None:
    """Find pyproject.toml file in XDG config directory or by searching upwards.

    Returns:
        Path to the found pyproject.toml file or None if not found.

    """
    # Check explicit config path from environment variable
    if _CONFIG_PATH_ENV_VAR in os.environ:
        config_path = Path(os.environ[_CONFIG_PATH_ENV_VAR])
        if config_path.exists():
            return config_path

    # Check XDG config directory
    xdg_config_home = os.environ.get(_XDG_CONFIG_HOME_ENV_VAR, _DEFAULT_XDG_CONFIG_HOME)
    xdg_path = Path(xdg_config_home).expanduser() / "zeroth-law" / _PYPROJECT_FILENAME
    if xdg_path.exists():
        return xdg_path

    # Search upwards from the current directory
    current_dir = Path.cwd()
    while True:
        config_path = current_dir / _PYPROJECT_FILENAME
        if config_path.exists():
            return config_path

        # Stop if we've reached the root directory
        if current_dir == current_dir.parent:
            break

        # Move up one directory
        current_dir = current_dir.parent

    return None


def parse_toml_file(file_path: Path) -> dict[str, Any]:
    """Parse a TOML file.

    Args:
        file_path: Path to the TOML file.

    Returns:
        Dictionary containing the parsed TOML data.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        TomlDecodeError: If the file is invalid TOML.
        ImportError: If no TOML parsing library is available.
        OSError: If the file cannot be read.

    """
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    try:
        with open(file_path, "rb") as f:
            return _TOML_LOADER.load(f)
    except ImportError as e:  # Raised by _DummyTomlLoader
        log.error(f"{e}")
        raise
    except OSError as e:
        err_msg = f"Could not read config file ({file_path}): {e}"
        log.exception(err_msg)
        raise OSError(err_msg) from e
    except Exception as e:
        # Check if the exception is a TOMLDecodeError from tomllib
        is_tomllib_error = isinstance(e, tomllib.TOMLDecodeError)
        if is_tomllib_error:
            err_msg = f"Invalid TOML in config file ({file_path}): {e}"
            log.exception(err_msg)
            # Raise the base class for consistent handling upstream if needed
            raise TomlDecodeError(err_msg) from e
        # Catch any other unexpected error during loading/parsing
        err_msg = f"Unexpected error loading/parsing config file {file_path}: {e}"
        log.exception(err_msg)
        raise RuntimeError(err_msg) from e


def extract_config_section(toml_data: dict[str, Any], section_path: str) -> dict[str, Any]:
    """Extract the specified section from TOML data.

    Args:
        toml_data: Parsed TOML data.
        section_path: Dot-separated path to the section (e.g., "tool.zeroth-law").

    Returns:
        Dictionary containing the extracted section or an empty dict if section is not found.

    """
    # Split the section path into components
    path_parts = section_path.split(".")

    # Extract the first level (usually "tool")
    current_data = toml_data.get(path_parts[0], {})
    if not isinstance(current_data, dict):
        log.warning(
            "Unexpected type for [%s] section: %s. Using defaults.",
            path_parts[0],
            type(current_data).__name__,
        )
        return {}

    # Extract the nested section (usually "zeroth-law")
    if len(path_parts) > 1:
        current_data = current_data.get(path_parts[1], {})
        if not isinstance(current_data, dict):
            log.warning(
                "Unexpected type for [%s] section: %s. Using defaults.",
                section_path,
                type(current_data).__name__,
            )
            return {}

    return current_data


def merge_with_defaults(config_section: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Merge a configuration section with defaults, excluding 'actions'."""
    # Start with a copy of the defaults
    merged_config = defaults.copy()

    # Override with values from config_section, skipping 'actions'
    for key, default_value in defaults.items():
        if key in config_section:
            loaded_value = config_section[key]
            merged_config[key] = loaded_value
        # Handle keys present in config_section but not in defaults (excluding 'actions')
        elif key not in defaults and key != "actions":
            log.warning(f"Unknown configuration key '{key}' found. Ignoring.")

    # Ensure 'actions' is not in the dict passed to validation
    merged_config.pop("actions", None)

    # Validate the merged configuration (without actions)
    try:
        # Pass only the default keys for validation
        config_to_validate = {k: merged_config.get(k, defaults[k]) for k in defaults}
        validated_config_model = validate_config(config_to_validate)
        # Convert Pydantic model back to dict
        return validated_config_model.model_dump()
    except Exception as e:
        log.warning(
            "Configuration validation failed: %s. Reverting invalid values to defaults.",
            e,
            exc_info=True,  # Log traceback for validation errors
        )

        # For non-ValidationError exceptions, return the default config
        if not hasattr(e, "errors"):
            return defaults.copy()

        # Extract the valid fields from the failed validation
        valid_config = defaults.copy()
        invalid_fields = {err.get("loc", [None])[0] for err in e.errors() if err.get("loc")}

        # Keep only the valid config values from the merged config
        for key, value in merged_config.items():
            if key in defaults and key not in invalid_fields:
                valid_config[key] = value

        return valid_config


def load_action_definitions(config_section: dict[str, Any]) -> dict[str, Any]:
    """Extract the 'actions' dictionary from the main config section."""
    actions = config_section.get("actions", {})
    if not isinstance(actions, dict):
        log.warning(
            f"Invalid type for '[{_TOOL_SECTION_PATH}.actions]' section: "
            f"{type(actions).__name__}. Expected a dictionary. No actions loaded.",
        )
        return {}
    return actions


def load_config(config_path_override: str | Path | None = None) -> dict[str, Any]:
    """Load and validate Zeroth Law configuration.

    Finds pyproject.toml, parses it, extracts the [tool.zeroth-law] section,
    merges with defaults, validates, parses hierarchical lists, loads actions,
    and returns the comprehensive configuration dictionary.

    Args:
        config_path_override: Explicit path to a config file (optional).

    Returns:
        A dictionary containing the full configuration, including parsed
        whitelist/blacklist and action definitions.
        Returns DEFAULT_CONFIG if no config file is found or if errors occur.
    """
    log.debug("Attempting to load Zeroth Law configuration...")
    config_file_path: Optional[Path] = None

    # 1. Find Config File
    if isinstance(config_path_override, (str, Path)):
        config_file_path = Path(config_path_override).resolve()
        if not config_file_path.is_file():
            log.error("Config file override specified but not found.", path=str(config_file_path))
            # Consider if this should raise an error or fall back to defaults?
            # Falling back to defaults might hide issues.
            # Let's return defaults for now, consistent with finding no file.
            return copy.deepcopy(DEFAULT_CONFIG)
        log.info("Using explicit config file path.", path=str(config_file_path))
    else:
        # Search for pyproject.toml
        # Try finding project root relative to CWD first for standard cases
        try:
            project_root = find_project_root()
            if project_root:
                config_file_path = project_root / _PYPROJECT_FILENAME
                if not config_file_path.is_file():
                    config_file_path = None  # Reset if not found at project root
            if config_file_path:
                log.info("Found config file via project root search.", path=str(config_file_path))
            else:
                log.info("Config file not found via project root search. No config loaded.")
                # Return defaults if no pyproject.toml is found via upward search
                # This is the expected behavior if run outside a project.
                return copy.deepcopy(DEFAULT_CONFIG)

        except ZLFProjectRootNotFoundError:
            log.info("Project root not found. Cannot load config relative to it. Returning defaults.")
            return copy.deepcopy(DEFAULT_CONFIG)

    # Ensure we actually have a path
    if not config_file_path:
        log.warning("No configuration file found. Using default settings.")
        return copy.deepcopy(DEFAULT_CONFIG)

    # 2. Parse TOML File
    try:
        toml_data = parse_toml_file(config_file_path)
    except (FileNotFoundError, OSError, TomlDecodeError, RuntimeError):
        log.warning("Failed to load or parse config file. Using default settings.")
        return copy.deepcopy(DEFAULT_CONFIG)  # Return defaults on parse failure
    except Exception as e:
        log.exception("Unexpected error during config parsing, using defaults.", error=e)
        return copy.deepcopy(DEFAULT_CONFIG)

        # 3. Extract ZLT Section
    config_section = extract_config_section(toml_data, _TOOL_SECTION_PATH)
    if not config_section:
        log.info("No [tool.zeroth-law] section found in config. Using defaults.")
        # Return a complete default structure if section is missing
        config = copy.deepcopy(DEFAULT_CONFIG)
        # Ensure expected nested structures exist even in defaults
        config["actions"] = config.get("actions", {})
        config["managed-tools"] = config.get(
            "managed-tools", {"whitelist": [], "blacklist": []}
        )  # Add default structure
        config["parsed_whitelist"] = parse_to_nested_dict([])
        config["parsed_blacklist"] = parse_to_nested_dict([])
        return config

    # 4. Merge File Config with Defaults
    merged_config = copy.deepcopy(DEFAULT_CONFIG)  # Start with defaults
    # Update with ALL keys from the loaded config section
    # This ensures file settings override defaults and extra keys from file are included
    # We might want stricter validation later to reject unknown keys if desired.
    merged_config.update(config_section)  # Overwrite defaults with file values

    # Ensure 'managed-tools' structure exists if not present in either default or file
    # Use .setdefault to add it only if missing, preserving existing content if present
    managed_tools_data = merged_config.setdefault("managed-tools", {"whitelist": [], "blacklist": []})
    if not isinstance(managed_tools_data, dict):
        log.warning(
            "Invalid 'managed-tools' format in config, reverting to default.", found_type=type(managed_tools_data)
        )
        managed_tools_data = {"whitelist": [], "blacklist": []}
        merged_config["managed-tools"] = managed_tools_data
    managed_tools_data.setdefault("whitelist", [])
    managed_tools_data.setdefault("blacklist", [])

    # Ensure 'actions' structure exists (though it's loaded separately later)
    merged_config.setdefault("actions", {})

    validation_errors = []
    validated_config = merged_config  # Temporarily assign, will be replaced by model dump

    # 5. Validate the Fully Merged Configuration
    try:
        validated_model = validate_config(merged_config)  # Validate the merged config
        # --- DEBUG: Inspect model attribute before dump --- #
        log.debug(
            "Inspecting validated_model.managed_tools before dump",
            data=getattr(validated_model, "managed_tools", "Attribute Missing"),
        )
        # --- END DEBUG ---
        validated_config = validated_model.model_dump(mode="python")
        # --- DEBUG: Inspect dumped dictionary --- #
        log.debug(
            "Inspecting validated_config dictionary after dump",
            data=validated_config.get("managed_tools", "Key Missing"),
        )
        # --- END DEBUG ---

        log.debug("Configuration validated successfully.")

        # 6. Parse Hierarchical Whitelist/Blacklist
        # --- FIX: Access using underscore key from model dump --- #
        # raw_whitelist = validated_config["managed-tools"].get("whitelist", [])
        # raw_blacklist = validated_config["managed-tools"].get("blacklist", [])
        managed_tools_data = validated_config.get("managed_tools", {})  # Use underscore
        raw_whitelist = managed_tools_data.get("whitelist", [])
        raw_blacklist = managed_tools_data.get("blacklist", [])
        # --- END FIX --- #

        whitelist_tree = parse_to_nested_dict(raw_whitelist)
        blacklist_tree = parse_to_nested_dict(raw_blacklist)

        # --- ADD PARSED TREES TO RETURNED CONFIG --- #
        validated_config["parsed_whitelist"] = whitelist_tree
        validated_config["parsed_blacklist"] = blacklist_tree
        log.debug("Added parsed whitelist/blacklist trees to config dict.")
        # --- END ADD PARSED TREES --- #

    except Exception as e:
        log.error("Configuration validation failed. Using default settings.", error=str(e), exc_info=True)
        validation_errors.append(str(e))
        # Return defaults on validation failure
        # Make sure defaults also have the nested structures
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["actions"] = config.get("actions", {})
        config["managed-tools"] = config.get("managed-tools", {"whitelist": [], "blacklist": []})
        config["parsed_whitelist"] = parse_to_nested_dict([])
        config["parsed_blacklist"] = parse_to_nested_dict([])
        config["_validation_errors"] = validation_errors  # Include error info
        return config

    # 7. Check for conflicts between parsed trees
    conflict_errors = check_list_conflicts(whitelist_tree, blacklist_tree)
    if conflict_errors:
        conflict_details = ", ".join(conflict_errors)
        log.error(
            "Configuration conflict detected between parsed whitelist and blacklist.",
            conflicts=conflict_details,
        )
        raise ValueError(f"Explicit conflicts found: {conflict_details}")

    # 8. Load Action Definitions (from original section, not merged)
    validated_config["actions"] = load_action_definitions(config_section)
    log.debug("Loaded action definitions.", actions=list(validated_config["actions"].keys()))

    # Add validation error info if any occurred during load
    validated_config["_validation_errors"] = validation_errors

    log.info("Configuration loaded successfully.", path=str(config_file_path))
    return validated_config


def _load_python_version_constraint(
    _file_path: Path,
) -> str | None:  # ARG001 handled by prefix
    """Load the python version constraint from pyproject.toml (Placeholder/Legacy)."""
    log.warning("_load_python_version_constraint is likely legacy and unused.")
    return None


# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
"""
## LIMITATIONS & RISKS:
# - Relies on tomllib (Python 3.11+) or tomli for TOML parsing.
# - Assumes config in standard locations (XDG config dir or project hierarchy).

## REFINEMENT IDEAS:
# - Enhanced error handling for specific validation errors.
# - Support for environment variables overriding specific settings.
# - Improved logging for configuration loading sequence.

## ZEROTH LAW COMPLIANCE:
# Framework Version: v0.1.0
# Last Check: 2023-09-01
# Score: 100%
# Penalties: None
"""

# <<< ZEROTH LAW FOOTER >>>
