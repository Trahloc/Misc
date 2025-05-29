"""
# PURPOSE: Common type definitions used throughout the application.

## INTERFACES:
 - PathLike: Type for objects that can be converted to paths
 - JsonDict: Type for JSON-like dictionaries
 - JsonValue: Type for JSON-like values
 - CallbackFunc: Type for callback functions
 - ResultCallback: Type for result callback functions
 - LogLevel: Literal type for log levels

## DEPENDENCIES:
 - typing: Type hints
 - typing_extensions: Optional for Literal in Python < 3.8
 - os: For PathLike
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union, Any, Callable, TypeVar, Protocol

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


class Closeable(Protocol):
    """Protocol for objects that can be closed."""

    def close(self) -> None: ...


class Disposable(Protocol):
    """Protocol for objects that can be disposed."""

    def dispose(self) -> None: ...


class HasName(Protocol):
    """Protocol for objects that have a name property."""

    @property
    def name(self) -> str: ...


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

## FUTURE TODOs:
 - Add runtime type checking utilities
 - Add more application-specific type definitions
 - Consider adding validation functions for types
"""
