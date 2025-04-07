"""
# PURPOSE: Utility functions for Zeroth Law.

## INTERFACES:
 - file_utils: File manipulation utilities
 - ast_utils: AST parsing utilities
 - config: Configuration management

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
 - ast
 - tomllib
"""

from .file_utils import (
    find_header_footer,
    count_executable_lines,
    replace_footer,
    get_line_range,
    edit_file_with_black,
)
from .ast_utils import get_ast_from_file, get_docstring
from .config import load_config

__all__ = [
    "find_header_footer",
    "count_executable_lines",
    "replace_footer",
    "get_line_range",
    "get_ast_from_file",
    "get_docstring",
    "load_config",
    "edit_file_with_black",
]
