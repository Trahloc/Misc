# FILE: src/zeroth_law/analyzer.py
"""Provides functions for analyzing Python source code files.

CONTEXT:
  Developed via TDD. Initial focus is checking for missing docstrings
  in public functions (Rule D103).
  Extended to check for header/footer presence (Principle #11).
"""

import ast
import typing
from pathlib import Path

# Define type aliases for the results for clarity
DocstringViolation = tuple[str, int]  # (function_name, line_number)
StructureViolation = tuple[str, int]  # (issue_type, line_number)
ComplexityViolation = tuple[str, int, int]  # (function_name, line_number, complexity_score)

# ----------------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------------


def _parse_file_to_ast(file_path: str | Path) -> tuple[ast.Module, str]:
    """Read and parse a Python file, returning the AST module and content.

    Handle FileNotFoundError and SyntaxError.
    """
    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(path))
    except FileNotFoundError as err:
        msg = f"File not found for analysis: {file_path}"
        raise FileNotFoundError(msg) from err
    except SyntaxError:
        # Re-raising SyntaxError directly is often best (TRY201)
        raise
    else:
        # Return only if try block succeeded without exceptions
        return tree, content


def _add_parent_pointers(tree: ast.AST) -> None:
    """Add a `_parents` attribute to each node in the AST tree."""
    for node_ in ast.walk(tree):
        for child in ast.iter_child_nodes(node_):
            child._parents = [*getattr(child, "_parents", []), node_]  # type: ignore[attr-defined]
            # Using type: ignore because _parents is dynamically added


# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


