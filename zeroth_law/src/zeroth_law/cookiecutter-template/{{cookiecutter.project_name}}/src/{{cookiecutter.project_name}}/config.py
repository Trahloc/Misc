"""
# PURPOSE: Configuration management.

## INTERFACES:
 - load_config(config_path: str) -> dict: Load configuration from file
 - get_config() -> dict: Get the current configuration

## DEPENDENCIES:
 - json
 - typing
"""
import json
from typing import Dict, Any, Optional

DEFAULT_CONFIG = {
    "max_line_length": 88,
    "min_docstring_length": 10,
    "max_function_length": 30,
    "max_cyclomatic_complexity": 8,
    "ignore_patterns": [
        ".*\\.pyc$",
        ".*\\.git.*",
        ".*__pycache__.*",
        ".*\\.egg-info.*"
    ]
}

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            # Merge with default config
            merged = DEFAULT_CONFIG.copy()
            merged.update(config)
            return merged
    except FileNotFoundError:
        return DEFAULT_CONFIG
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")

def get_config() -> Dict[str, Any]:
    """Get the current configuration."""
    return DEFAULT_CONFIG.copy()