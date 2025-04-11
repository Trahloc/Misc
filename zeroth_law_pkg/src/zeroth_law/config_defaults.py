"""Default configuration values for Zeroth Law.

This module contains the default values for all configuration options.
These are used as fallbacks when no custom configuration is provided.
"""

from typing import Any

# Default configuration values
DEFAULT_CONFIG: dict[str, Any] = {
    "exclude_dirs": [
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
    ],
    "exclude_files": [],
    "max_lines": 100,
    "max_complexity": 10,
    "max_parameters": 5,
    "max_statements": 50,
    "ignore_rules": [],
}
