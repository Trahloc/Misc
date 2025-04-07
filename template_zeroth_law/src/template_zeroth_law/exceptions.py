# FILE: template_zeroth_law/src/template_zeroth_law/exceptions.py
"""
# PURPOSE: Custom exceptions for Zeroth Law Framework.

## INTERFACES:
 - ZerothLawError: Base exception class
 - ConfigError: Configuration error
 - ValidationError: Input validation error
 - FileError: File handling error

## DEPENDENCIES: None
## TODO: Customize exception types based on your project's needs
"""
from typing import Any, Dict, Optional


class ZerothLawError(Exception):
    """
    PURPOSE: Base class for all Zeroth Law exceptions.
    CONTEXT: Parent exception that provides common functionality for all derived exceptions
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: Common error handling behavior established
    RETURNS: N/A
    EXCEPTIONS: N/A
    USAGE EXAMPLES:
        >>> try:
        ...     raise ZerothLawError("An error occurred")
        ... except ZerothLawError as e:
        ...     str(e)
        'An error occurred'
    """

    def __init__(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        PURPOSE: Initialize the error with a message and optional attributes.
        CONTEXT: Constructor for the base exception class
        PRE-CONDITIONS & ASSUMPTIONS: None
        PARAMS:
            message (str): Error message
            *args (Any): Additional positional arguments
            **kwargs (Any): Additional keyword arguments as attributes
        POST-CONDITIONS & GUARANTEES: Error is initialized with message and attributes
        RETURNS: None
        EXCEPTIONS: None
        """
        super().__init__(message, *args)
        self.message = (
            message if not args else f"{message} {' '.join(str(arg) for arg in args)}"
        )
        self._attributes = kwargs
        # Set attributes directly on the instance
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        """
        PURPOSE: Format the error message.
        CONTEXT: String representation of the exception
        PRE-CONDITIONS & ASSUMPTIONS: None
        PARAMS: None
        POST-CONDITIONS & GUARANTEES: None
        RETURNS:
            str: Formatted error message
        EXCEPTIONS: None
        """
        return self.message

    def __repr__(self) -> str:
        """
        PURPOSE: Detailed representation including class name and attributes.
        CONTEXT: Developer-friendly representation of the exception
        PRE-CONDITIONS & ASSUMPTIONS: None
        PARAMS: None
        POST-CONDITIONS & GUARANTEES: None
        RETURNS:
            str: Technical representation of the exception
        EXCEPTIONS: None
        """
        attrs = ", ".join(f"{k}={v!r}" for k, v in self._attributes.items())
        return f"{self.__class__.__name__}({self.message!r}" + (
            f", {attrs})" if attrs else ")"
        )

    @property
    def attributes(self) -> Dict[str, Any]:
        """
        PURPOSE: Get error attributes.
        CONTEXT: Access to the error's metadata
        PRE-CONDITIONS & ASSUMPTIONS: None
        PARAMS: None
        POST-CONDITIONS & GUARANTEES: None
        RETURNS:
            Dict[str, Any]: Copy of error attributes
        EXCEPTIONS: None
        """
        return self._attributes.copy()


class ConfigError(ZerothLawError):
    """
    PURPOSE: Raised when there's a configuration error.
    CONTEXT: Configuration loading or validation operations
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS: N/A
    EXCEPTIONS: N/A
    USAGE EXAMPLES:
        >>> try:
        ...     raise ConfigError("Invalid configuration", key="timeout", value=-1)
        ... except ConfigError as e:
        ...     f"Invalid {e.attributes.get('key')}: {e.attributes.get('value')}"
        'Invalid timeout: -1'
    """

    pass


class ValidationError(ZerothLawError):
    """
    PURPOSE: Raised when input validation fails.
    CONTEXT: Input validation operations where values don't meet requirements
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS: N/A
    EXCEPTIONS: N/A
    USAGE EXAMPLES:
        >>> try:
        ...     raise ValidationError("Invalid input", field="email", value="not-an-email")
        ... except ValidationError as e:
        ...     f"Validation failed: {e.message}"
        'Validation failed: Invalid input'
    """

    pass


class FileError(ZerothLawError):
    """
    PURPOSE: Raised when file operations fail.
    CONTEXT: File system operations like reading, writing, or checking files
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS: N/A
    EXCEPTIONS: N/A
    USAGE EXAMPLES:
        >>> try:
        ...     raise FileError("File operation failed", file_path="/path/to/file")
        ... except FileError as e:
        ...     e.attributes.get('file_path')
        '/path/to/file'
    """

    pass


"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Simplified exception hierarchy to essential types
## FUTURE TODOs: Consider adding context managers for common error handling patterns
"""
