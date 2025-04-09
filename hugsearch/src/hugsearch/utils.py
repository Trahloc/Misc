"""
# PURPOSE: Common utility functions used throughout the application.

## INTERFACES:
 - get_project_root() -> Path: Get the project's root directory
 - sanitize_filename(filename: str) -> str: Sanitize a filename to be safe for filesystem
 - merge_dicts(dict1: Dict, dict2: Dict) -> Dict: Deep merge two dictionaries
 - parse_timestamp(timestamp: str) -> datetime: Parse a timestamp string into a datetime object

## DEPENDENCIES:
 - os: Operating system utilities
 - re: Regular expressions
 - sys: System utilities
 - datetime: Datetime utilities
 - pathlib: Path manipulation
 - typing: Type hints
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def get_project_root() -> Path:
    """
    PURPOSE: Get the project's root directory.

    RETURNS:
        Path object to the project root
    """
    # Try to find project root by looking for standard files
    current_path = Path.cwd()
    markers = ["pyproject.toml", "setup.py", ".git", "README.md"]

    # Start from current working directory and go up
    check_path = current_path
    while check_path != check_path.parent:
        for marker in markers:
            if (check_path / marker).exists():
                return check_path
        check_path = check_path.parent

    # If no markers found, return the working directory
    return current_path


def sanitize_filename(filename: str) -> str:
    """
    PURPOSE: Sanitize a filename to be safe for the filesystem.

    PARAMS:
        filename: The original filename

    RETURNS:
        A sanitized filename with unsafe characters removed
    """
    # Replace unsafe characters with underscores
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # Replace multiple spaces with a single space
    sanitized = re.sub(r"\s+", " ", sanitized)
    # Trim spaces from the ends
    sanitized = sanitized.strip()
    # Ensure filename isn't empty after sanitization
    if not sanitized:
        sanitized = "unnamed_file"
    return sanitized


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    PURPOSE: Deep merge two dictionaries, with dict2 values taking precedence.

    PARAMS:
        dict1: First dictionary
        dict2: Second dictionary (overrides dict1 values)

    RETURNS:
        A new dictionary with merged values
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def parse_timestamp(timestamp: str, formats: Optional[List[str]] = None) -> datetime:
    """
    PURPOSE: Parse a timestamp string into a datetime object.

    PARAMS:
        timestamp: The timestamp string to parse
        formats: List of format strings to try, in order

    RETURNS:
        A datetime object

    RAISES:
        ValueError: If timestamp couldn't be parsed with any format
    """
    if formats is None:
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
            "%b %d %Y %H:%M:%S",
            "%b %d %Y",
            "%d %b %Y %H:%M:%S",
            "%d %b %Y",
        ]

    for fmt in formats:
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            continue

    raise ValueError(
        f"Could not parse timestamp '{timestamp}' with any of the provided formats"
    )


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added commonly needed utility functions
 - Added proper error handling and validation
 - Added detailed documentation

## FUTURE TODOs:
 - Add file operations utilities
 - Add string manipulation utilities
 - Add data validation utilities
"""
