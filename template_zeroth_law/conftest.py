# FILE_LOCATION: template_zeroth_law/conftest.py
"""
# PURPOSE: Configure pytest for the template_zeroth_law project.

## INTERFACES:
 - pytest_configure: Configure pytest to add the project root and src directory to Python path

## DEPENDENCIES:
 - pytest
 - sys
 - pathlib
"""
import sys
from pathlib import Path
import pytest


def pytest_configure(config):
    """
    PURPOSE: Add the project root and src directory to the Python path.

    PARAMS:
        config: The pytest configuration object

    RETURNS:
        None
    """
    # Get the project root directory (where this conftest.py is located)
    root_dir = Path(__file__).parent
    src_dir = root_dir / "src"

    # Add both root and src directories to Python path if not already there
    paths = [str(root_dir), str(src_dir)]
    for path in paths:
        if path not in sys.path:
            sys.path.insert(0, path)


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added src directory to Python path
 - Ensures tests can import the project modules without needing PYTHONPATH

## FUTURE TODOs:
 - None
"""
