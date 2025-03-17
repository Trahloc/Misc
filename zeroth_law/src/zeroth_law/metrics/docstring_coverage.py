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
    """Checks if a function has a docstring."""
    has_docstring = ast.get_docstring(node) is not None
    return {"has_docstring": has_docstring}
