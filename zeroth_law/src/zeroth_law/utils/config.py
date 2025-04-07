"""Configuration utilities for the Zeroth Law analyzer.

This module provides functions for loading and validating configuration
for the Zeroth Law analyzer.

# PURPOSE: Configuration management for Zeroth Law.

## INTERFACES:
 - load_config: Load and validate configuration from file
 - find_pylintrc: Find and load appropriate pylintrc configuration

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
 - tomllib
 - configparser
"""

from typing import Dict, List, Any
import toml
from zeroth_law.exceptions import ConfigError
import logging
import os
from pathlib import Path
from typing import Optional
import configparser

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "max_executable_lines": 300,
    "max_function_lines": 30,
    "max_cyclomatic_complexity": 8,
    "max_parameters": 4,
    "max_line_length": 140,
    "max_locals": 15,
    "missing_header_penalty": 20,
    "missing_footer_penalty": 10,
    "missing_docstring_penalty": 2,
    "unused_import_penalty": 10,
    "ignore_patterns": [
        "**/__pycache__/**",
        "**/.git/**",
        "**/.venv/**",
        "**/venv/**",
        "**/*.pyc",
        "**/.pytest_cache/**",
        "**/.coverage",
        "**/htmlcov/**",
        ".*\\.egg-info.*",
    ],
}


def find_pylintrc(config_path: str) -> Optional[Dict]:
    """Find and load pylintrc configuration.

    Args:
        config_path: Path to the configuration file or directory

    Returns:
        Dictionary containing pylint configuration or None if not found
    """
    # If config_path is a directory, use it directly
    if os.path.isdir(config_path):
        start_dir = Path(config_path)
    else:
        # If it's a file, use its parent directory
        start_dir = Path(config_path).parent

    # Start from the directory and work up
    current_dir = start_dir
    while current_dir != current_dir.parent:  # Stop at root
        pylintrc = current_dir / ".pylintrc"
        if pylintrc.exists():
            try:
                config = configparser.ConfigParser()
                config.read(pylintrc)
                return {s: dict(config.items(s)) for s in config.sections()}
            except Exception as e:
                logger.warning(f"Failed to parse {pylintrc}: {e}")
                return None
        current_dir = current_dir.parent
    return None


def load_config(config_path: Optional[str] = None) -> Dict:
    """Load and validate configuration from file.

    This function loads configuration from a TOML file if provided,
    otherwise uses default values. It also attempts to load pylint
    configuration and merge it with the default configuration.

    Args:
        config_path (Optional[str]): Path to configuration file

    Returns:
        Dict: Configuration dictionary

    Raises:
        ConfigError: If configuration file is invalid
    """
    # Start with default config
    config = DEFAULT_CONFIG.copy()

    # Load TOML configuration if provided and it's a file
    if config_path and os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                toml_config = toml.loads(f.read())
                config.update(toml_config)
        except Exception as e:
            raise ConfigError(f"Failed to load configuration file: {e}")

    # Load pylint configuration if available
    if config_path:
        pylint_config = find_pylintrc(config_path)
        if pylint_config:
            # Map pylint configuration to our metrics
            if "FORMAT" in pylint_config:
                if "max-line-length" in pylint_config["FORMAT"]:
                    config["max_line_length"] = int(pylint_config["FORMAT"]["max-line-length"])

            if "DESIGN" in pylint_config:
                if "max-args" in pylint_config["DESIGN"]:
                    config["max_parameters"] = int(pylint_config["DESIGN"]["max-args"])
                if "max-locals" in pylint_config["DESIGN"]:
                    config["max_locals"] = int(pylint_config["DESIGN"]["max-locals"])
                if "max-statements" in pylint_config["DESIGN"]:
                    config["max_function_lines"] = int(pylint_config["DESIGN"]["max-statements"])

    return config


def get(key: str, default: Any = None) -> Any:
    """Get a configuration value.

    Args:
        key (str): The configuration key to get
        default (Any): Default value if key not found

    Returns:
        Any: The configuration value or default
    """
    config = load_config()
    return config.get(key, default)
