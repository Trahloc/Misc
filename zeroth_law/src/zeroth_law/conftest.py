# FILE_LOCATION: src/zeroth_law/conftest.py
"""
# PURPOSE: Configure pytest for zeroth_law package.

## INTERFACES:
 - pytest_ignore_collect: Configure pytest to ignore cookiecutter template files

## DEPENDENCIES:
 - pytest
 - os
 - pathlib
"""
import os
from pathlib import Path
import pytest

def pytest_ignore_collect(collection_path, config):
    """
    PURPOSE: Tell pytest to ignore cookiecutter template files and generated test projects.
    
    This function prevents pytest from attempting to collect and run tests
    from the cookiecutter template files, which contain placeholders that
    cause syntax errors when interpreted as Python code. It also ignores
    test projects like zeroth_law_test that might have duplicate test module names.
    
    PARAMS:
        collection_path: The path being considered for test collection
        config: The pytest configuration object
        
    RETURNS:
        True if the path should be ignored, False otherwise
    """
    # Convert to Path object for easier manipulation
    path = Path(str(collection_path))
    
    # Check if the path contains directories we want to ignore
    if "cookiecutter-template" in path.parts:
        return True
    
    # Ignore test projects like zeroth_law_test
    if "zeroth_law_test" in path.parts:
        return True
    
    # Check for Jinja2 template syntax in the path (e.g., {{cookiecutter.project_name}})
    if any("{{" in part and "}}" in part for part in path.parts):
        return True
    
    return False
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added pytest configuration to ignore cookiecutter template files
 - Added support for ignoring test projects to prevent duplicate module name issues
 - Added detection of Jinja2 template syntax in paths

## FUTURE TODOs:
 - Update to handle additional template directories if added
""" 