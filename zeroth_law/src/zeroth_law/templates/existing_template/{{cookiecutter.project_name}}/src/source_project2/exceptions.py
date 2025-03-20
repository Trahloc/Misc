# FILE_LOCATION: source_project2/src/source_project2/exceptions.py
"""
# PURPOSE: Define custom exceptions for the source_project2 analyzer.

## INTERFACES:
 - ZerothLawError
 - FileNotFoundError
 - NotPythonFileError
 - NotADirectoryError
 - AnalysisError
 - ConfigError

## DEPENDENCIES:
 - None
"""

class ZerothLawError(Exception):
    """Base class for all Zeroth Law specific exceptions."""
    pass

class FileNotFoundError(ZerothLawError):
    """Raised when a file or directory is not found."""
    pass

class NotPythonFileError(ZerothLawError):
    """Raised when a file is not a Python file."""
    pass
class NotADirectoryError(ZerothLawError):
    """Raised when a directory is not a directory."""
    pass

class AnalysisError(ZerothLawError):
    """Raised when an error occurs during code analysis."""
    pass

class ConfigError(ZerothLawError):
    """Raised when there is an error with the configuration."""
    pass