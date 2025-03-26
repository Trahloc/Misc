# FILE_LOCATION: template_zeroth_law/tests/template_zeroth_law/test_exceptions.py
"""
# PURPOSE: Tests for custom exception classes and error handling.

## INTERFACES:
 - test_exception_hierarchy: Test exception class inheritance
 - test_exception_usage: Test exception raising and catching
 - test_error_messages: Test error message formatting
 - test_exception_attributes: Test custom exception attributes

## DEPENDENCIES:
 - pytest: Testing framework
 - template_zeroth_law.exceptions: Custom exceptions
"""
from typing import Type, Any
import pytest

from template_zeroth_law.exceptions import (
    ZerothLawError,
    FileNotFoundError,
    NotPythonFileError,
    NotADirectoryError,
    AnalysisError,
    ConfigError,
)


def test_exception_hierarchy():
    """
    PURPOSE: Verify the exception inheritance hierarchy.

    CONTEXT: All custom exceptions should inherit from ZerothLawError,
            which itself inherits from Exception.
    """
    # Assert base class inheritance
    assert issubclass(ZerothLawError, Exception)

    # Assert all custom exceptions inherit from ZerothLawError
    custom_exceptions: list[Type[ZerothLawError]] = [
        FileNotFoundError,
        NotPythonFileError,
        NotADirectoryError,
        AnalysisError,
        ConfigError,
    ]

    for exc in custom_exceptions:
        assert issubclass(exc, ZerothLawError), f"{exc.__name__} must inherit from ZerothLawError"


@pytest.mark.parametrize("exc_class", [
    FileNotFoundError,
    NotPythonFileError,
    NotADirectoryError,
    AnalysisError,
    ConfigError,
])
def test_exception_creation(exc_class: Type[ZerothLawError]):
    """
    PURPOSE: Test exception instantiation and message handling.

    PARAMS:
        exc_class: Exception class to test
    """
    # Test basic message
    msg = "Test error message"
    exc = exc_class(msg)
    assert str(exc) == msg
    assert isinstance(exc, ZerothLawError)

    # Test with additional context
    context = {"file": "test.py", "line": 42}
    exc_with_context = exc_class(msg, **context)
    assert str(exc_with_context) == msg

    # Verify context is stored
    for key, value in context.items():
        assert hasattr(exc_with_context, key)
        assert getattr(exc_with_context, key) == value


def test_error_message_formatting():
    """Test error message formatting with different input types."""
    # Test with string formatting
    path = "/test/file.py"
    exc = FileNotFoundError(f"File not found: {path}")
    assert str(exc) == "File not found: /test/file.py"

    # Test with multiple arguments
    exc = AnalysisError("Multiple", "arguments", "test")
    assert str(exc) == "Multiple arguments test"


def test_exception_with_cause():
    """Test exception chaining."""
    try:
        try:
            raise ValueError("Original error")
        except ValueError as e:
            raise AnalysisError("Analysis failed") from e
    except AnalysisError as e:
        assert isinstance(e.__cause__, ValueError)
        assert str(e.__cause__) == "Original error"


@pytest.mark.parametrize("exc_class,attribute_dict", [
    (FileNotFoundError, {"path": "/test/file.py"}),
    (NotPythonFileError, {"file": "test.txt"}),
    (NotADirectoryError, {"path": "/test"}),
    (AnalysisError, {"module": "test_module", "line": 42}),
    (ConfigError, {"config_file": "config.json", "key": "missing_key"}),
])
def test_exception_attributes(exc_class: Type[ZerothLawError], attribute_dict: dict[str, Any]):
    """
    PURPOSE: Test custom attributes on exception instances.

    PARAMS:
        exc_class: Exception class to test
        attribute_dict: Dictionary of attributes to set and verify
    """
    # Create exception with attributes
    exc = exc_class("Test message", **attribute_dict)

    # Verify all attributes are set and accessible
    for key, value in attribute_dict.items():
        assert hasattr(exc, key), f"{exc_class.__name__} missing attribute: {key}"
        assert getattr(exc, key) == value


def test_exception_repr():
    """Test exception representation for debugging."""
    exc = AnalysisError("Test error", module="test_module", line=42)
    repr_str = repr(exc)

    # Verify repr contains essential information
    assert "AnalysisError" in repr_str
    assert "Test error" in repr_str
    assert "module='test_module'" in repr_str
    assert "line=42" in repr_str


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added parametrized tests for all exception classes
 - Added tests for attribute handling
 - Added tests for exception chaining
 - Added tests for error message formatting
 - Added comprehensive type hints
 - Added assertion messages
 - Increased assertion density

## FUTURE TODOs:
 - Add tests for custom exception formatting
 - Add tests for exception handling in async context
 - Add performance tests for exception creation
"""
