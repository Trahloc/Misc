# FILE_LOCATION: {{cookiecutter.project_name}}/tests/{{cookiecutter.project_name}}/commands/test_info.py
"""
# PURPOSE: Tests for {{cookiecutter.project_name}}.commands.info.

## INTERFACES:
#   test_info_exists: Verify the module exists.

## DEPENDENCIES:
#   pytest
#   {{cookiecutter.project_name}}.commands.info
"""
import pytest

def test_info_exists():
    """
    PURPOSE: Verify that the info command module exists.

    PARAMS: None

    RETURNS: None
    """
    # This is a placeholder test that will always pass.
    # Replace this with actual tests for the info command.
    try:
        # This import will raise an ImportError if the module doesn't exist
        from {{cookiecutter.project_name}}.commands import info
        assert hasattr(info, 'command')
    except ImportError:
        assert False, "commands.info module does not exist"
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added basic module existence test

## FUTURE TODOs:
 - Add more specific tests for the info command
""" 