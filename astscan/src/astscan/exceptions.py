# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/templates/exceptions.py.template
"""
# PURPOSE: Define custom exceptions for the astscan analyzer.

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