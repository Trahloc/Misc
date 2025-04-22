# FILE: src/zeroth_law/analyzer/python/parameters.py
"""Analyzes Python functions for excessive parameters."""

import ast
import logging
from pathlib import Path

# from .ast_utils import _add_parent_pointers, _parse_file_to_ast
from .ast_utils import _build_parent_map, _parse_file_to_ast

log = logging.getLogger(__name__)

# Type alias for violation tuple
ParameterViolation = tuple[str, int, int]

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
        # _add_parent_pointers(tree)  # Add parent pointers needed for is_method check
        parent_map = _build_parent_map(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Log node details for debugging
                # log.debug(f"Found function/async function: {getattr(node, 'name', 'N/A')} at line {getattr(node, 'lineno', 'N/A')}")
                # log.debug(f"AST Node: {ast.dump(node)}") # Dump the AST node structure

                # Don't analyze methods for now
                # is_method = any(isinstance(parent, ast.ClassDef) for parent in getattr(node, "_parents", []))
                parent = parent_map.get(node)
                is_method = parent is not None and isinstance(parent, ast.ClassDef)
                if is_method:
                    continue

                # Count parameters (args, posonlyargs, kwonlyargs, vararg, kwarg)
                # Exclude 'self' or 'cls' for methods if we analyze them later
                args = node.args
                param_count = (
                    len(args.args)
                    + len(args.posonlyargs)
                    + len(args.kwonlyargs)
                    + (1 if args.vararg else 0)
                    + (1 if args.kwarg else 0)
                )
                # Log calculated count
                # log.debug(f"Calculated param_count for {node.name}: {param_count}")

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
