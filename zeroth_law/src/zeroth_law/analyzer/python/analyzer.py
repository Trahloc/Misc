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
ParameterViolation = tuple[str, int, int]  # (function_name, line_number, parameter_count)
StatementViolation = tuple[str, int, int]  # (function_name, line_number, statement_count)
LineCountViolation = tuple[str, int, int]  # (issue_type, line_number, count)

EXPECTED_HEADER_LINES = 2  # Constant for magic number 2

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
            child._parents = [*getattr(child, "_parents", []), node_]  # type: ignore[attr-defined] # noqa: SLF001
            # Using type: ignore because _parents is dynamically added


# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


class ComplexityVisitor(ast.NodeVisitor):
    """Calculates cyclomatic complexity for a visited function node."""

    def __init__(self: typing.Self) -> None:
        """Initialize complexity counter for the function being visited."""
        self.complexity = 1  # Start with a base complexity of 1 for the function entry

    def visit_FunctionDef(self: typing.Self, node: ast.FunctionDef) -> None:  # noqa: N802
        """Visit FunctionDef node."""
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self: typing.Self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        """Visit AsyncFunctionDef node."""
        self.generic_visit(node)

    # Separate methods for different control flow/branching nodes
    def visit_If(self: typing.Self, node: ast.If) -> None:  # noqa: N802
        """Visit If node."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self: typing.Self, node: ast.For | ast.AsyncFor) -> None:  # noqa: N802
        """Visit For or AsyncFor node."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self: typing.Self, node: ast.While) -> None:  # noqa: N802
        """Visit While node."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self: typing.Self, node: ast.ExceptHandler) -> None:  # noqa: N802
        """Visit ExceptHandler node."""
        self.generic_visit(node)

    def visit_With(self: typing.Self, node: ast.With | ast.AsyncWith) -> None:  # noqa: N802
        """Visit With or AsyncWith node."""
        self.generic_visit(node)

    def visit_Assert(self: typing.Self, node: ast.Assert) -> None:  # noqa: N802
        """Visit Assert node."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self: typing.Self, node: ast.Try) -> None:  # noqa: N802
        """Visit Try node."""
        self.complexity += len(node.handlers)
        self.generic_visit(node)  # Also visit children

    def visit_BoolOp(self: typing.Self, node: ast.BoolOp) -> None:  # noqa: N802
        """Visit BoolOp node."""
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

    def visit_FunctionDef(self: typing.Self, node: ast.FunctionDef) -> None:  # noqa: N802
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

    def visit_AsyncFunctionDef(self: typing.Self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
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
# TODO: [impl/header] Implement minimal header check logic.
def check_header_compliance(file_path: str | Path) -> list[str]:  # Renamed from analyze_header_footer, return list of codes
    """Check if a file starts with the required Zeroth Law header.

    Args:
    ----
        file_path: The path to the Python file.

    Returns:
    -------
        A list of error codes (strings) if non-compliant, empty list otherwise.
        Possible error codes: HEADER_MISSING_FILE_LINE, HEADER_MISSING_DOCSTRING_START,
                          FILE_NOT_FOUND, HEADER_CHECK_ERROR.

    """
    errors: list[str] = []
    lines: list[str] = []  # Initialize lines here
    try:
        # Use Path object for consistency
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            # Read up to 2 lines, strip whitespace
            lines = [line.strip() for line in [f.readline(), f.readline()] if line]  # Ensure lines aren't empty strings

        # Check line 1
        if len(lines) < 1 or not lines[0].startswith("# FILE:"):
            errors.append("HEADER_MISSING_FILE_LINE")
        # Check line 2
        if len(lines) < EXPECTED_HEADER_LINES or not lines[1].startswith('"""'):  # Use constant
            errors.append("HEADER_MISSING_DOCSTRING_START")

    except FileNotFoundError:
        errors.append("FILE_NOT_FOUND")
    except OSError as e:  # Catch OS level file errors (includes FileNotFoundError, PermissionError, etc.)
        # Avoid adding duplicate FILE_NOT_FOUND if already caught
        if "FILE_NOT_FOUND" not in errors:
            errors.append(f"HEADER_CHECK_OS_ERROR: {e}")
    # If we really need to catch anything else, log it and report generic error
    # except Exception as e:
    #     log.exception("Unexpected error during header check", file=str(path), exc_info=e) # Assumes logger `log` exists
    #     errors.append(f"HEADER_CHECK_UNEXPECTED_ERROR") # Avoid leaking details

    return errors


# TODO: Re-implement footer check (analyze_header_footer previously did both)
def check_footer_compliance(file_path: str | Path) -> list[str]:
    """Check if a file contains the required Zeroth Law footer marker.

    Args:
    ----
        file_path: The path to the Python file.

    Returns:
    -------
        A list containing 'FOOTER_MISSING' if the marker is not found,
        otherwise an empty list. Possible error codes: FOOTER_MISSING,
        FILE_NOT_FOUND, FOOTER_CHECK_OS_ERROR.

    """
    errors: list[str] = []
    required_footer_marker = "## ZEROTH LAW COMPLIANCE:"
    try:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        if required_footer_marker not in content:
            errors.append("FOOTER_MISSING")
    except FileNotFoundError:
        errors.append("FILE_NOT_FOUND")
    except OSError as e:
        errors.append(f"FOOTER_CHECK_OS_ERROR: {e}")
    # Not catching broad Exception here

    return errors


# TODO: Create main compliance checking function that calls individual checks like header, footer, etc.


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


# --- Parameter Analysis ---
def analyze_parameters(file_path: str | Path, threshold: int) -> list[ParameterViolation]:
    """Analyzes functions in a Python file for excessive parameters.

    PURPOSE:
      Counts parameters for each function/async function and returns those
      exceeding the specified threshold.

    PARAMS:
      file_path (str | Path): Path to the Python file to analyze.
      threshold (int): The maximum allowed number of parameters.

    Returns
    -------
      list[ParameterViolation]: A list of tuples, where each tuple contains the
                                name, line number, and parameter count of a function
                                exceeding the threshold.

    EXCEPTIONS:
      FileNotFoundError: If file_path does not exist.
      SyntaxError: If the file contains invalid Python syntax.

    """
    violations: list[ParameterViolation] = []
    tree, _ = _parse_file_to_ast(file_path)
    _add_parent_pointers(tree)  # Add parent pointers needed for is_method check

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # Don't analyze methods for now
            is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(node, "_parents", []))
            if is_method:
                continue

            # Count parameters (args, posonlyargs, kwonlyargs, vararg, kwarg)
            # Exclude 'self' or 'cls' for methods if we analyze them later
            args = node.args
            param_count = (
                len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs) + (1 if args.vararg else 0) + (1 if args.kwarg else 0)
            )

            if param_count > threshold:
                violations.append((node.name, node.lineno, param_count))

    return violations


