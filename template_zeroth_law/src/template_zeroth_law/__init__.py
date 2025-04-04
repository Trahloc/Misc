# FILE_LOCATION: template_zeroth_law/src/template_zeroth_law/__init__.py
"""
# PURPOSE: Exposes the public API for the template_zeroth_law module.

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

"""
## KNOWN ERRORS: None
## IMPROVEMENTS:
- Added proper documentation structure
- Organized imports consistently
- Added explicit __all__ definition
## FUTURE TODOs:
- Consider adding version information
- Consider adding module-level type hints
- Add automated __all__ generation using autoinit
"""
