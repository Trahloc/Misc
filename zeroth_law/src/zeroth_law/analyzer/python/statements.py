# FILE: src/zeroth_law/analyzer/python/statements.py
"""Analyzes Python functions for excessive statement counts."""

import ast
import logging
import typing
from pathlib import Path

from .ast_utils import _add_parent_pointers, _parse_file_to_ast

log = logging.getLogger(__name__)

# Type alias for violation result
StatementViolation = tuple[str, int, int]  # (function_name, line_number, statement_count)

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


class StatementCounterVisitor(ast.NodeVisitor):
    """Counts executable statements within a visited function node."""

    def __init__(self: typing.Self) -> None:
        """Initialize statement counter."""
        self.count = 0

    def visit_FunctionDef(self: typing.Self, node: ast.FunctionDef) -> None:
        """Visit FunctionDef to count statements in its body."""
        self._count_body_statements(node)

    def visit_AsyncFunctionDef(self: typing.Self, node: ast.AsyncFunctionDef) -> None:
        """Visit AsyncFunctionDef to count statements in its body."""
        self._count_body_statements(node)

    def _count_body_statements(self: typing.Self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Counts statements in the function body, excluding docstrings.

        Does not recurse into nested functions/classes.
        """
        if not node.body:
            return

        # Skip docstring if it exists
        first_stmt = node.body[0]
        start_index = 0
        if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str):
            start_index = 1

        self.count = len(node.body[start_index:])
        # Note: This simple count doesn't delve into statement types.
        # A pass statement counts, an if block counts as one, etc.

    # Do not define generic_visit to prevent counting statements in nested scopes.


def analyze_statements(file_path: str | Path, threshold: int) -> list[StatementViolation]:
    """Analyzes functions in a Python file for excessive statements.

    Args:
    ----
        file_path: Path to the Python file to analyze.
        threshold: The maximum allowed number of statements in a function.

    Returns:
    -------
        A list of tuples, where each tuple contains the
        name, line number, and statement count of a function
        exceeding the threshold.

    Raises:
    ------
        FileNotFoundError: If file_path does not exist.
        SyntaxError: If the file contains invalid Python syntax.
        OSError: For other file I/O errors.

    """
    violations: list[StatementViolation] = []
    try:
        tree, _ = _parse_file_to_ast(file_path)
        _add_parent_pointers(tree)  # Add parent pointers needed for is_method check

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Don't analyze methods for now
                is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(node, "_parents", []))
                if is_method:
                    continue

                visitor = StatementCounterVisitor()
                # Visit only the function node; the visitor handles counting its body
                visitor.visit(node)
                statement_count = visitor.count

                if statement_count > threshold:
                    violations.append((node.name, node.lineno, statement_count))
    except (FileNotFoundError, SyntaxError, OSError) as e:
        log.error(f"Could not analyze statements for {file_path}: {e}")
        raise
    except Exception as e:
        log.exception(f"Unexpected error analyzing statements for {file_path}", exc_info=e)
        raise RuntimeError(f"Unexpected error during statement analysis for {file_path}") from e

    return violations


# <<< ZEROTH LAW FOOTER >>>
