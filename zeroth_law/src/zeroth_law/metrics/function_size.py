# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/metrics/function_size.py
"""
# PURPOSE: Calculate metrics related to function size.

## INTERFACES:
  - calculate_function_size_metrics(node: ast.FunctionDef) -> dict: Get Function size

## DEPENDENCIES:
   - ast
"""
import ast
from typing import Dict, Any

def calculate_function_size_metrics(node: ast.FunctionDef) -> Dict[str, Any]:
    """Calculates the number of lines in a function (excluding docstrings)."""
    lines = 0
    for n in ast.walk(node):
      if isinstance(n, ast.stmt) and not isinstance(n, ast.Expr) or not (hasattr(n, 'value') and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)):
        lines += 1
    return {"lines": lines}
