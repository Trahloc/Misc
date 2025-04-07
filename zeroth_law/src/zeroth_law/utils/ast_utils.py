"""
# PURPOSE: AST parsing utilities for Zeroth Law.

## INTERFACES:
 - get_ast_from_file: Parse Python file into AST
 - get_docstring: Extract docstring from AST node

## DEPENDENCIES:
 - logging
 - typing
 - ast
 - pathlib
"""

import ast
import logging
import os
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


def get_ast_from_file(file_path: str) -> Optional[ast.Module]:
    """Parse a Python file into an AST.

    Args:
        file_path (str): Path to the Python file to parse.

    Returns:
        Optional[ast.Module]: The AST module if successful, None if parsing fails.

    Raises:
        SyntaxError: If the file contains syntax errors.
        FileNotFoundError: If the file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    return ast.parse(source_code)


def get_docstring(node: ast.AST) -> Optional[str]:
    """Extract the docstring from an AST node.

    Args:
        node (ast.AST): The AST node to extract the docstring from.

    Returns:
        Optional[str]: The docstring if present, None otherwise.
    """
    if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
        return None

    if not node.body:
        return None

    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Str):
        return first.value.s
    return None
