# FILE_LOCATION: {{ cookiecutter.project_name }}/src/{{ cookiecutter.project_name }}/__init__.py
"""
# PURPOSE: Exposes the public API for the {{ cookiecutter.project_name }} module.

## INTERFACES:
# - config: Configuration management
# - cli: Command-line interface
# - commands: CLI commands
# - logging: Logging utilities
# - types: Type definitions
# - utils: Utility functions

## DEPENDENCIES: None (only internal modules)
"""
from . import config
from . import cli
from . import commands
from . import logging
from . import types
from . import utils

__all__ = [
    "config",
    "cli",
    "commands",
    "logging",
    "types",
    "utils",
]