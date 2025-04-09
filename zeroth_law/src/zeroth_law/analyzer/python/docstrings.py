# FILE: src/zeroth_law/analyzer/python/docstrings.py
"""Analyzes Python code for docstring compliance."""

import ast
import io
import logging
import tokenize
from pathlib import Path

from .ast_utils import _add_parent_pointers, _parse_file_to_ast

log = logging.getLogger(__name__)

# Type alias for violation result
DocstringViolation = tuple[str, int]  # (name, line_number) - Name can be 'module' or function name

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


def _get_first_token(code: str) -> tokenize.TokenInfo | None:
    """Get the first non-trivial token from a code string."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        # Find the first meaningful token (not encoding, NL, COMMENT, etc.)
        for token in tokens:
            if token.type not in (tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT):
                return token
    except tokenize.TokenError:
        log.warning("Tokenizing failed while checking for module docstring start.")
    return None


def _get_ast_docstring(node: ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> str | None:
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
    try:
        tree, _ = _parse_file_to_ast(file_path)  # Use content if needed later
        _add_parent_pointers(tree)  # Needed for method check

        # Check module docstring
        if not _get_ast_docstring(tree):
            # Check if the first node is just pass or similar, maybe ignore?
            # For now, report missing module docstring strictly.
            violations.append(("module", 1))

        # Check functions and async functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Skip methods for now (could be configurable later)
                is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(node, "_parents", []))
                if is_method:
                    continue

                if not _get_ast_docstring(node):
                    violations.append((node.name, node.lineno))

            # TODO: Optionally check classes and methods later

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
