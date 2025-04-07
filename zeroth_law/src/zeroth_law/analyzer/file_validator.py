"""
# PURPOSE: File validation utilities for Zeroth Law.

## INTERFACES:
 - should_ignore: Check if file should be ignored
 - check_file_validity: Validate file structure
 - check_for_unrendered_templates: Check for unrendered template syntax

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
 - re
"""

import os
import logging
import fnmatch
import re
from typing import List

from zeroth_law.exceptions import (
    FileNotFoundError,
    NotPythonFileError,
    AnalysisError,
)

logger = logging.getLogger(__name__)


def should_ignore(file_path: str, base_path: str, ignore_patterns: List[str]) -> bool:
    """Check if a file should be ignored based on the ignore patterns.

    This function determines whether a file should be excluded from analysis based on
    a list of glob patterns. It normalizes both the file path and patterns to ensure
    consistent matching across different operating systems.

    Args:
        file_path (str): The absolute path of the file to check.
        base_path (str): The base directory path to make paths relative to.
        ignore_patterns (List[str]): List of glob patterns to match against.
            Patterns should use forward slashes and can include wildcards.

    Returns:
        bool: True if the file should be ignored, False otherwise.

    Examples:
        >>> should_ignore("/path/to/file.py", "/path", ["*.pyc", "test/*"])
        False
        >>> should_ignore("/path/to/test/file.py", "/path", ["test/*"])
        True
    """
    try:
        # Get path relative to the base directory
        rel_path = os.path.relpath(file_path, base_path)
        # Convert path to use forward slashes for consistent matching
        normalized_path = rel_path.replace(os.sep, "/")

        # Add a leading ./ to match patterns that start with . like .old/
        if not normalized_path.startswith("./"):
            normalized_path = "./" + normalized_path

        for pattern in ignore_patterns:
            # Normalize pattern to use forward slashes
            norm_pattern = pattern.replace(os.sep, "/")
            # Add ./ prefix to pattern if it starts with a dot directory
            if norm_pattern.startswith(".") and not norm_pattern.startswith("./"):
                norm_pattern = "./" + norm_pattern

            if fnmatch.fnmatch(normalized_path, norm_pattern):
                logger.debug(f"Path '{normalized_path}' matched pattern '{norm_pattern}'")
                return True
        return False
    except ValueError:
        # Handle case where file_path is on different drive than base_path (Windows)
        return False


def check_file_validity(file_path: str) -> None:
    """Check if a file exists and is a Python file.

    Args:
        file_path (str): Path to the file to check.

    Raises:
        FileNotFoundError: If the file does not exist.
        NotPythonFileError: If the file is not a Python file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.endswith(".py"):
        logger.warning(f"Skipping non-Python file: {file_path}")
        raise NotPythonFileError(f"Not a Python file: {file_path}")


def check_for_unrendered_templates(file_path: str, source_code: str, excluded_files: List[str]) -> None:
    """Check if a file contains unrendered template variables.

    Args:
        file_path (str): Path to the file to check.
        source_code (str): Content of the file.
        excluded_files (List[str]): List of filenames that are allowed to contain template variables.

    Raises:
        AnalysisError: If unrendered template variables are found in a non-excluded file.
    """
    if (
        os.path.basename(file_path) not in excluded_files
        and not file_path.endswith("analyzer.py")
        and re.search(r"\{\{.*?\}\}", source_code)
    ):
        logger.warning(f"Skipping unrendered template file: {file_path}")
        raise AnalysisError(f"Unrendered template detected in file: {file_path}")
