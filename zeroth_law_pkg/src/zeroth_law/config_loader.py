# File: src/zeroth_law/config_loader.py
"""Configuration handling for Zeroth Law.

This module loads and validates project configuration for Zeroth Law auditing.
It handles finding, parsing TOML files, and extracting the relevant config section.

The module supports both tomllib (Python 3.11+) and tomli (for older versions)
for parsing TOML configuration files.
"""

import logging
import os
import tomllib
from pathlib import Path
from typing import Any

import structlog

# Import defaults from shared module
from zeroth_law.config_defaults import DEFAULT_CONFIG
from zeroth_law.config_validation import validate_config

# Setup logging
log = structlog.get_logger()

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


# Define base exception for type hinting/fallback
class TomlDecodeError(Exception):
    """Base exception class for TOML decoding errors."""


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
    """Load Zeroth Law config, process actions separately, merge rest with defaults."""
    # Find the config file
    found_path: Path | None
    if config_path_override is None:
        found_path = find_pyproject_toml()
        if found_path is None:
            log.warning("No config file found (XDG or upwards search). Using defaults.")
            final_config = DEFAULT_CONFIG.copy()
            final_config["actions"] = {}
            return final_config
    else:
        found_path = Path(config_path_override)

    if not found_path or not found_path.exists():
        # If no config file found, return defaults + empty actions
        log.debug("No config file found. Returning default config with empty actions.")
        final_config = DEFAULT_CONFIG.copy()
        final_config["actions"] = {}
        return final_config

    try:
        # Parse the TOML file
        toml_data = parse_toml_file(found_path)
        # Extract the main tool section
        config_section = extract_config_section(toml_data, _TOOL_SECTION_PATH)

        # Separate actions from the rest of the config
        actions_config = load_action_definitions(config_section)  # Use the dedicated function
        # Create a copy of the section without actions for merging with defaults
        config_section_without_actions = {k: v for k, v in config_section.items() if k != "actions"}

        # Merge the non-actions part with defaults and validate
        merged_validated_config = merge_with_defaults(config_section_without_actions, DEFAULT_CONFIG)

        # Combine the validated/merged part with the original actions
        final_config = merged_validated_config
        final_config["actions"] = actions_config

        return final_config

    except (FileNotFoundError, TomlDecodeError, ImportError, OSError) as e:
        log.error(f"Failed to load config from {found_path}: {e}")
        # Return defaults + empty actions on load error
        final_config = DEFAULT_CONFIG.copy()
        final_config["actions"] = {}
        return final_config
    except Exception as e:
        log.exception(f"Unexpected error loading config from {found_path}. Returning defaults.", exc_info=e)
        final_config = DEFAULT_CONFIG.copy()
        final_config["actions"] = {}
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
