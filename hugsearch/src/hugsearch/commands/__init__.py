"""
# PURPOSE: Exposes CLI commands as a module

## INTERFACES:
 - version.command: Implements the version command
 - check.command: Implements the check command
 - info.command: Implements the info command

## DEPENDENCIES:
 - .version: Version command implementation
 - .check: System check command implementation
 - .info: Info command implementation
"""

from . import version
from . import check
from . import info

__all__ = ["version", "check", "info"]
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Explicit exports
 - Updated to include only essential commands
 - Removed example-specific commands

## FUTURE TODOs:
 - Consider command discovery mechanism for plugin-like architecture
"""
