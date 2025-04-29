# FILE: src/zeroth_law/analyzer/python/ast_utils.py
"""Utilities for working with Python Abstract Syntax Trees (AST)."""

import ast
import structlog
from pathlib import Path

log = structlog.get_logger()


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


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Builds a map from each node in the AST to its parent node.

    Args:
    ----
        tree: The root node of the AST.

    Returns:
    -------
        A dictionary mapping child nodes to their parent node.

    """
    parent_map: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent_map[child] = node
    return parent_map


# <<< ZEROTH LAW FOOTER >>>
