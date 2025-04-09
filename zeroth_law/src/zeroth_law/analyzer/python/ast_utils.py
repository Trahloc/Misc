# FILE: src/zeroth_law/analyzer/python/ast_utils.py
"""Utilities for working with Python Abstract Syntax Trees (AST)."""

import ast
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def _parse_file_to_ast(file_path: str | Path) -> tuple[ast.Module, str]:
    """Parses a Python file into an AST module, handling potential errors.

    Args:
    ----
        file_path: The path to the Python file.

    Returns:
    -------
        A tuple containing the AST module and the file content.

    Raises:
    ------
        FileNotFoundError: If the file doesn't exist.
        SyntaxError: If the file has syntax errors.
        OSError: For other file-related OS errors.

    """
    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(path))
        return tree, content
    except FileNotFoundError:
        log.error(f"File not found during AST parsing: {path}")
        raise
    except SyntaxError as e:
        log.error(f"Syntax error parsing {path}: {e}")
        raise
    except OSError as e:
        log.error(f"OS error reading {path}: {e}")
        raise
    except Exception as e:
        # Catch any other unexpected errors during parsing
        log.exception(f"Unexpected error parsing {path}", exc_info=e)
        # Re-raise as a generic exception or a custom one if preferred
        raise RuntimeError(f"Failed to parse {path} due to an unexpected error.") from e


def _add_parent_pointers(tree: ast.AST) -> None:
    """Adds a `_parents` attribute to each node in the AST.

    This allows traversing up the tree, useful for checks like determining
    if a function is a method within a class.

    Args:
    ----
        tree: The root node of the AST.

    """
    for node in ast.walk(tree):
        node._parents = []  # Initialize the parents list for all nodes
    # Second pass to assign parents
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            if hasattr(child, "_parents"):
                child._parents.append(node)
            else:
                # This case should ideally not happen if the first loop worked
                log.warning(f"Node type {type(child).__name__} missing _parents list during assignment.")
                child._parents = [node]


# <<< ZEROTH LAW FOOTER >>>
