# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/metrics/imports.py
"""
# PURPOSE: Analyze import statements for context independence

## INTERFACES:
  - calculate_import_metrics(tree: ast.AST) -> dict: Analyze imports

## DEPENDENCIES:
    ast
"""
import ast
from typing import Dict, Any


def calculate_import_metrics(tree: ast.AST) -> Dict[str, Any]:
    """Counts the number of imports as a simple measure of context independence"""
    import_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_count += 1

    imports_score = max(0, 100 - import_count * 5)

    return {"import_count": import_count, "imports_score": imports_score}
