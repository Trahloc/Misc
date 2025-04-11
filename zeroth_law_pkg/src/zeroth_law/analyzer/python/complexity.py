# FILE: src/zeroth_law/analyzer/python/complexity.py
"""Analyzes Python code for cyclomatic complexity.

Based on the radon library's approach.
"""

import ast
import logging
from pathlib import Path
from typing import Self

# Removed problematic import: import ruff.complexity as ruff_complexity
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
        self._target_node = node  # Store the target node if provided
        if node:
            # If node provided, visit it immediately to calculate complexity
            self.visit(node)

    def visit(self: Self, node: ast.AST) -> None:
        """Visit a node, incrementing complexity for branching constructs.

        Only visits children if the node is the target function or its descendant.
        Stops recursion into nested functions/classes defined within the target.
        """
        is_branching = False

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
                # ast.With,  # Exclude simple with (radon doesn't count)
                # ast.AsyncWith, # Exclude simple async with
                ast.Match,  # match statement (base complexity)
                ast.MatchAs,  # match ... as ...
                ast.MatchOr,  # or pattern in match case
                ast.IfExp,  # ternary expression (if x else y)
                ast.Assert,  # Assert statement adds complexity
                # Comprehensions: The `if` part adds complexity
                ast.ListComp,
                ast.SetComp,
                ast.DictComp,
                ast.GeneratorExp,
            ),
        ):
            is_branching = True
            self.complexity += 1

        # Special handling for Try: need to investigate if `finally` adds complexity
        # if isinstance(node, ast.Try) and node.finalbody:
        #    self.complexity += 1 # If finally always adds

        # Special handling for comprehensions - the ifs inside add complexity
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for gen in node.generators:
                for if_clause in gen.ifs:
                    self.complexity += 1  # Each 'if' in the comprehension
                    self.visit(if_clause)  # Visit the condition itself for and/or

        # Recurse into children, BUT stop if we encounter a nested function/class
        # Only visit children if the current node is not a nested definition
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) or node is self._target_node:
            # If it's the target node itself, we definitely visit its children
            # If it's not a definition, visit children
            super().generic_visit(node)

        # Note: The previous _is_descendant_or_self logic was complex and potentially buggy.
        # This simpler approach stops recursion *into* nested definitions.

    # No longer need _is_descendant_or_self


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
        tree, _ = _parse_file_to_ast(file_path)
        parent_map = _build_parent_map(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Check if it's a method (defined inside a class)
                parent = parent_map.get(node)
                is_method = parent is not None and isinstance(parent, ast.ClassDef)

                # For now, analyze both functions and methods
                # if is_method:
                #     continue # Optionally skip methods

                # Use the local ComplexityVisitor
                visitor = ComplexityVisitor(node=node)  # Pass the function node to the constructor
                complexity_score = visitor.complexity

                if complexity_score > threshold:
                    violations.append((node.name, node.lineno, complexity_score))

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