# --- Statement Analysis ---
class StatementCounterVisitor(ast.NodeVisitor):
    """Counts executable statements within a visited function node."""

    def __init__(self: typing.Self) -> None:
        """Initialize statement counter."""
        self.count = 0

    def visit(self: typing.Self, node: ast.AST) -> None:
        """Override visit to count direct statements in a function body."""
        # We only want to count statements directly within the function body,
        # not within nested functions or classes defined inside.
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for stmt in node.body:
                # Exclude docstrings
                is_docstring = isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)
                if not is_docstring:
                    self.count += 1
        # Do not call generic_visit here, we are only counting top-level statements in the func.


def analyze_statements(file_path: str | Path, threshold: int) -> list[StatementViolation]:
    """Analyzes functions in a Python file for excessive statements.

    PURPOSE:
      Counts executable statements within each function/async function and returns
      those exceeding the specified threshold.
      Note: This is a simple count, not accounting for nested complexity.

    PARAMS:
      file_path (str | Path): Path to the Python file to analyze.
      threshold (int): The maximum allowed number of statements.

    Returns
    -------
      list[StatementViolation]: A list of tuples, where each tuple contains the
                                name, line number, and statement count of a function
                                exceeding the threshold.

    EXCEPTIONS:
      FileNotFoundError: If file_path does not exist.
      SyntaxError: If the file contains invalid Python syntax.

    """
    violations: list[StatementViolation] = []
    tree, _ = _parse_file_to_ast(file_path)
    _add_parent_pointers(tree)  # Add parent pointers needed for is_method check

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # Don't analyze methods for now
            is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(node, "_parents", []))
            if is_method:
                continue

            visitor = StatementCounterVisitor()
            visitor.visit(node)  # Count statements within this function node
            statement_count = visitor.count

            if statement_count > threshold:
                violations.append((node.name, node.lineno, statement_count))

    return violations


