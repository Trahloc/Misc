"""
# PURPOSE: Pytest configuration and fixtures for template_zeroth_law tests.

## INTERFACES:
 - module_exists: Fixture to check if a module exists

## DEPENDENCIES:
 - pytest
 - importlib
"""

import os
import tempfile
import importlib
from pathlib import Path
from typing import Generator, Iterator, Optional

import pytest


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """
    PURPOSE: Create a temporary directory for tests
    CONTEXT: Test fixture for file operations
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: Temporary directory is created and cleaned up
    RETURNS:
        Iterator[Path]: Path to the temporary directory
    EXCEPTIONS: None
    USAGE EXAMPLES:
        def test_file_operations(temp_dir):
            test_file = temp_dir / "test.txt"
            test_file.write_text("content")
            assert test_file.exists()
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_python_file(temp_dir: Path) -> Iterator[Path]:
    """
    PURPOSE: Create a temporary Python file for tests
    CONTEXT: Test fixture for Python file operations
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS:
        temp_dir (Path): Directory to create file in (from temp_dir fixture)
    POST-CONDITIONS & GUARANTEES: Temporary Python file is created
    RETURNS:
        Iterator[Path]: Path to the temporary Python file
    EXCEPTIONS: None
    USAGE EXAMPLES:
        def test_python_file_validator(temp_python_file):
            # Test code with a guaranteed Python file
            assert temp_python_file.suffix == '.py'
    """
    test_file = temp_dir / "test_file.py"
    test_file.write_text(
        """
# Test Python file
def example_function():
    return "Hello, World!"
"""
    )
    yield test_file


def check_module_exists(module_name: str) -> bool:
    """
    PURPOSE: Check if a module can be imported.
    CONTEXT: Used for conditional test execution.
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS:
        module_name (str): The name of the module to check
    POST-CONDITIONS & GUARANTEES: None
    RETURNS:
        bool: True if the module exists, False otherwise
    EXCEPTIONS: None
    """
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


@pytest.fixture
def module_exists():
    """
    PURPOSE: Fixture that returns a function to check if a module exists.
    CONTEXT: Used for conditional test execution.
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS:
        function: A function that takes a module name and returns True if it exists
    EXCEPTIONS: None
    """
    return check_module_exists


"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Added module existence check helper
## FUTURE TODOs: Add more test fixtures as needed
"""
