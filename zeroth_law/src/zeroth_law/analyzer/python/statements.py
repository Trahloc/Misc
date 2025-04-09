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
    """Counts executable statements within a visited function node.
    Recursively visits statement nodes within the function, excluding nested functions/classes.
    """

    def __init__(self: typing.Self) -> None:
        """Initialize statement counter."""
        self.count = 0

    def _is_statement_node(self, node: ast.AST) -> bool:
        """Check if a node represents a countable executable statement."""
        # Basic statements
        if isinstance(
            node,
            (
                ast.Assign,
                ast.AugAssign,
                ast.AnnAssign,  # Count annotated assignments
                ast.Return,
                ast.Raise,
                ast.Assert,
                ast.Delete,
                ast.Pass,  # Decide if pass should count (currently yes)
                ast.Break,
                ast.Continue,
                ast.Import,  # Count imports?
                ast.ImportFrom,
            ),
        ):
            return True
        # Expression statements (like function calls that don't assign)
        if isinstance(node, ast.Expr):
            return True
        # Control flow structures also count as statements themselves
        if isinstance(
            node,
            (
                ast.If,  # Count the if itself
                ast.For,  # Count the for loop itself
                ast.While,  # Count the while loop itself
                ast.With,  # Count the with block itself
                ast.Try,  # Count the try block itself
            ),
        ):
            return True
        return False

    def visit(self, node: ast.AST) -> None:
        """Visit nodes, count statements, and recurse appropriately."""
        is_stmt = self._is_statement_node(node)
        needs_recursion = isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.With,
                ast.Try,
                # Note: Add AsyncFor, AsyncWith if needed
            ),
        )

        if is_stmt:
            self.count += 1

        # Prevent recursion into nested functions or classes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # As before, assume entry point is visit_FunctionDef/Async
            return

        # Recurse only if it's a compound statement OR not a statement at all (e.g., BoolOp)
        if needs_recursion or not is_stmt:
            super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Entry point for counting statements in a function."""
        # Skip docstring before counting
        body_to_visit = node.body
        if body_to_visit and isinstance(body_to_visit[0], ast.Expr) and isinstance(body_to_visit[0].value, ast.Constant):
            body_to_visit = body_to_visit[1:]

        for stmt in body_to_visit:
            self.visit(stmt)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Entry point for counting statements in an async function."""
        # Skip docstring before counting
        body_to_visit = node.body
        if body_to_visit and isinstance(body_to_visit[0], ast.Expr) and isinstance(body_to_visit[0].value, ast.Constant):
            body_to_visit = body_to_visit[1:]

        for stmt in body_to_visit:
            self.visit(stmt)


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
                is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(node, "_parents", []))
                if is_method:
                    continue

                visitor = StatementCounterVisitor()
                # Explicitly call visit_FunctionDef/Async which now handles traversal
                if isinstance(node, ast.FunctionDef):
                    visitor.visit_FunctionDef(node)
                else:  # AsyncFunctionDef
                    visitor.visit_AsyncFunctionDef(node)

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
