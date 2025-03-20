# FILE_LOCATION: hugsearch/conftest.py
"""
# PURPOSE: Configure pytest for the zeroth_law_template project.

## INTERFACES:
 - pytest_configure: Configure pytest to add the project root to Python path

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
    PURPOSE: Add the project root to the Python path.
    
    PARAMS:
        config: The pytest configuration object
        
    RETURNS:
        None
    """
    # Get the project root directory (where this conftest.py is located)
    root_dir = Path(__file__).parent
    
    # Add the project root to the Python path if it's not already there
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added Python path configuration for pytest
 - Ensures tests can import the project modules without needing PYTHONPATH

## FUTURE TODOs:
 - None
""" 