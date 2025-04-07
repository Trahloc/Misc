"""
# PURPOSE: Common type definitions used throughout the application.

## INTERFACES:
 - PathLike: Type for objects that can be converted to paths
 - JsonDict: Type for JSON-like dictionaries
 - JsonValue: Type for JSON-like values
 - CallbackFunc: Type for callback functions
 - ResultCallback: Type for result callback functions
 - LogLevel: Literal type for log levels
 - create_click_compatible_mock: Function to create Click-compatible mock objects

## DEPENDENCIES:
 - typing: Type hints
 - typing_extensions: Optional for Literal in Python < 3.8
 - os: For PathLike
"""

import os
import sys
import codecs
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union, Any, Callable, TypeVar, Optional, Protocol, cast, runtime_checkable, Type

# Define type variables
T = TypeVar("T")
U = TypeVar("U")

# Try to use Literal from typing (Python 3.8+) or typing_extensions
try:
    if sys.version_info >= (3, 8):
        from typing import Literal, TypedDict
    else:
        from typing_extensions import Literal, TypedDict
except ImportError:
    try:
        from typing_extensions import Literal, TypedDict
    except ImportError:
        # Fallback if typing_extensions is not available
        Literal = Any  # type: ignore
        TypedDict = Dict  # type: ignore

# Path-like types
PathLike = Union[str, os.PathLike, Path]

# JSON-related types
JsonValue = Union[None, bool, int, float, str, List["JsonValue"], "JsonDict"]
JsonDict = Dict[str, JsonValue]

# Callback function types
CallbackFunc = Callable[[Any], None]
ResultCallback = Callable[[T], U]

# Log level literals
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Date-related types
DateLike = Union[datetime, str, int, float]


# Testing utility functions
def create_click_compatible_mock(mock_class: Type[Any]) -> Any:
    """
    PURPOSE: Create a mock object that is compatible with Click's internals.

    This function specifically addresses the issue where Click attempts to call
    codecs.lookup() on stream.encoding, which fails if encoding is a MagicMock.

    PARAMS:
        mock_class: The mock class to use (e.g., MagicMock, Mock)

    RETURNS:
        A Click-compatible mock object with encoding configured properly
    """
    try:
        from unittest.mock import PropertyMock
    except ImportError:
        raise ImportError("unittest.mock is required for creating Click-compatible mocks")

    mock = mock_class()

    # Set the encoding attribute to a real string that codecs.lookup() can handle
    type(mock).encoding = PropertyMock(return_value="utf-8")

    # Ensure other common attributes used by Click are properly mocked
    mock.isatty = mock_class(return_value=True)
    mock.flush = mock_class(return_value=None)

    return mock


@runtime_checkable
class Closeable(Protocol):
    """Protocol for objects that can be closed."""
    def close(self) -> None:
        """Close the object."""
        ...


@runtime_checkable
class Disposable(Protocol):
    """Protocol for objects that can be disposed."""
    def dispose(self) -> None:
        """Dispose of the object."""
        ...


@runtime_checkable
class HasName(Protocol):
    """Protocol for objects that have a name property."""
    @property
    def name(self) -> str:
        """Get the object's name."""
        ...


# Application-specific type definitions
class ConfigDict(TypedDict, total=False):
    """Type definition for configuration dictionaries."""

    app_name: str
    version: str
    debug: bool
    log_level: LogLevel


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added common type definitions
 - Added protocol classes for common interfaces
 - Added fallbacks for older Python versions
 - Added proper runtime protocol checking
 - Added utility function for creating Click-compatible mock objects for testing

## FUTURE TODOs:
 - Add runtime type checking utilities
 - Add more application-specific type definitions
 - Consider adding validation functions for types
"""
