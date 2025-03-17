#/zeroth_law/metrics/naming.py
"""
# PURPOSE: Evaluate semantic naming (very simplified).

## INTERFACES:
 - calculate_naming_score(node: ast.FunctionDef) -> dict: Calculate basic semantic naming score.

## DEPENDENCIES:
  - ast
"""
import ast
import re
from typing import Dict, Any

def calculate_naming_score(node: ast.FunctionDef) -> Dict[str, Any]:
    """Calculates a simplified naming score based on word count."""
    name = node.name
    words = len(re.findall(r'[A-Z][a-z]*|\b[a-z]+', name))
    score = min(100, words * 33)  # Very basic heuristic
    return {"naming_score": score}
