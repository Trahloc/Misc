# FILE: src/zeroth_law/analyzer/python/statements.py
"""Analyzes Python functions for excessive statement counts."""

import ast
from io import BytesIO
import structlog
import tokenize
from pathlib import Path
from typing import List, Tuple, Dict, Any

# from .ast_utils import _add_parent_pointers, _parse_file_to_ast
from .ast_utils import _build_parent_map, _parse_file_to_ast

log = structlog.get_logger()

# Type alias for violation tuple
StatementViolation = tuple[str, int, int]  # (node_name, line_number, statement_count)

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


class StatementCounterVisitor(ast.NodeVisitor):
    """Counts executable statements within a visited function node.
    Recursively visits statement nodes within the function, excluding nested functions/classes.
    """

    def __init__(self: Any) -> None:
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
            # Attempt to exclude docstrings specifically
            if (
                isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
                # Additional check: Check if it's the first node in a function/class/module body?
                # This requires parent info, which is complex. Let's use a simpler heuristic for now.
                # TODO: Revisit robust docstring detection.
            ):
                # Assume top-level Expr with string Constant is a docstring for now.
                # This might incorrectly exclude intended string literal statements.
                return False  # Don't count likely docstrings
            return True  # Count other Expr statements
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

        # Recurse only if it's a compound statement OR not a statement at all (e.g., BoolOp)
        # The check `not is_stmt` ensures we visit nodes like BoolOp whose operands are statements
        if needs_recursion or not is_stmt:
            super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Entry point for counting statements in a function.
        Relies on the generic visit and _is_statement_node to handle body.
        """
        # Process the entire body, relying on visit/_is_statement_node to filter
        for stmt in node.body:
            self.visit(stmt)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Entry point for counting statements in an async function.
        Relies on the generic visit and _is_statement_node to handle body.
        """
        # Process the entire body, relying on visit/_is_statement_node to filter
        for stmt in node.body:
            self.visit(stmt)


def analyze_statements(file_path: str | Path, threshold: int) -> list[StatementViolation]:
    """Analyzes functions in a Python file for excessive statements.

    Args:
    ----
        file_path: Path to the Python file.
        threshold: Maximum allowed statements per function.

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
        parent_map: dict[ast.AST, ast.AST] = _build_parent_map(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                parent: ast.AST | None = parent_map.get(node)
                is_method: bool = parent is not None and isinstance(parent, ast.ClassDef)
                if is_method:
                    continue

                visitor = StatementCounterVisitor()
                visitor.visit(node)
                statement_count = visitor.count
                # Add debug logging
                log.debug(
                    f"Function: {node.name}, Line: {node.lineno}, Counted Statements: {statement_count}, Threshold: {threshold}"
                )
                if statement_count >= threshold:
                    # Use node.lineno - assuming it now points to start of signature/decorators
                    log.debug(
                        f"Reporting violation for {node.name} with {statement_count} statements against threshold {threshold}"
                    )
                    violations.append((node.name, node.lineno, statement_count))

    except (FileNotFoundError, SyntaxError, OSError) as e:
        log.error(f"Could not analyze statements for {file_path}: {e}")
        raise
    except Exception as e:
        log.exception(f"Unexpected error analyzing statements for {file_path}", exc_info=e)
        raise RuntimeError(f"Unexpected error during statement analysis for {file_path}") from e

    return violations


# <<< ZEROTH LAW FOOTER >>>
