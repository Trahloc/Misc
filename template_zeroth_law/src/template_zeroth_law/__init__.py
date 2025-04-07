# FILE: template_zeroth_law/src/template_zeroth_law/__init__.py
"""
# PURPOSE: Main package initialization and version definition.

## INTERFACES:
 - __version__: Version string for the template_zeroth_law package
 - ZerothLawError: Base exception class
 - ConfigError: Configuration error class
 - ValidationError: Validation error class
 - FileError: File operation error class
 - Config: Configuration management class
 - get_config: Get config singleton
 - load_config: Load configuration from file

## DEPENDENCIES: None
## TODO: Customize exports based on your project's needs
"""

__version__ = "0.1.0"

# Import and expose key functionality
from template_zeroth_law.exceptions import (
    ZerothLawError,
    ConfigError,
    ValidationError,
    FileError,
)
from template_zeroth_law.config import Config, get_config, load_config

# Explicitly define what's available when using 'from template_zeroth_law import *'
__all__ = [
    "ZerothLawError",
    "ConfigError",
    "ValidationError",
    "FileError",
    "Config",
    "get_config",
    "load_config",
    "__version__",
]

"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Simplified exports to essential components
## FUTURE TODOs: Implement automatic version management
"""
