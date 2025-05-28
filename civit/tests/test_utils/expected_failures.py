"""
Helper utilities for handling tests where failure is the expected result.

This module provides decorators and utilities to mark tests as "No-Go" tests,
where a failure is actually the correct and expected outcome.
"""

import pytest
import functools
import logging
from typing import Type, Optional, Callable, Any
from contextlib import contextmanager


def expect_exception(exception_type: Type[Exception], message: Optional[str] = None):
    """
    Decorator for tests that are expected to raise a specific exception.

    This decorates the test as both a pytest.mark.nogo test and ensures that
    the test will only pass if the specified exception is raised.

    Args:
        exception_type: The exception type that should be raised
        message: Optional string that should be in the exception message

    Returns:
        A decorated test function that passes when the expected exception is raised
    """

    def decorator(func):
        @pytest.mark.nogo
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with pytest.raises(exception_type) as excinfo:
                func(*args, **kwargs)

            # If a specific message is expected, verify it's in the exception
            if message is not None:
                assert message in str(excinfo.value), (
                    f"Expected exception message to contain '{message}', "
                    f"but got: '{str(excinfo.value)}'"
                )

        return wrapper

    return decorator


def nogo_test(expected_exception: Type[Exception], message: Optional[str] = None):
    """
    Decorator to mark a test as a No-Go test that expects a specific exception.

    This is a more semantically clear alias for expect_exception.

    Args:
        expected_exception: The exception type that should be raised
        message: Optional string that should be in the exception message

    Returns:
        A decorated test function
    """
    return expect_exception(expected_exception, message)


def assert_raises(
    exception_type: Type[Exception],
    func: Callable[..., Any],
    *args,
    message: Optional[str] = None,
    **kwargs,
):
    """
    Assert that calling func with the given args raises the expected exception.

    This is useful for checking expected failures within a test that also
    performs other assertions.

    Args:
        exception_type: The exception type that should be raised
        func: The function to call
        *args: Positional arguments to pass to func
        message: Optional string that should be in the exception message
        **kwargs: Keyword arguments to pass to func

    Returns:
        The exception that was raised for further inspection

    Raises:
        AssertionError: If the expected exception is not raised
    """
    with pytest.raises(exception_type) as excinfo:
        func(*args, **kwargs)

    if message is not None:
        assert message in str(excinfo.value), (
            f"Expected exception message to contain '{message}', "
            f"but got: '{str(excinfo.value)}'"
        )

    return excinfo.value


@contextmanager
def expect_log_error(
    logger_name: str, level=logging.ERROR, message: Optional[str] = None
):
    """
    Context manager that temporarily captures logs of specified level.

    This is useful when testing code that is expected to log errors, but you don't
    want those error logs to appear in the test output.

    Args:
        logger_name: The name of the logger to capture
        level: The minimum log level to capture (default: ERROR)
        message: Optional message to check for in the captured logs

    Yields:
        A list to which captured log messages will be added
    """
    captured_logs = []

    # Create a custom handler that captures logs
    class CaptureHandler(logging.Handler):
        def emit(self, record):
            captured_logs.append(record)

    # Get the logger we want to capture
    logger = logging.getLogger(logger_name)

    # Save original handlers and level
    original_handlers = list(logger.handlers)
    original_level = logger.level
    original_propagate = logger.propagate

    # Replace with our capture handler
    logger.handlers = []
    logger.addHandler(CaptureHandler(level))
    logger.setLevel(min(level, logger.level) if logger.level > 0 else level)
    logger.propagate = False  # Prevent propagation to parent loggers

    try:
        yield captured_logs
    finally:
        # Restore original handlers and level
        logger.handlers = original_handlers
        logger.setLevel(original_level)
        logger.propagate = original_propagate

    # If a message was specified, check if it appears in the logs
    if message is not None:
        matching_logs = [
            record for record in captured_logs if message in record.getMessage()
        ]
        assert (
            matching_logs
        ), f"Expected log message containing '{message}' was not found"


def silent_errors(func=None, logger_names=None):
    """
    Decorator to suppress error logs in tests.

    Use this decorator on tests that are expected to trigger error logs.
    The test will still pass/fail normally, but error logs won't be displayed.

    Args:
        func: The test function to decorate
        logger_names: List of logger names to silence. If None, uses ['root']

    Returns:
        The decorated function
    """
    if logger_names is None:
        logger_names = ["root"]

    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            # Store original log levels to restore them later
            original_levels = {}
            for name in logger_names:
                logger = logging.getLogger(name)
                original_levels[name] = logger.level
                # Temporarily increase the log level to CRITICAL to suppress lower-level logs
                logger.setLevel(logging.CRITICAL)

            try:
                # Run the test
                return test_func(*args, **kwargs)
            finally:
                # Restore original log levels
                for name, level in original_levels.items():
                    logging.getLogger(name).setLevel(level)

        return wrapper

    # Allow usage with or without arguments
    if func is not None:
        return decorator(func)
    return decorator
