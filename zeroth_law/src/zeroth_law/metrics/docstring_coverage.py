# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/metrics/docstring_coverage.py
"""
# PURPOSE: Check for the presence of a docstring in a function.

## INTERFACES:
 - calculate_docstring_coverage(node: ast.FunctionDef) -> dict: Get Docstring presence

## DEPENDENCIES:
  - ast
"""

import ast
from typing import Dict, Any


def calculate_docstring_coverage(node: ast.FunctionDef) -> Dict[str, Any]:
    """Check if a function has a docstring and return coverage information.

    This function analyzes a Python function's AST node to determine if it has
    a docstring. A docstring is considered present if there is a string literal
    as the first statement in the function body.

    Args:
        node (ast.FunctionDef): The AST node representing the function to analyze.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - has_docstring (bool): True if the function has a docstring,
              False otherwise.

    Note:
        A function is considered to have a docstring if it has a string literal
        as its first statement. For example:

        def example():
            '''This is a docstring.'''
            pass

        The function above would return {'has_docstring': True}.
    """
    has_docstring = ast.get_docstring(node) is not None
    return {"has_docstring": has_docstring}


"""
## KNOWN ERRORS: None.

## IMPROVEMENTS: None.

## FUTURE TODOs: Consider adding more sophisticated docstring analysis, such as checking for docstring quality.

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 95/100 - Good
    - Penalties:
      - Function calculate_docstring_coverage exceeds max lines: -5
    - Analysis Timestamp: 2025-04-06T15:52:46.677626
"""
