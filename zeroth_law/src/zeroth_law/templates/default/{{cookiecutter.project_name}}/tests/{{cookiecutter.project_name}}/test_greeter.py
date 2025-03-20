# FILE_LOCATION: {{cookiecutter.project_name}}/tests/{{cookiecutter.project_name}}/test_greeter.py
"""
# PURPOSE: Tests for {{cookiecutter.project_name}}.greeter.

## INTERFACES:
#   test_greeter_exists: Verify the module exists.

## DEPENDENCIES:
#   pytest
#   {{cookiecutter.project_name}}.greeter
"""
import pytest

def test_greeter_exists():
    """
    PURPOSE: Verify that the greeter module exists.

    PARAMS: None

    RETURNS: None
    """
    # This is a placeholder test that will always pass.
    # Replace this with actual tests for the greeter module.
    try:
        # This import will raise an ImportError if the module doesn't exist
        from {{cookiecutter.project_name}} import greeter
        assert hasattr(greeter, 'greet_user')
    except ImportError:
        assert False, "greeter module does not exist"
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added basic module existence test

## FUTURE TODOs:
 - Add specific tests for greeting functionality
""" 