# --- Line Count Analysis Helpers ---


def _get_ast_docstring_lines(content: str) -> set[int]:
    """Parse content and return line numbers occupied by AST docstrings."""
    docstring_lines = set()
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                doc = ast.get_docstring(node, clean=False)
                if (
                    doc
                    and node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and node.body[0].value.value == doc
                ):
                    start = node.body[0].lineno
                    end = node.body[0].end_lineno
                    if start is not None and end is not None:
                        for i in range(start, end + 1):
                            docstring_lines.add(i)
    except SyntaxError:
        # If parsing fails, we can't reliably detect AST docstrings
        pass
    return docstring_lines


def _handle_triple_quotes_fallback(
    line_num: int, stripped_line: str, in_docstring_state: tuple[bool, str | None], docstring_lines: set[int]
) -> tuple[bool, str | None, bool]:
    """Handle fallback detection of triple-quoted strings (non-AST aware).

    Returns a tuple: (new_in_docstring, new_docstring_quotes, should_count_line)
    """
    in_docstring, docstring_quotes = in_docstring_state
    should_count = False

    min_single_line_len = 6

    if not in_docstring:
        if stripped_line.startswith(('"""', "'''")):
            in_docstring = True
            docstring_quotes = stripped_line[:3]
            if stripped_line.endswith(docstring_quotes) and len(stripped_line) >= min_single_line_len:
                in_docstring = False  # Single line block
            # Count the start line only if not part of an AST docstring
            if line_num not in docstring_lines:
                should_count = True
        elif line_num not in docstring_lines:  # Not starting triple quote and not AST docstring
            should_count = True
    # Inside a triple-quoted block detected by this fallback logic
    elif docstring_quotes is not None and stripped_line.endswith(docstring_quotes):
        in_docstring = False
        # Count the end line only if not part of an AST docstring
        if line_num not in docstring_lines:
            should_count = True
    elif line_num not in docstring_lines:  # Inside block, but not AST docstring line
        should_count = True

    return in_docstring, docstring_quotes, should_count


# --- Line Count Analysis ---
def _count_executable_lines(content: str) -> int:
    """Count executable lines, excluding comments, blank lines, and docstrings."""
    lines = content.splitlines()
    count = 0
    # Mypy Fix: Explicitly type hint the state tuple
    in_docstring_fallback_state: tuple[bool, str | None] = (False, None)

    # Get line numbers covered by reliably identified AST docstrings
    docstring_lines = _get_ast_docstring_lines(content)

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip blank lines and comment-only lines
        if not stripped or stripped.startswith("#"):
            continue

        # Skip lines identified as part of AST docstrings
        if i in docstring_lines:
            continue

        # Handle potential triple-quoted strings not caught by AST (fallback)
        # and determine if the line should be counted based on this fallback state
        in_docstring, quotes, should_count = _handle_triple_quotes_fallback(i, stripped, in_docstring_fallback_state, docstring_lines)
        in_docstring_fallback_state = (in_docstring, quotes)

        if should_count:
            count += 1

    return count


