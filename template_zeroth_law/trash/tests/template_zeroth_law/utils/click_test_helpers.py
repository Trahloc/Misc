"""
# PURPOSE: Provide helper functions for testing click commands.

## INTERFACES:
 - create_click_compatible_mock(mock_class): Create a mock compatible with click I/O

## DEPENDENCIES:
 - unittest.mock
"""

from unittest.mock import MagicMock


def create_click_compatible_mock(mock_class):
    """
    PURPOSE: Create a mock that works with click's file operations
    CONTEXT: Test utility for mocking stdout/stderr in click commands
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS:
        mock_class: The mock class to use as a base
    POST-CONDITIONS & GUARANTEES: None
    RETURNS:
        A mock object that can be used with click
    EXCEPTIONS: None
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
    return mock


"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Created utility for click testing
## FUTURE TODOs: Add more click testing utilities
"""
