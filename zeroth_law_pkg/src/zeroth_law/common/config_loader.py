# File: src/zeroth_law/config_loader.py
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

import structlog  # Import structlog
import tomlkit
from .config_validation import validate_config

# Import the new parser
from .hierarchical_utils import parse_to_nested_dict, ParsedHierarchy

# Import defaults from shared module
from zeroth_law.config_defaults import DEFAULT_CONFIG

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
    """Load Zeroth Law config, process actions separately, merge rest with defaults.

    Parses managed-tools whitelist/blacklist into structured dictionaries.
    """
    # Find the config file
    found_path: Path | None
    if config_path_override is None:
        found_path = find_pyproject_toml()
        if found_path is None:
            log.warning("No config file found (XDG or upwards search). Using defaults + empty actions/managed.")
            # Return structure including expected keys, even if empty
            final_config = DEFAULT_CONFIG.copy()
            final_config["actions"] = {}
            # Use the parsed (empty) structure
            final_config["managed-tools"] = {
                "whitelist": {},  # Parsed structure is dict
                "blacklist": {},  # Parsed structure is dict
            }
            return final_config
    else:
        found_path = Path(config_path_override)

    if not found_path or not found_path.exists():
        # If no config file found, return defaults + empty actions/managed
        log.warning(f"Config file not found at {found_path}. Using defaults + empty actions/managed.")
        final_config = DEFAULT_CONFIG.copy()
        final_config["actions"] = {}
        final_config["managed-tools"] = {
            "whitelist": {},
            "blacklist": {},
        }
        return final_config

    try:
        # Parse the TOML file
        toml_data = parse_toml_file(found_path)
        # Extract the main tool section
        config_section = extract_config_section(toml_data, _TOOL_SECTION_PATH)

        # Get the core config settings (excluding actions and managed-tools initially)
        core_config_settings = {k: v for k, v in config_section.items() if k not in ("actions", "managed-tools")}

        # Merge core settings with defaults and validate
        merged_core_config = merge_with_defaults(core_config_settings, DEFAULT_CONFIG)

        # Extract actions config
        actions_config = load_action_definitions(config_section)

        # Extract and parse managed-tools config
        managed_tools_config = config_section.get("managed-tools", {})
        raw_whitelist = managed_tools_config.get("whitelist", [])
        raw_blacklist = managed_tools_config.get("blacklist", [])

        # --- Use the new nested parser --- #
        parsed_whitelist: ParsedHierarchy = parse_to_nested_dict(raw_whitelist)
        parsed_blacklist: ParsedHierarchy = parse_to_nested_dict(raw_blacklist)

        final_config = merged_core_config
        final_config["actions"] = actions_config
        final_config["managed-tools"] = {
            "whitelist": parsed_whitelist,
            "blacklist": parsed_blacklist,
        }

        log.debug(f"Successfully loaded and processed config from: {found_path}")
        # <<<--- ADDED DEBUG PRINT --- >>>
        log.debug("Final loaded config (managed-tools parsed)", managed_tools=final_config["managed-tools"])
        # <<<--- END ADDED DEBUG PRINT --- >>>
        return final_config

    except Exception as e:
        log.error(
            f"Failed to load or process config file {found_path}: {e}. Using defaults.",
            exc_info=True,
        )
        # Return defaults + empty parsed structure on any load error
        final_config = DEFAULT_CONFIG.copy()
        final_config["actions"] = {}
        final_config["managed-tools"] = {
            "whitelist": {},
            "blacklist": {},
        }
        return final_config


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
