"""
# PURPOSE: Template file handling for Zeroth Law.

## INTERFACES:
 - is_template_file: Check if file is a template
 - analyze_template_file: Analyze template file metrics

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
 - re
"""

import os
import logging
import re
from pathlib import Path
from typing import Dict, List, Any

from zeroth_law.utils.file_utils import find_header_footer, count_executable_lines

logger = logging.getLogger(__name__)


def is_template_file(file_path: str, excluded_files: List[str]) -> bool:
    """Determine if a file is a template file.

    Args:
        file_path (str): Path to the file to check.
        excluded_files (List[str]): List of filenames to exclude from template detection.

    Returns:
        bool: True if the file is a template, False otherwise.
    """
    normalized_path = os.path.normpath(file_path)
    templates_directory = os.path.normpath("templates")
    is_template = normalized_path.startswith(templates_directory)

    if os.path.basename(file_path) in excluded_files:
        is_template = False

    logger.debug(f"Analyzing file: {file_path}, is_template: {is_template}")
    return is_template


def analyze_template_file(file_path: str, source_code: str) -> Dict[str, Any]:
    """Analyze a template file with basic metrics.

    Args:
        file_path (str): Path to the template file.
        source_code (str): Content of the file.

    Returns:
        Dict[str, Any]: Basic metrics for the template file.
    """
    header, footer = find_header_footer(source_code)
    executable_lines = count_executable_lines(source_code)

    return {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "is_template": True,
        "header_footer_status": ("complete" if header and footer else ("missing_header" if not header else "missing_footer")),
        "executable_lines": executable_lines,
        "overall_score": "N/A - Template File",
        "compliance_level": "Template File",
        "functions": [],
        "penalties": [],
    }
