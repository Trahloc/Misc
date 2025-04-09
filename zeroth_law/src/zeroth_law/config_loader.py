# FILE: src/zeroth_law/config_loader.py
"""Loads and validates project configuration for Zeroth Law auditing.

Handles reading settings from pyproject.toml.

CONTEXT:
  Developed via TDD. Initial focus is loading essential configuration
  like the target Python version from pyproject.toml.

Notes
-----
  Uses tomllib (Python 3.11+) for TOML parsing.

"""

import logging
import sys
from pathlib import Path
from typing import Any

import xdg

# --- TOML Library Handling --- #

# Keep track of which loader is available
_TOML_LOADER: Any = None
_TOMLLIB_FOUND = False
_TOMLI_FOUND = False

try:
    import tomllib

    _TOML_LOADER = tomllib
    _TOMLLIB_FOUND = True
except ImportError:
    try:
        import tomli

        _TOML_LOADER = tomli
        _TOMLI_FOUND = True
    except ImportError:
        pass  # No loader found


# Define base exception for type hinting, real exception is caught below
class TomlDecodeError(Exception):
    """Base exception class for TOML decoding errors."""


class _DummyTomlLoader:
    """Dummy class for placeholder TOML parsing when no library is installed."""

    @staticmethod
    # type: ignore[no-untyped-def]
    def load(*_args: Any, **_kwargs: Any) -> dict[str, Any]:  # ANN401 ignored
        """Raise ImportError indicating missing TOML library."""
        err_msg = "TOML library (tomllib or tomli) not found. Cannot parse pyproject.toml."
        raise ImportError(err_msg)


if _TOML_LOADER is None:
    _TOML_LOADER = _DummyTomlLoader()


log = logging.getLogger(__name__)

# Default configuration values
_CONFIG_SECTION = "tool.zeroth-law"
DEFAULT_CONFIG: dict[str, Any] = {
    "exclude_dirs": [".git", ".hg", ".svn", ".tox", ".venv", "__pycache__", "build", "dist"],
    "exclude_files": [],
    "ignore_codes": [],
    "max_lines": 100,
    "max_complexity": 10,
}


def find_pyproject_toml(start_path: Path | None = None) -> Path | None:
    """Find Zeroth Law config, check XDG dir then search upwards.

    Looks for:
    1. $XDG_CONFIG_HOME/zeroth_law/pyproject.toml (or default ~/.config/)
    2. pyproject.toml in start_path (or cwd) or its parents.

    Args:
    ----
        start_path: The directory to start the upward search from. Defaults to CWD.

    Returns:
    -------
        The Path object of the found config file, or None if not found.

    """
    # 1. Check XDG config location
    xdg_base_dir: Path = xdg.xdg_config_home()
    xdg_config_path = xdg_base_dir / "zeroth_law" / "pyproject.toml"
    log.debug("Checking XDG config path: %s", xdg_config_path)
    if xdg_config_path.is_file():
        log.debug("Found config in XDG directory.")
        return xdg_config_path

    # 2. Search upwards from start_path (or cwd)
    current_path = Path(start_path) if start_path else Path.cwd()
    log.debug("Searching for pyproject.toml upwards from: %s", current_path)
    # Iterate using sequence unpacking
    for parent_dir in (current_path, *current_path.parents):
        potential_path = parent_dir / "pyproject.toml"
        if potential_path.is_file():
            log.debug("Found config at: %s", potential_path)
            return potential_path

    log.debug("No pyproject.toml found in XDG or parent directories.")
    return None


