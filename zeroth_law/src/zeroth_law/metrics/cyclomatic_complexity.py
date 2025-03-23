# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/metrics/cyclomatic_complexity.py
"""
# PURPOSE: Calculate the cyclomatic complexity of a function.

## INTERFACES:
 - calculate_cyclomatic_complexity(node: ast.FunctionDef) -> dict: Get the cyclomatic complexity of a function

## DEPENDENCIES:
 - ast
"""
import ast
from typing import Dict, Any


class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """Visitor to count cyclomatic complexity."""

    def __init__(self):
        self.complexity = 1

    def visit_If(self, node: ast.If):
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp):  # Add IfExp (ternary operator)
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        self.complexity += len(node.handlers)
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert):  # Count asserts
        self.complexity += 1
        self.generic_visit(node)


def calculate_cyclomatic_complexity(node: ast.FunctionDef) -> Dict[str, Any]:
    """Calculates the cyclomatic complexity of a function."""
    visitor = CyclomaticComplexityVisitor()
    visitor.visit(node)
    return {"cyclomatic_complexity": visitor.complexity}
