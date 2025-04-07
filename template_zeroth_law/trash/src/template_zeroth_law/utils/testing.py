"""
# PURPOSE: Provide utility functions for testing

## INTERFACES:
 - create_click_compatible_mock: Create a mock compatible with Click's file operations

## DEPENDENCIES:
 - unittest.mock
"""

from unittest.mock import MagicMock
from typing import Any, Callable


def create_click_compatible_mock(mock_class: Callable[[], Any]) -> Any:
    """
    PURPOSE: Create a mock object that works with Click's file operations
    CONTEXT: Testing Click commands that write to stdout/stderr
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS:
        mock_class: Mock class constructor (typically MagicMock)
    POST-CONDITIONS & GUARANTEES: Returns a mock that won't cause Click to fail
    RETURNS:
        Any: A configured mock object
    EXCEPTIONS: None
    USAGE EXAMPLES:
        >>> with patch('sys.stdout', create_click_compatible_mock(MagicMock)):
        ...     click.echo("Test")  # Won't raise exceptions
    """
    mock = mock_class()
    # Ensure the mock doesn't report as closed
    mock.closed = False
    # Ensure write method exists and returns appropriate values
    mock.write = MagicMock(return_value=None)
    # Ensure flush method exists
    mock.flush = MagicMock(return_value=None)
    # Add name attribute for compatibility
    mock.name = MagicMock()
    # Required for Python 3.8+ compatibility
    mock.isatty = MagicMock(return_value=False)
    return mock


"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Created for better organization of testing utilities
## FUTURE TODOs: Add more helper functions for common testing patterns
"""
