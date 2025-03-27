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
    """AST Visitor that calculates cyclomatic complexity of Python code.

    This visitor traverses an AST and counts decision points that increase
    the cyclomatic complexity of the code. The following constructs are counted:
    - If statements and expressions (including ternary operators)
    - For and While loops
    - With statements
    - Try/Except blocks (each except handler counts)
    - Boolean operations (each additional operand counts)
    - Assert statements

    The base complexity is 1, and each decision point adds 1 to the total.

    Attributes:
        complexity (int): The current cyclomatic complexity count.
    """

    def __init__(self):
        """Initialize the visitor with base complexity of 1."""
        self.complexity = 1

    def visit_If(self, node: ast.If):
        """Visit an if statement and increment complexity.

        Args:
            node (ast.If): The AST node representing an if statement.
        """
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp):
        """Visit a ternary operator and increment complexity.

        Args:
            node (ast.IfExp): The AST node representing a ternary operator.
        """
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        """Visit a for loop and increment complexity.

        Args:
            node (ast.For): The AST node representing a for loop.
        """
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        """Visit a while loop and increment complexity.

        Args:
            node (ast.While): The AST node representing a while loop.
        """
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        """Visit a with statement and increment complexity.

        Args:
            node (ast.With): The AST node representing a with statement.
        """
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        """Visit a try/except block and increment complexity for each handler.

        Args:
            node (ast.Try): The AST node representing a try/except block.
        """
        self.complexity += len(node.handlers)
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        """Visit a boolean operation and increment complexity for each additional operand.

        For example, 'a and b and c' has two additional operands beyond the first,
        so it adds 2 to the complexity.

        Args:
            node (ast.BoolOp): The AST node representing a boolean operation.
        """
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert):
        """Visit an assert statement and increment complexity.

        Args:
            node (ast.Assert): The AST node representing an assert statement.
        """
        self.complexity += 1
        self.generic_visit(node)


def calculate_cyclomatic_complexity(node: ast.FunctionDef) -> Dict[str, Any]:
    """Calculate the cyclomatic complexity of a function.

    This function analyzes the AST of a Python function and calculates its
    cyclomatic complexity, which is a measure of the function's complexity
    based on the number of decision points in the code.

    Args:
        node (ast.FunctionDef): The AST node representing the function to analyze.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - cyclomatic_complexity (int): The calculated complexity value.
                1 is the base complexity for a linear function.
                Higher values indicate more complex control flow.

    Examples:
        >>> import ast
        >>> tree = ast.parse("def example(): if x: return 1 else: return 2")
        >>> func_node = tree.body[0]
        >>> calculate_cyclomatic_complexity(func_node)
        {'cyclomatic_complexity': 2}  # Base 1 + 1 for the if statement
    """
    visitor = CyclomaticComplexityVisitor()
    visitor.visit(node)
    return {"cyclomatic_complexity": visitor.complexity}