def load_config(config_path_override: str | Path | None = None) -> dict[str, Any]:  # noqa: C901, PLR0912
    """Load Zeroth Law config, merge with defaults.

    Search XDG path and parent dirs for pyproject.toml if config_path_override is None.

    Args:
    ----
        config_path_override: Explicit path to the config file (e.g., pyproject.toml).
                              If None, searches automatically (XDG, then upwards).

    Returns:
    -------
        A dictionary containing the loaded and validated configuration.

    Raises:
    ------
        FileNotFoundError: If an explicitly specified config_path_override is not found.
        TomlDecodeError: If the found or specified config file is invalid TOML.
        ImportError: If no TOML parsing library (tomllib/tomli) is installed.
        OSError: If the config file cannot be read.

    """
    found_path: Path | None
    if config_path_override is None:
        found_path = find_pyproject_toml()
        if found_path is None:
            log.warning("No config file found (XDG or upwards search). Using defaults.")
            return DEFAULT_CONFIG.copy()
    else:
        found_path = Path(config_path_override)
        if not found_path.is_file():
            err_msg = f"Config file not found: {found_path}"
            log.error(err_msg)
            raise FileNotFoundError(err_msg)

    log.debug("Loading configuration from: %s", found_path)
    loaded_config = DEFAULT_CONFIG.copy()
    data: dict[str, Any] = {}

    try:
        with found_path.open("rb") as f:
            data = _TOML_LOADER.load(f)
    # Catch specific errors if libraries were found
    except getattr(sys.modules.get("tomllib"), "TOMLDecodeError", TomlDecodeError) as e_toml:
        if _TOMLLIB_FOUND:
            err_msg = f"Invalid TOML in config file ({found_path}): {e_toml}"
            log.exception(err_msg)  # Use log.exception (TRY400)
            raise TomlDecodeError(err_msg) from e_toml
        # If tomllib wasn't found, this exception shouldn't be caught here
        # unless tomli error inherits from base Exception and base TomlDecodeError is Exception
        # Fall through to potentially catch tomli error or base Exception
    except getattr(sys.modules.get("tomli"), "TOMLDecodeError", TomlDecodeError) as e_tomli:
        if _TOMLI_FOUND:
            err_msg = f"Invalid TOML in config file ({found_path}): {e_tomli}"
            log.exception(err_msg)  # Use log.exception (TRY400)
            raise TomlDecodeError(err_msg) from e_tomli
        # Fall through if tomli wasn't the loaded library
    except OSError as e:
        err_msg = f"Could not read config file ({found_path}): {e}"
        log.exception(err_msg)  # Use log.exception (TRY400)
        raise OSError(err_msg) from e
    except ImportError as e:
        # Raised by _DummyTomlLoader
        log.error(e)
        raise
    except Exception as e:
        # Catch any other unexpected error during loading/parsing
        err_msg = f"Unexpected error loading/parsing config file {found_path}: {e}"
        log.exception(err_msg)  # Use log.exception (TRY400)
        raise RuntimeError(err_msg) from e

    tool_data = data.get("tool", {})
    if not isinstance(tool_data, dict):
        log.warning("Unexpected type for [tool] section in %s: %s. Using defaults.", found_path, type(tool_data).__name__)
        return loaded_config

    config_section = tool_data.get(_CONFIG_SECTION, {})
    if not isinstance(config_section, dict):
        log.warning(
            "Unexpected type for [%s] section in %s: %s. Using defaults.", _CONFIG_SECTION, found_path, type(config_section).__name__
        )
        return loaded_config

    for key, default_value in DEFAULT_CONFIG.items():
        if key in config_section:
            loaded_value = config_section[key]
            if isinstance(loaded_value, type(default_value)):
                loaded_config[key] = loaded_value
            else:
                log.warning(
                    "Invalid type for '%s' in config %s: Expected %s, got %s. Using default.",
                    key,
                    found_path,
                    type(default_value).__name__,
                    type(loaded_value).__name__,
                )
    log.debug("Final configuration: %s", loaded_config)
    return loaded_config


def _load_python_version_constraint(_file_path: Path) -> str | None:  # ARG001 handled by prefix
    """Load the python version constraint from pyproject.toml (Placeholder/Legacy)."""
    log.warning("_load_python_version_constraint is likely legacy and unused.")
    return None


# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
"""
## LIMITATIONS & RISKS:
# - Currently only stubs, no real loading or validation.
# - Assumes pyproject.toml exists in a predictable location relative to source.

## REFINEMENT IDEAS:
# - Implement actual TOML parsing using `tomllib` (Python 3.11+).
# - Use Pydantic for validation of the [tool.zeroth-law] section.
# - Add error handling for missing file or invalid TOML.
# - Provide default values for settings.

## ZEROTH LAW COMPLIANCE:
# Framework Version: <Specify Framework Version>
# TDD Cycle: <Specify Test Status (e.g., Red, Green, Refactor)>
# Last Check: <Timestamp>
# Score: <Score>
# Penalties: <Penalties>
"""

# <<< ZEROTH LAW FOOTER >>>
