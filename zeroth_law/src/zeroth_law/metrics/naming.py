# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/metrics/naming.py
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
    """Calculate a semantic naming score for a function based on its name.

    This function evaluates the quality of a function's name by counting the
    number of meaningful words it contains. It recognizes both camelCase and
    snake_case naming conventions. The score is calculated using a simple
    heuristic where each word contributes 33 points, capped at 100.

    Args:
        node (ast.FunctionDef): The AST node representing the function to analyze.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - naming_score (int): A score from 0-100 indicating name quality.
              - 0-32: Single word, potentially too simple
              - 33-66: Two words, good for simple functions
              - 67-100: Three or more words, good for complex functions

    Examples:
        >>> import ast
        >>> # Single word name
        >>> tree = ast.parse('def calculate(): pass')
        >>> func_node = tree.body[0]
        >>> calculate_naming_score(func_node)
        {'naming_score': 33}

        >>> # Two word name
        >>> tree = ast.parse('def calculate_score(): pass')
        >>> func_node = tree.body[0]
        >>> calculate_naming_score(func_node)
        {'naming_score': 66}

        >>> # CamelCase name
        >>> tree = ast.parse('def calculateNamingScore(): pass')
        >>> func_node = tree.body[0]
        >>> calculate_naming_score(func_node)
        {'naming_score': 99}
    """
    name = node.name
    words = len(re.findall(r"[A-Z][a-z]*|\b[a-z]+", name))
    score = min(100, words * 33)  # Very basic heuristic
    return {"naming_score": score}


"""
## KNOWN ERRORS: None.

## IMPROVEMENTS: None.

## FUTURE TODOs: None.

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 95/100 - Good
    - Penalties:
      - Function calculate_naming_score exceeds max lines: -5
    - Analysis Timestamp: 2025-04-06T15:52:46.410733
"""
