#!/usr/bin/env python
"""
# PURPOSE: Run pytest tests with proper configuration.

## INTERFACES:
    - main(): Run tests using our custom pytest wrapper

## DEPENDENCIES:
    - run_pytests: Our custom pytest wrapper
    - sys: System module for command-line arguments
"""

import sys
import os
from pathlib import Path
import importlib.util
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Run pytest tests with proper configuration.

    This function uses our custom pytest wrapper to ensure tests run
    without problematic plugins.

    Returns:
        int: Exit code from pytest
    """
    # Get the script directory
    script_dir = Path(__file__).parent.absolute()

    # Import and run our custom pytest wrapper
    wrapper_path = script_dir / "run_pytests.py"

    if not wrapper_path.exists():
        logger.error(f"Pytest wrapper script not found at {wrapper_path}")
        return 1

    # Import the wrapper module
    spec = importlib.util.spec_from_file_location("run_pytests", wrapper_path)
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)

    # Run the wrapper's main function
    return wrapper.main()


if __name__ == "__main__":
    sys.exit(main())
