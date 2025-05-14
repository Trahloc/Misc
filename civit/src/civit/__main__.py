"""
Main entry point for the civit command-line tool.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
