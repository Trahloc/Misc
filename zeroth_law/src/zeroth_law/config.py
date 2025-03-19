"""
# PURPOSE: Handle configuration for the Zeroth Law analyzer.

## INTERFACES:
 - load_config(config_path: str) -> dict

## DEPENDENCIES:
 - toml
 - typing
"""
from typing import Dict, List
import toml
from zeroth_law.exceptions import ConfigError

# Define default configuration values
DEFAULT_CONFIG: Dict = {
    "max_executable_lines": 300,
    "max_function_lines": 30,
    "max_cyclomatic_complexity": 8,
    "max_parameters": 4,
    "missing_header_penalty": 20,
    "missing_footer_penalty": 10,
    "missing_docstring_penalty": 2,
    "ignore_patterns": [
        "**/__pycache__/**",
        "**/.git/**",
        "**/.venv/**",
        "**/venv/**",
        "**/*.pyc",
        "**/.pytest_cache/**",
        "**/.coverage",
        "**/htmlcov/**"
    ]
}

def load_config(config_path: str) -> Dict:
    """Loads configuration from a TOML file."""
    try:
        config = toml.load(config_path)
        # Validate configuration (basic type checking)
        for key, value in config.items():
            if key not in DEFAULT_CONFIG:
                raise ConfigError(f"Unknown configuration option: {key}")
            if isinstance(DEFAULT_CONFIG[key], list):
                if not isinstance(value, list):
                    raise ConfigError(f"Invalid type for configuration option: {key}. Expected list, got {type(value)}")
            elif not isinstance(value, type(DEFAULT_CONFIG[key])):
                raise ConfigError(f"Invalid type for configuration option: {key}. Expected {type(DEFAULT_CONFIG[key])}, got {type(value)}")

        # Merge with defaults (so unspecified options use defaults)
        return {**DEFAULT_CONFIG, **config}

    except toml.TomlDecodeError as e:
        raise ConfigError(f"Error decoding TOML file: {e}") from e
    except FileNotFoundError as e:
        raise ConfigError(f"Configuration file not found: {config_path}") from e
    except Exception as e:
        raise ConfigError(f"Error loading configuration: {e}") from e