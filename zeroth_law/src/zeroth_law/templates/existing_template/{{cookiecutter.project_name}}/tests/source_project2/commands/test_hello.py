# FILE_LOCATION: source_project2/tests/source_project2/commands/test_hello.py
"""
# PURPOSE: Tests for source_project2.commands.hello.

## INTERFACES:
#   test_hello_exists: Verify the module exists.

## DEPENDENCIES:
#   pytest
#   source_project2.commands.hello
"""
import pytest

def test_hello_exists():
    """
    PURPOSE: Verify that the hello command module exists.

    PARAMS: None

    RETURNS: None
    """
    # This is a placeholder test that will always pass.
    # Replace this with actual tests for the hello command.
    try:
        # This import will raise an ImportError if the module doesn't exist
        from {{ cookiecutter.project_name }}.commands import hello
        assert hasattr(hello, 'command')
    except ImportError:
        assert False, "commands.hello module does not exist"
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added basic module existence test

## FUTURE TODOs:
 - Add more specific tests for the hello command
""" 