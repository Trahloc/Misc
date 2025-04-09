# FILE: tmux_manager/src/tmux_manager/__main__.py
"""
# PURPOSE: Entry point module for direct execution of the package.

## INTERFACES: main() -> int: Entry point for the CLI, returns exit code

## DEPENDENCIES:
  - sys: For system-level operations
  - cli: For command-line interface implementation
"""

import sys
from . import cli


def main() -> int:
    """
    PURPOSE: Main entry point when the package is executed directly.

    RETURNS:
    int: Exit code
    """
    return cli.main()


if __name__ == "__main__":
    sys.exit(main())

"""
## KNOWN ERRORS:
- No known errors

## IMPROVEMENTS:
- Simple entry point for direct execution
- Delegates to the CLI module for functionality

## FUTURE TODOs:
- Add signal handling for graceful shutdown
"""
