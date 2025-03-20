# FILE_LOCATION: {{cookiecutter.project_name}}/tests/{{cookiecutter.project_name}}/test_exceptions.py
"""
# PURPOSE: Tests for {{cookiecutter.project_name}}.exceptions.

## INTERFACES:
#   test_exceptions_exist: Verify the exception classes exist.
#   test_exception_inheritance: Verify the exception inheritance structure.

## DEPENDENCIES:
#   pytest
#   {{cookiecutter.project_name}}.exceptions
"""
import pytest
from {{cookiecutter.project_name}}.exceptions import (
    ZerothLawError,
    FileNotFoundError,
    NotPythonFileError,
    NotADirectoryError,
    AnalysisError,
    ConfigError
)

def test_exceptions_exist():
    """
    PURPOSE: Verify that all exception classes exist.

    PARAMS: None

    RETURNS: None
    """
    assert ZerothLawError
    assert FileNotFoundError
    assert NotPythonFileError
    assert NotADirectoryError
    assert AnalysisError
    assert ConfigError

def test_exception_inheritance():
    """
    PURPOSE: Verify the inheritance structure of custom exceptions.

    PARAMS: None

    RETURNS: None
    """
    # All custom exceptions should inherit from ZerothLawError
    assert issubclass(FileNotFoundError, ZerothLawError)
    assert issubclass(NotPythonFileError, ZerothLawError)
    assert issubclass(NotADirectoryError, ZerothLawError)
    assert issubclass(AnalysisError, ZerothLawError)
    assert issubclass(ConfigError, ZerothLawError)

    # ZerothLawError should inherit from Exception
    assert issubclass(ZerothLawError, Exception)

def test_exception_raising():
    """
    PURPOSE: Test that exceptions can be raised and caught properly.

    PARAMS: None

    RETURNS: None
    """
    # Test raising and catching each exception type
    with pytest.raises(ZerothLawError):
        raise ZerothLawError("Test error")
    
    with pytest.raises(FileNotFoundError):
        raise FileNotFoundError("Test error")
    
    with pytest.raises(NotPythonFileError):
        raise NotPythonFileError("Test error")
    
    with pytest.raises(NotADirectoryError):
        raise NotADirectoryError("Test error")
    
    with pytest.raises(AnalysisError):
        raise AnalysisError("Test error")
    
    with pytest.raises(ConfigError):
        raise ConfigError("Test error")
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added basic tests for exception classes
 - Added tests for exception inheritance structure
 - Added tests for raising and catching exceptions

## FUTURE TODOs:
 - Add tests for exception message formatting if implemented
""" 