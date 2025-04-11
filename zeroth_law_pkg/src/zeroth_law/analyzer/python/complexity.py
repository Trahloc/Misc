# FILE: src/zeroth_law/analyzer/python/complexity.py
"""Analyzes Python code for cyclomatic complexity.

Based on the radon library's approach.
"""

import ast
import logging
from pathlib import Path
from typing import Self

import ruff.complexity as ruff_complexity  # Use ruff's complexity logic

# from .ast_utils import _add_parent_pointers, _parse_file_to_ast
from .ast_utils import _build_parent_map, _parse_file_to_ast

log = logging.getLogger(__name__)

# Type alias using modern built-in generic type
ComplexityViolation = tuple[str, int, int]  # (node_name, line_number, complexity_score)

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor to calculate cyclomatic complexity of a single function/method node."""

    def __init__(self: Self, node: ast.FunctionDef | ast.AsyncFunctionDef | None = None) -> None:
        """Initialize complexity counter.

        Args:
        ----
            node: The function/async function definition node to analyze.
                  If provided, the visit starts from here.

        """
        self.complexity = 1  # Start with 1 for the function entry
        self._current_node = node  # Store the target node if provided

    def visit(self: Self, node: ast.AST) -> None:
        """Visit a node, incrementing complexity for branching constructs.

        Only visits children if the node is the target function or its descendant.
        """
        # If a target node was specified, only proceed if this node is the target or a descendant.
        # This prevents counting complexity from nested functions/classes.
        if self._current_node and not self._is_descendant_or_self(node, self._current_node):
            return  # Skip nodes outside the target function scope

        # Increment complexity for specific node types
        if isinstance(
            node,
            (
                ast.If,  # if statement
                ast.While,  # while loop
                ast.For,  # for loop
                ast.AsyncFor,  # async for loop
                ast.And,  # and operator (short-circuiting)
                ast.Or,  # or operator (short-circuiting)
                ast.Try,  # try block (base complexity)
                ast.ExceptHandler,  # except block (each handler adds complexity)
                ast.With,  # with statement (potential complexity in context manager)
                ast.AsyncWith,  # async with statement
                ast.Match,  # match statement (base complexity)
                ast.MatchAs,  # match ... as ...
                ast.MatchOr,  # or pattern in match case
                ast.IfExp,  # ternary expression (if x else y)
                ast.comprehension,  # list/dict/set comprehension (the 'if' part)
            ),
        ):
            self.complexity += 1

        # Special handling for If nodes: count elif and else branches
        if isinstance(node, ast.If) and node.orelse:
            # If there's an else block, it adds complexity
            # This count was previously missing, causing the test to fail
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # This is an elif, already counted in the loop above
                pass
            else:
                # This is an else, adds complexity
                self.complexity += 1

        # Recursively visit children
        self.generic_visit(node)

    def _is_descendant_or_self(self: Self, node: ast.AST, ancestor: ast.AST) -> bool:
        """Check if `node` is the same as `ancestor` or one of its descendants."""
        current: ast.AST | None = node
        while current:
            if current is ancestor:
                return True
            # Check if _parents attribute exists and is not empty
            parents = getattr(current, "_parents", [])
            if not parents:
                break  # Reached the root or a node without parent info
            # Move to the first parent (assuming single inheritance for simplicity here)
            current = parents[0]
        return False


def analyze_complexity(file_path: str | Path, threshold: int) -> list[ComplexityViolation]:
    """Analyzes functions in a Python file for high cyclomatic complexity.

    Args:
    ----
        file_path: Path to the Python file to analyze.
        threshold: The maximum allowed cyclomatic complexity.

    Returns:
    -------
        A list of tuples, where each tuple contains the
        name, line number, and complexity score of a function
        exceeding the threshold.

    Raises:
    ------
        FileNotFoundError: If file_path does not exist.
        SyntaxError: If the file contains invalid Python syntax.
        OSError: For other file I/O errors.

    """
    violations: list[ComplexityViolation] = []
    try:
        tree, content = _parse_file_to_ast(file_path)
        # _add_parent_pointers(tree)  # Add parent pointers needed for is_method check
        parent_map = _build_parent_map(tree)

        # Use ruff's visitor for complexity calculation
        visitor = ruff_complexity.Visitor(max_complexity=threshold, metrics={})
        visitor.visit(tree)

        for item in visitor.items:
            # Check if the complex item is a function or async function
            # We need to find the corresponding AST node to check if it's a method
            func_node = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == item.name and node.lineno == item.lineno:
                    func_node = node
                    break

            if func_node:
                # Check if it's a method
                # is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(func_node, "_parents", []))
                parent = parent_map.get(func_node)
                is_method = parent is not None and isinstance(parent, ast.ClassDef)

                # Only add violation if it's *not* a method (or adjust logic if methods should be included)
                if not is_method:
                    violations.append((item.name, item.lineno, item.complexity))
            else:
                # Ruff visitor might identify complex blocks that aren't top-level functions
                # For now, only report function complexity
                pass

    except (FileNotFoundError, SyntaxError, OSError) as e:
        log.error(f"Could not analyze complexity for {file_path}: {e}")
        # Re-raise or handle as appropriate for the calling context
        raise
    except Exception as e:
        log.exception(f"Unexpected error analyzing complexity for {file_path}", exc_info=e)
        # Re-raise or handle
        raise RuntimeError(f"Unexpected error during complexity analysis for {file_path}") from e

    return violations


# <<< ZEROTH LAW FOOTER >>>
