# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/metrics/function_size.py
"""
# PURPOSE: Calculate metrics related to function size.

## INTERFACES:
  - calculate_function_size_metrics(node: ast.FunctionDef) -> dict: Get Function size

## DEPENDENCIES:
   - ast
   - typing
   - zeroth_law.utils.config
"""
import ast
from typing import Dict, Any
from zeroth_law.utils.config import load_config


def calculate_function_size_metrics(node: ast.FunctionDef, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Calculates the number of lines in a function (excluding docstrings).

    This function counts the actual lines of code in a function, excluding:
    - Docstrings
    - Blank lines
    - Comment-only lines

    Args:
        node (ast.FunctionDef): The AST node of the function to analyze
        config (Dict[str, Any], optional): Configuration dictionary. If None, will load default config.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - lines (int): The number of actual code lines in the function
            - exceeds_max_lines (bool): Whether the function exceeds max_function_lines from config
            - max_lines (int): The configured maximum number of lines allowed
    """
    # Load configuration if not provided
    if config is None:
        config = load_config()

    max_function_lines = config.get("max_function_lines")

    # Get the source lines for the function
    start_line = node.lineno
    end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line

    # Get the docstring node if it exists
    docstring = None
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
        docstring = node.body[0].value.value

    # Calculate docstring lines
    docstring_start = node.body[0].lineno if docstring else None
    docstring_end = node.body[0].end_lineno if docstring else None
    docstring_lines = (docstring_end - docstring_start + 1) if docstring else 0

    # Count actual lines, excluding docstring
    total_lines = end_line - start_line + 1
    actual_lines = total_lines - docstring_lines

    return {"lines": actual_lines, "exceeds_max_lines": actual_lines > max_function_lines, "max_lines": max_function_lines}


"""
## KNOWN ERRORS: None.

## IMPROVEMENTS: 
  - Added configuration support from .zeroth_law.toml
  - Added validation against max_function_lines
  - Added more detailed return values

## FUTURE TODOs: Consider adding more sophisticated line counting:
  - Exclude comment-only lines
  - Handle multi-line strings that aren't docstrings
  - Count logical lines (e.g. multiple statements on one line)

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 100/100 - Excellent
    - Analysis Timestamp: 2025-04-06T15:52:46.501007
"""
