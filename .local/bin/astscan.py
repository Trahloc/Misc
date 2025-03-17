#!/usr/bin/env python3

"""
PURPOSE:
This script analyzes Python files within a specified directory, extracting information
about functions, classes, and module-level variables. It then outputs this information
to the console. This is designed to aid in code understanding and analysis.

INTERFACES:
  - analyze_directory(directory: str) -> None:
      Analyzes the Python files in the given directory and prints the extracted
      information to the console.
  - CodeAnalyzer.visit_FunctionDef(node: ast.FunctionDef) -> None:
      Callback function to handle function definitions during AST traversal.
  - CodeAnalyzer.visit_ClassDef(node: ast.ClassDef) -> None:
      Callback function to handle class definitions during AST traversal.
  - CodeAnalyzer.visit_Assign(node: ast.Assign) -> None:
      Callback function to handle assignment statements during AST traversal.

DEPENDENCIES:
  - ast: Provides functionality for parsing Python code into an Abstract Syntax Tree (AST).
  - os: Provides operating system-related functionality, such as walking through directories.
  - sys: Provides access to system-specific parameters and functions, such as command-line arguments.

ZEROTH LAW STATUS: 60% Complete
  - [x] Clear file purpose
  - [x] Interface documentation complete
  -Key Metrics applied
"""

import ast
import os
import sys

class CodeAnalyzer(ast.NodeVisitor):
    """
    This class traverses the Abstract Syntax Tree (AST) of a Python file
    and extracts information about functions, classes, and variables.
    """
    def __init__(self):
        """
        Initializes the CodeAnalyzer with empty lists to store function,
        class, and variable names.
        """
        self.functions = []  # Corrected initialization
        self.classes = []  # Corrected initialization
        self.variables = []  # Corrected initialization

    def visit_FunctionDef(self, node):
        """
        This method is called when a function definition is encountered in the AST.
        It appends the function name to the list of functions.
        """
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """
        This method is called when a class definition is encountered in the AST.
        It appends the class name to the list of classes.
        """
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        """
        This method is called when an assignment statement is encountered in the AST.
        It extracts the names of assigned variables and appends them to the list
        of variables.
        """
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variables.append(target.id)
        self.generic_visit(node)

def analyze_directory(directory: str) -> None:
    """
    Analyzes Python files in a directory.

    This function recursively traverses the given directory, identifies Python
    files, parses their code using the ast module, and extracts information
    about functions, classes, and module-level variables. The extracted
    information is then printed to the console.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as file_handle:
                        code = file_handle.read()
                    tree = ast.parse(code)
                    analyzer = CodeAnalyzer()
                    analyzer.visit(tree)

                    print(f"--- File: {file_path} ---")
                    print("Functions:", analyzer.functions)
                    print("Classes:", analyzer.classes)
                    print("Variables:", analyzer.variables)

                except SyntaxError as syntax_error:
                    print(f"SyntaxError in {file_path}: {syntax_error}")
                except Exception as general_exception:
                    print(f"Error analyzing {file_path}: {general_exception}")

if __name__ == "__main__":
    """
    This block is executed when the script is run directly.
    It handles command-line arguments and calls the analyze_directory function
    to analyze the specified directory.
    """
    if len(sys.argv) != 2:
        print("Usage: astscan <directory_path>")
    else:
        directory_to_analyze = sys.argv[1]
        analyze_directory(directory_to_analyze)

"""
ZEROTH LAW ASSESSMENT: 85% Complete (AI's subjective evaluation)
Improvements made:
  - Fixed syntax errors in variable initializations
  - Corrected usage message to match actual command name (astscan instead of analyze_dir)
  - Maintained comprehensive header and footer documentation
  - Ensured code follows semantic naming conventions

Next improvements needed:
  - Add better error handling for file access and permission issues
  - Implement metrics collection to provide quantitative analysis of code
  - Consider adding output formatting options (JSON, CSV) for further processing
"""
