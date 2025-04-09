# FILE: src/zeroth_law/analyzer/python/parameters.py
"""Analyzes Python functions for excessive parameters."""

import ast
import logging
from pathlib import Path

from .ast_utils import _add_parent_pointers, _parse_file_to_ast

log = logging.getLogger(__name__)

# Type alias for violation result
ParameterViolation = tuple[str, int, int]  # (function_name, line_number, parameter_count)

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


def analyze_parameters(file_path: str | Path, threshold: int) -> list[ParameterViolation]:
    """Analyzes functions in a Python file for excessive parameters.

    Args:
    ----
        file_path: Path to the Python file to analyze.
        threshold: The maximum allowed number of parameters.

    Returns:
    -------
        A list of tuples, where each tuple contains the
        name, line number, and parameter count of a function
        exceeding the threshold.

    Raises:
    ------
        FileNotFoundError: If file_path does not exist.
        SyntaxError: If the file contains invalid Python syntax.
        OSError: For other file I/O errors.

    """
    violations: list[ParameterViolation] = []
    try:
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
    except (FileNotFoundError, SyntaxError, OSError) as e:
        log.error(f"Could not analyze parameters for {file_path}: {e}")
        raise
    except Exception as e:
        log.exception(f"Unexpected error analyzing parameters for {file_path}", exc_info=e)
        raise RuntimeError(f"Unexpected error during parameter analysis for {file_path}") from e

    return violations


# <<< ZEROTH LAW FOOTER >>>
