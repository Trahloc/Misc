# FILE_LOCATION: {{ cookiecutter.project_name }}/tests/{{ cookiecutter.project_name }}/test_cli.py
"""
# PURPOSE: Tests for {{ cookiecutter.project_name }}.cli.

## INTERFACES:
#   test_cli_exists: Verify the module exists.

## DEPENDENCIES:
#   pytest
#   {{ cookiecutter.project_name }}.cli
"""
import pytest

def test_cli_exists():
    """
    PURPOSE: Verify that the cli module exists.

    PARAMS: None

    RETURNS: None
    """
    # This is a placeholder test that will always pass.
    # Replace this with actual tests for the cli module.
    try:
        # This import will raise an ImportError if the module doesn't exist
        from {{ cookiecutter.project_name }} import cli
        assert True
    except ImportError:
        assert False, "cli module does not exist"
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added basic module existence test

## FUTURE TODOs:
 - Add more specific tests for CLI functionality
""" 