def analyze_line_counts(file_path: str | Path, max_exec_lines: int) -> list[LineCountViolation]:
    """Analyzes a Python file for total executable line count.

    PURPOSE:
      Counts executable lines (excluding blank lines, comments, and docstrings)
      and checks if the total exceeds the threshold.

    PARAMS:
      file_path (str | Path): Path to the Python file to analyze.
      max_exec_lines (int): The maximum allowed number of executable lines.

    Returns
    -------
      list[LineCountViolation]: List containing violation if threshold exceeded.
                                 e.g., [("max_executable_lines", 1, count)]

    """
    violations: list[LineCountViolation] = []
    executable_line_count = 0
    in_docstring_fallback = False
    docstring_quotes_fallback = None

    try:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        # Get line numbers occupied by docstrings recognized by AST
        ast_docstring_lines = _get_ast_docstring_lines(content)

        for i, line in enumerate(lines):
            line_num = i + 1
            stripped_line = line.strip()

            # Skip blank lines
            if not stripped_line:
                continue

            # Skip full-line comments
            if stripped_line.startswith("#"):
                continue

            # Skip lines identified as AST docstrings
            if line_num in ast_docstring_lines:
                continue

            # Fallback for triple-quoted strings not caught by AST (e.g., SyntaxError)
            # NOTE: This fallback is complex and might be imperfect.
            # Re-evaluate if this complexity is truly needed or if relying
            # solely on AST check + simple comment check is sufficient.
            (
                in_docstring_fallback,
                docstring_quotes_fallback,
                should_count_line,
            ) = _handle_triple_quotes_fallback(
                line_num,
                stripped_line,
                (in_docstring_fallback, docstring_quotes_fallback),
                ast_docstring_lines,
            )

            if should_count_line:
                executable_line_count += 1
            # Handle case where AST parsing failed but we detect start/end
            # elif not ast_docstring_lines and not should_count_line:
            # If AST failed, and fallback says don't count (because it thinks
            # it's a docstring start/end line), then we skip.
            #     pass

        if executable_line_count > max_exec_lines:
            violations.append(("max_executable_lines", 1, executable_line_count))

    except FileNotFoundError:
        violations.append(("FILE_NOT_FOUND", 1, 0))
    except OSError as e:
        violations.append((f"LINE_COUNT_OS_ERROR: {e}", 1, 0))
    # Ignore SyntaxError for line counting, try to count what we can

    return violations


# --- Main Analyzer Orchestration (Placeholder) ---
# TODO: Create a main function/class that takes config and runs all checks.


# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
"""
## LIMITATIONS & RISKS:
# - Only checks top-level functions (not methods in classes for D103).
# - Docstring check is basic (checks if the first statement is Expr(Constant(str))).
# - Cyclomatic complexity visitor is basic and may differ from tools like radon.
# - Parameter counting doesn't exclude self/cls yet (as methods aren't analyzed).
# - Statement counting is basic (top-level only) and may differ from tools like Pylint.
# - Doesn't handle all edge cases of AST structure perfectly.

## REFINEMENT IDEAS:
# - Integrate check for D102 (missing docstring in public method).
# - Integrate check for D100 (missing docstring in public module).
# - Header/Footer: Improve robustness beyond simple string search for footer.
# - Complexity: Consider using the external `radon` library for more robust metrics or as a benchmark.
# - Docstrings/Parameters/Statements: While Ruff/Pylint offer similar checks (e.g., D103, PLR0913, PLR0915),
#   maintaining custom checks here allows for centralized configuration within [tool.zeroth_law]
#   and potential future custom scoring/reporting. Standard tool rules serve as valuable references.
# - Configuration: Explore mechanisms to optionally sync relevant [tool.zeroth_law] settings
#   (e.g., max-parameters) downstream to tools like Ruff/Pylint if desired for consistency.
# - Create a more generic Analyzer class structure to run checks more efficiently.

## ZEROTH LAW COMPLIANCE:
# Framework Version: 2025-04-08-tdd
# TDD Cycle: Green (test_find_missing_public_function_docstrings)
# Last Check: <timestamp>
# Score: <score>
# Penalties: <penalties>
"""
