# FILE: src/zeroth_law/analyzer/python/docstrings.py
"""Analyzes Python code for docstring compliance."""

import ast
import io
import structlog
import tokenize
from pathlib import Path
from io import BytesIO
from typing import List, Tuple, Dict, Any, Optional

from .ast_utils import _build_parent_map, _parse_file_to_ast

log = structlog.get_logger()

# Type alias for violation tuple
DocstringViolation = tuple[str, str, int]  # (node_type, node_name, line_number)

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


def _get_first_token(code: str) -> tokenize.TokenInfo | None:
    """Get the first non-trivial token from a code string."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        # Find the first meaningful token (not encoding, NL, COMMENT, etc.)
        for token in tokens:
            if token.type not in (
                tokenize.ENCODING,
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.COMMENT,
            ):
                return token
    except tokenize.TokenError:
        log.warning("Tokenizing failed while checking for module docstring start.")
    return None


def _get_ast_docstring(
    node: ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
) -> str | None:
    """Safely retrieves the docstring from an AST node."""
    return ast.get_docstring(node, clean=False)


def analyze_docstrings(file_path: str | Path) -> list[DocstringViolation]:
    """Analyzes a Python file for missing docstrings in modules, functions.

    Relies on `ast.get_docstring`.

    Args:
    ----
        file_path: Path to the Python file to analyze.

    Returns:
    -------
        A list of tuples, where each tuple contains the name ('module' or function name)
        and line number of a definition missing a docstring.

    Raises:
    ------
        FileNotFoundError: If file_path does not exist.
        SyntaxError: If the file contains invalid Python syntax.
        OSError: For other file I/O errors.

    """
    violations: list[DocstringViolation] = []
    module_docstring_present = False

    try:
        tree, _ = _parse_file_to_ast(file_path)
        parent_map = _build_parent_map(tree)

        # Check module docstring
        if not ast.get_docstring(tree):
            violations.append(("module", Path(file_path).name, 1))
        else:
            module_docstring_present = True

        for node in ast.walk(tree):
            node_type = ""
            node_name = ""
            # line_number = node.lineno  # Cannot get reliably from all node types here

            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Skip methods for now (could add check later)
                parent = parent_map.get(node)
                is_method = parent is not None and isinstance(parent, ast.ClassDef)
                if is_method:
                    continue
                # Skip __init__ if module docstring exists (common pattern)
                if node.name == "__init__" and module_docstring_present:
                    continue

                if not ast.get_docstring(node):
                    node_type = "function"
                    node_name = node.name
                    line_number = node.lineno  # Get line number here where we know it exists
            elif isinstance(node, ast.ClassDef):
                # Check if it's nested within another class
                parent = parent_map.get(node)
                is_nested_class = parent is not None and isinstance(parent, ast.ClassDef)
                # Skip nested classes for simplicity
                if is_nested_class:
                    continue

                if not ast.get_docstring(node):
                    node_type = "class"
                    node_name = node.name
                    line_number = node.lineno  # Get line number here

            if node_type:
                violations.append((node_type, node_name, line_number))

    except (FileNotFoundError, SyntaxError, OSError) as e:
        log.error(f"Could not analyze docstrings for {file_path}: {e}")
        # Propagate error or return specific violation?
        # For now, re-raise to indicate analysis could not complete.
        raise
    except Exception as e:
        log.exception(f"Unexpected error analyzing docstrings for {file_path}", exc_info=e)
        raise RuntimeError(f"Unexpected error during docstring analysis for {file_path}") from e

    return violations


# <<< ZEROTH LAW FOOTER >>>
