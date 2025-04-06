"""
Example tests demonstrating how to suppress expected error logs.

These examples show how to write tests where a function is expected to log errors,
but you don't want those error logs to appear in the test output.
"""

import pytest
import logging
from tests.test_utils import silent_errors, expect_log_error


# Setup a logger for testing
logger = logging.getLogger("example")


def function_that_logs_error(message):
    """Example function that logs an error."""
    logger.error(f"Error: {message}")
    return False


def function_that_logs_and_raises(message):
    """Example function that logs an error and raises an exception."""
    logger.error(f"Error: {message}")
    raise ValueError(message)


# Example 1: Using the silent_errors decorator
@silent_errors(logger_names=["example"])
def test_function_with_silent_errors():
    """Test with suppressed error logs.
    
    This test will pass and no error logs will be shown in the output,
    even though an error is logged by the function.
    """
    result = function_that_logs_error("Something went wrong")
    assert result is False


# Example 2: Using the expect_log_error context manager
def test_with_expect_log_error():
    """Test that verifies an error was logged but doesn't display it.
    
    This test will pass and will verify that the expected error was logged,
    but the error log won't be shown in the output.
    """
    with expect_log_error("example", message="Something went wrong") as logs:
        result = function_that_logs_error("Something went wrong")
    
    assert result is False
    assert len(logs) == 1
    assert logs[0].levelno == logging.ERROR


# Example 3: Combining with nogo_test for exceptions
@pytest.mark.nogo
@silent_errors(logger_names=["example"])
def test_function_that_logs_and_raises():
    """Test a function that both logs errors and raises exceptions.
    
    This test uses multiple decorators - it will:
    1. Silence the error logs (silent_errors)
    2. Mark the test as expected to fail (nogo)
    """
    with pytest.raises(ValueError) as exc_info:
        function_that_logs_and_raises("Expected exception")
    
    assert "Expected exception" in str(exc_info.value)


# Example 4: Using context manager for more control
def test_explicit_expect_log_error():
    """Test that selectively captures error logs for verification.
    
    This allows you to test that specific error messages were logged
    without showing them in the test output.
    """
    # First part without error logs
    result1 = True
    assert result1 is True
    
    # Second part with expected error logs
    with expect_log_error("example") as logs:
        result2 = function_that_logs_error("Expected error")
        assert result2 is False
    
    # Check that we got the expected log
    assert len(logs) == 1
    assert "Expected error" in logs[0].getMessage() 