class ComplexityVisitor(ast.NodeVisitor):
    """Calculates cyclomatic complexity for a visited function node."""

    def __init__(self: typing.Self) -> None:
        """Initialize complexity counter for the function being visited."""
        self.complexity = 1  # Start with a base complexity of 1 for the function entry

    def visit_If(self: typing.Self, node: ast.If | ast.AsyncFor | ast.For | ast.While | ast.ExceptHandler | ast.With) -> None:
        """Increment complexity for control flow branching statements."""
        self.complexity += 1
        # Also visit children to catch nested complexity
        self.generic_visit(node)

    def visit_Assert(self: typing.Self, node: ast.Assert) -> None:
        """Increment complexity for assert statements."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self: typing.Self, node: ast.Try) -> None:
        """Increment complexity for each `except` block."""
        # The try block itself doesn't add complexity, but each handler does
        self.complexity += len(node.handlers)
        self.generic_visit(node)

    def visit_BoolOp(self: typing.Self, node: ast.BoolOp) -> None:
        """Increment complexity for each 'and'/'or' operator."""
        # Each operator (and/or) after the first one adds a path
        if isinstance(node.op, ast.And | ast.Or):
            self.complexity += len(node.values) - 1
        self.generic_visit(node)

    # Other node types like Break, Continue, Raise could also arguably add complexity
    # depending on the exact definition used, but we'll stick to common ones for now.


class DocstringVisitor(ast.NodeVisitor):
    """An AST visitor that collects public functions/methods missing docstrings."""

    def __init__(self: typing.Self) -> None:
        """Initialize the visitor."""
        self.violations: list[DocstringViolation] = []

    def visit_FunctionDef(self: typing.Self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        # Calculate if it's a method first
        is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(node, "_parents", []))

        # Check if public function and not a method
        if not node.name.startswith("_") and not is_method:
            # Check for docstring (first node is Expr(Constant(str)))
            has_docstring = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            if not has_docstring:
                self.violations.append((node.name, node.lineno))

        # Continue visiting children ONLY if not inside a class
        if not is_method:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self: typing.Self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(node, "_parents", []))

        # Check if public function and not a method
        if not node.name.startswith("_") and not is_method:
            # Check for docstring
            has_docstring = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            if not has_docstring:
                self.violations.append((node.name, node.lineno))

        # Continue visiting children ONLY if not inside a class
        if not is_method:
            self.generic_visit(node)

    # Explicitly stop visiting ClassDef children for now
    # def visit_ClassDef(self, node: ast.ClassDef) -> None:
    #     pass # Do not visit children of classes


def analyze_docstrings(file_path: str | Path) -> list[DocstringViolation]:
    """Analyzes a Python file for missing docstrings in public functions (D103).

    PURPOSE:
      Identifies top-level public functions and async functions that lack
      a docstring immediately following their definition.

    PARAMS:
      file_path (str | Path): Path to the Python file to analyze.

    Returns
    -------
      list[DocstringViolation]: A list of tuples, where each tuple contains the
                                name and line number of a function missing a docstring.

    EXCEPTIONS:
      FileNotFoundError: If file_path does not exist.
      SyntaxError: If the file contains invalid Python syntax.

    USAGE EXAMPLES:
      >>> # Create a dummy file:
      >>> # def func_ok():
      >>> #   '''Doc here.''' # Use single quotes inside example
      >>> #   pass
      >>> # def func_bad():
      >>> #   pass
      >>> analyze_docstrings("dummy.py") # doctest: +SKIP
      [('func_bad', 5)]

    """
    tree, _ = _parse_file_to_ast(file_path)  # Unpack tuple, only need tree
    _add_parent_pointers(tree)  # Visitor requires parent info

    visitor = DocstringVisitor()
    visitor.visit(tree)
    return visitor.violations


# --- Header/Footer Analysis ---
def analyze_header_footer(file_path: str | Path) -> list[StructureViolation]:
    """Analyzes a Python file for missing header and footer comments.

    PURPOSE:
      Checks if the file starts with a module-level docstring (header) and
      ends with a specific Zeroth Law compliance comment block (footer),
      as required by Principle #11.

    PARAMS:
      file_path (str | Path): Path to the Python file to analyze.

    Returns
    -------
      list[StructureViolation]: A list of tuples indicating structural issues,
                                such as ("missing_header", 1) or
                                ("missing_footer", line_num).

    EXCEPTIONS:
      FileNotFoundError: If file_path does not exist.
      SyntaxError: If the file contains invalid Python syntax.

    """
    violations: list[StructureViolation] = []
    # Get both tree and content from the helper
    tree, content = _parse_file_to_ast(file_path)

    # Check for module-level docstring (header)
    has_header = (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    )
    if not has_header:
        violations.append(("missing_header", 1))

    # Check for Zeroth Law footer
    # A simple string search is sufficient and avoids AST complexity for trailing comments/docstrings
    # The required marker is "## ZEROTH LAW COMPLIANCE:"
    required_footer_marker = "## ZEROTH LAW COMPLIANCE:"
    if required_footer_marker not in content:
        # Report the violation at the end of the file
        last_line_num = len(content.splitlines())
        violations.append(("missing_footer", last_line_num + 1))

    return violations


# --- Complexity Analysis ---
def analyze_complexity(file_path: str | Path, threshold: int) -> list[ComplexityViolation]:
    """Analyzes functions in a Python file for high cyclomatic complexity.

    PURPOSE:
      Calculates cyclomatic complexity for each function/async function
      and returns those exceeding the specified threshold.

    PARAMS:
      file_path (str | Path): Path to the Python file to analyze.
      threshold (int): The maximum allowed cyclomatic complexity.

    Returns
    -------
      list[ComplexityViolation]: A list of tuples, where each tuple contains the
                                 name, line number, and complexity score of a function
                                 exceeding the threshold.

    EXCEPTIONS:
      FileNotFoundError: If file_path does not exist.
      SyntaxError: If the file contains invalid Python syntax.

    """
    violations: list[ComplexityViolation] = []
    tree, _ = _parse_file_to_ast(file_path)
    _add_parent_pointers(tree)  # Add parent pointers needed for is_method check

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # Don't analyze methods for now, similar to docstring check
            is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(node, "_parents", []))
            if is_method:
                continue

            visitor = ComplexityVisitor()
            # Visit only the current function node and its children
            visitor.visit(node)
            complexity = visitor.complexity

            if complexity > threshold:
                violations.append((node.name, node.lineno, complexity))

    return violations


# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
"""
## LIMITATIONS & RISKS:
# - Only checks top-level functions (not methods in classes for D103).
# - Docstring check is basic (checks if the first statement is Expr(Constant(str))).
# - Doesn't handle all edge cases of AST structure perfectly.

## REFINEMENT IDEAS:
# - Integrate check for D102 (missing docstring in public method).
# - Integrate check for D100 (missing docstring in public module).
# - Improve robustness of docstring detection.
# - Create a more generic Analyzer class structure.

## ZEROTH LAW COMPLIANCE:
# Framework Version: 2025-04-08-tdd
# TDD Cycle: Green (test_find_missing_public_function_docstrings)
# Last Check: <timestamp>
# Score: <score>
# Penalties: <penalties>
"""
