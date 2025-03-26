# FILE_LOCATION: template_zeroth_law/src/template_zeroth_law/exceptions.py
"""
# PURPOSE: Custom exceptions for Zeroth Law Framework.

## INTERFACES:
 - ZerothLawError: Base exception class
 - FileNotFoundError: File not found error
 - NotPythonFileError: Not a Python file error
 - NotADirectoryError: Directory not found error
 - AnalysisError: Analysis failure error
 - ConfigError: Configuration error

## DEPENDENCIES: None
"""
from typing import Any, Dict, Optional


class ZerothLawError(Exception):
    """Base class for all Zeroth Law exceptions."""
    def __init__(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Initialize the error with a message and optional attributes.

        Args:
            message: Error message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments as attributes
        """
        super().__init__(message, *args)
        self.message = message if not args else f"{message} {' '.join(str(arg) for arg in args)}"
        self._attributes = kwargs
        # Set attributes directly on the instance
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        """Format the error message."""
        return self.message

    def __repr__(self) -> str:
        """Detailed representation including class name and attributes."""
        attrs = ', '.join(f'{k}={v!r}' for k, v in self._attributes.items())
        return f"{self.__class__.__name__}({self.message!r}" + (f", {attrs})" if attrs else ")")

    @property
    def attributes(self) -> Dict[str, Any]:
        """Get error attributes."""
        return self._attributes.copy()


class FileNotFoundError(ZerothLawError):
    """Raised when a required file is not found."""
    pass


class NotPythonFileError(ZerothLawError):
    """Raised when a file is not a Python source file."""
    pass


class NotADirectoryError(ZerothLawError):
    """Raised when a required directory is not found."""
    pass


class AnalysisError(ZerothLawError):
    """Raised when code analysis fails."""
    pass


class ConfigError(ZerothLawError):
    """Raised when configuration is invalid or missing."""
    pass


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added proper error message handling
 - Added support for custom attributes via kwargs
 - Added proper string representation

## FUTURE TODOs:
 - Add custom error codes
 - Add error categorization
 - Add structured error data
"""
