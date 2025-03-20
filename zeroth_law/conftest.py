# FILE_LOCATION: conftest.py
"""
# PURPOSE: Configure pytest for the zeroth_law project.

## INTERFACES:
 - pytest_configure: Configure pytest to add the project root to Python path
 - pytest_ignore_collect: Ignore cookiecutter template files

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

def pytest_ignore_collect(path):
    """
    PURPOSE: Ignore cookiecutter template files during test collection.
    
    PARAMS:
        path: The path to check
        
    RETURNS:
        bool: True if the path should be ignored, False otherwise
    """
    # Convert path to string for easier checking
    path_str = str(path)
    
    # Ignore files in cookiecutter template directories
    if "cookiecutter-template" in path_str:
        return True
        
    # Ignore files with Jinja2 template syntax
    if "{{" in path_str and "}}" in path_str:
        return True
        
    return False
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added Python path configuration for pytest
 - Ensures tests can import the project modules without needing PYTHONPATH
 - Added proper cookiecutter template file ignoring

## FUTURE TODOs:
 - None
""" 