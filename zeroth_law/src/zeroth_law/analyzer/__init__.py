"""
# PURPOSE: Core analysis functionality for Zeroth Law.

## INTERFACES:
 - core: Main analysis functions
 - evaluator: Compliance evaluation
 - template_handler: Template file handling
 - file_validator: File validation utilities

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
 - ast
"""

from .core import analyze_directory, analyze_file
from .evaluator import evaluate_compliance
from .template_handler import is_template_file, analyze_template_file
from .file_validator import should_ignore, check_file_validity, check_for_unrendered_templates

__all__ = [
    "analyze_directory",
    "analyze_file",
    "evaluate_compliance",
    "is_template_file",
    "analyze_template_file",
    "should_ignore",
    "check_file_validity",
    "check_for_unrendered_templates",
]
