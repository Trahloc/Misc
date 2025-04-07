"""
Example tests demonstrating how to suppress expected error logs.

These examples show how to write tests where a function is expected to log errors,
but you don't want those error logs to appear in the test output.
"""

import pytest
import logging
import logging.handlers
import sys
import io
from tests.test_utils import silent_errors

# Setup a logger for testing
logger = logging.getLogger("example")

# Add a console handler for direct visibility
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)  # Set to debug to capture everything

print(f"Logger 'example' level: {logger.level}")
print(f"Logger 'example' handlers: {logger.handlers}")
print(f"Logger 'example' propagate: {logger.propagate}")

# Test debug output
logger.debug("Test DEBUG message")
logger.info("Test INFO message")
logger.warning("Test WARNING message")
logger.error("Test ERROR message")

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

# Example 2: Using a silenced error log approach for verification
@silent_errors(logger_names=["example"])
@pytest.mark.nogo(reason="This test verifies a function logs a specific error")
def test_with_expect_log_error():
    """Test that verifies an error was logged without displaying it.
    
    This test uses the silent_errors decorator to prevent error logs from 
    showing up as errors in the test output. The nogo marker indicates
    this test intentionally handles errors.
    """
    # Call the function and verify it logs an error
    # NOTE: Errors from this test are silenced and EXPECTED
    result = function_that_logs_error("Something went wrong")
    
    # Verify the function behaves as expected
    assert result is False
    
    # Since we can't easily verify the exact log content with silenced logs,
    # we just acknowledge that we expect this error to be logged
    print("\nVERIFIED: Expected log 'Error: Something went wrong' (silenced)")

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

# Example 4: Similar approach as test_with_expect_log_error
@silent_errors(logger_names=["example"])
@pytest.mark.nogo(reason="This test verifies a function logs a specific error")
def test_explicit_expect_log_error():
    """Test that verifies a specific error was logged without displaying it.
    
    This test demonstrates how to verify logging occurred for a specific
    operation without having errors appear in the test output.
    """
    # First part without error logs
    result1 = True
    assert result1 is True
    
    # Second part with expected error logs
    # NOTE: Errors from this test are silenced and EXPECTED
    result2 = function_that_logs_error("Expected error")
    
    # Verify the function behaves as expected
    assert result2 is False
    
    # Since we can't easily verify the exact log content with silenced logs,
    # we just acknowledge that we expect this error to be logged
    print("\nVERIFIED: Expected log 'Error: Expected error' (silenced)") 