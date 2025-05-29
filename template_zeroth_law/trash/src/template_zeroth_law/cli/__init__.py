# FILE: template_zeroth_law/src/template_zeroth_law/cli/__init__.py
"""
# PURPOSE: Command-line interface module initialization.

## INTERFACES:
 - commands.hello: Hello world command
 - commands.init: Initialize a new project based on this template
## DEPENDENCIES: None
## TODO: Add CLI command exports
"""

from template_zeroth_law.cli.commands import hello, init

__all__ = ["hello", "init"]

"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Updated command exports to match template purpose
## FUTURE TODOs: Move CLI commands from __main__.py to this module
"""

"""
PURPOSE: Command-line interface for the Zeroth Law template.

INTERFACES:
    - main: Main entry point for the CLI.

DEPENDENCIES: None
"""

import argparse
import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    """
    PURPOSE: Main entry point for the Zeroth Law CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Zeroth Law Template - A framework for well-structured Python applications"
    )

    # Add subparsers for different commands
    parser.add_subparsers(dest="command", help="Command to execute")

    # TODO: Add command subparsers here

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # TODO: Execute the selected command

    return 0
