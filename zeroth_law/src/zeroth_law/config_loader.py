"""Provides functions for loading and accessing project configuration.

CONTEXT:
  Developed via TDD. Initial focus is loading essential configuration
  like the target Python version from pyproject.toml.

Notes
-----
  Uses tomllib (Python 3.11+) for TOML parsing.

"""

import tomllib  # Use built-in tomllib (available in Python 3.11+)
from pathlib import Path

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


def load_python_version_from_pyproject(file_path: str | Path) -> str:
    """Load pyproject.toml and return the Python version string.

    PURPOSE:
      Extract the required Python version constraint defined under
      [tool.poetry.dependencies].python.

    PARAMS:
      file_path (str | Path): Path to the pyproject.toml file.

    Returns
    -------
      str: The Python version constraint string.

    EXCEPTIONS:
      FileNotFoundError: If the specified file_path does not exist.
      KeyError: If the expected keys (tool, poetry, dependencies, python)
                are not found in the TOML structure.
      tomllib.TOMLDecodeError: If the file is not valid TOML.
      TypeError: If the loaded python version value is not a string.

    USAGE EXAMPLES:
      >>> # Assuming pyproject.toml contains python = ">=3.13,<4.0"
      >>> load_python_version_from_pyproject("pyproject.toml")
      '>=3.13,<4.0'

    """
    path = Path(file_path)
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError as err:
        msg = f"Configuration file not found: {file_path}"
        raise FileNotFoundError(msg) from err
    except tomllib.TOMLDecodeError as err:
        msg = f"Invalid TOML format in {file_path}: {err}"
        raise tomllib.TOMLDecodeError(msg) from err

    try:
        # Navigate through the nested dictionary structure
        python_version = data["tool"]["poetry"]["dependencies"]["python"]
    except KeyError as err:
        msg = f"Missing expected key path in {file_path}: tool.poetry.dependencies.{err}"
        raise KeyError(msg) from err
    else:
        if not isinstance(python_version, str):
            msg = f"Expected python version to be a string, found {type(python_version).__name__} in {file_path}"
            raise TypeError(msg)
        return python_version


# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
"""
## LIMITATIONS & RISKS:
# - Assumes standard pyproject.toml structure defined by Poetry.
# - Error handling for file I/O could be more nuanced (e.g., permissions).

## REFINEMENT IDEAS:
# - Add caching if file is loaded frequently.
# - Create a dedicated Config class to hold loaded values.
# - Abstract file loading to handle different config formats potentially.

## ZEROTH LAW COMPLIANCE:
# Framework Version: 2025-04-08-tdd
# TDD Cycle: Green (test_load_python_version_success)
# Last Check: <timestamp>
# Score: <score>
# Penalties: <penalties>
"""
