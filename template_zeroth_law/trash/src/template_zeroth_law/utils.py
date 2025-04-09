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
    PURPOSE: Get the root directory of the project.

    CONTEXT: Used to locate project files relative to the root

    PRE-CONDITIONS & ASSUMPTIONS: Called from within a Python project directory

    PARAMS: None

    POST-CONDITIONS & GUARANTEES: Returns a Path object to the project root

    RETURNS:
        Path: Path to the project root

    EXCEPTIONS:
        None

    USAGE EXAMPLES:
        >>> from template_zeroth_law.utils import get_project_root
        >>> project_root = get_project_root()
        >>> (project_root / "pyproject.toml").exists()
        True
    """
    # Start from the current directory
    current = Path.cwd().absolute()

    # Look for markers of a project root (pyproject.toml, setup.py, .git)
    root_markers = [
        "pyproject.toml",
        "setup.py",
        ".git",
    ]

    # Walk up the directory tree until we find a marker
    while current != current.parent:
        for marker in root_markers:
            if (current / marker).exists():
                return current
        current = current.parent

    # If no marker found, return the current directory
    return Path.cwd()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed_file"

    # Handle path traversal attempts
    if ".." in filename:
        prefix = "_"
    else:
        prefix = ""

    # Get original parts for handling paths with invalid characters
    # but preserve all components for complex paths
    if "/" in filename or "\\" in filename:
        # Extract file name part (last component) and process it separately
        parts = re.split(r"[/\\]+", filename.replace("..", ""))
        # Skip empty parts
        parts = [p for p in parts if p]

        if not parts:
            return "unnamed_file"

        # Sanitize each part individually
        sanitized_parts = []
        for part in parts:
            # Replace invalid characters with underscores
            part = re.sub(r'[<>:"|?*\'\\]+', "_", part)
            # Clean up multiple underscores
            part = re.sub(r"_{2,}", "_", part)
            # Clean up spaces
            part = re.sub(r"\s+", " ", part)
            # Trim leading/trailing spaces and underscores
            part = part.strip(" _")

            if part:  # Skip empty parts
                sanitized_parts.append(part)

        if not sanitized_parts:
            return "unnamed_file"

        # Join the processed parts with underscores
        name = "_".join(sanitized_parts)

        # Split into name and extension
        name_parts = name.rsplit(".", 1)
        base_name = name_parts[0]
        ext = f".{name_parts[1]}" if len(name_parts) > 1 else ""

        return prefix + base_name + ext
    else:
        # Handle simple filenames (no path separators)
        # Split into name and extension
        name_parts = filename.rsplit(".", 1)
        name = name_parts[0]
        ext = f".{name_parts[1]}" if len(name_parts) > 1 else ""

        # Handle hidden files
        if name.startswith("."):
            name = "_" + name[1:]

        # Replace invalid characters
        name = re.sub(r'[<>:"|?*\'\\]+', "_", name)

        # Clean up multiple underscores and spaces
        name = re.sub(r"_{2,}", "_", name)
        name = re.sub(r"\s+", " ", name)

        # Clean up leading/trailing spaces and underscores
        name = name.strip(" _")

        # Handle empty or whitespace-only names
        if not name or name.isspace():
            return "unnamed_file"

        return prefix + name + ext


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
