import ast
import pytest
from pathlib import Path

# Define the path to the cli_args.py file
CLI_ARGS_PATH = Path("src/hfais/cli_args.py")

# Helper function to extract all function names from cli_args.py
def get_cli_args_functions():
    with CLI_ARGS_PATH.open("r") as f:
        tree = ast.parse(f.read())
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

# Test to ensure all functions in cli_args.py are valid and follow naming conventions
def test_cli_args_functions_exist():
    cli_args_functions = get_cli_args_functions()

    # Ensure there are no duplicate function names
    assert len(cli_args_functions) == len(set(cli_args_functions)), "Duplicate function names found in cli_args.py"

    # Ensure all function names are descriptive and follow naming conventions
    for func in cli_args_functions:
        assert func.startswith("add_"), f"Function '{func}' in cli_args.py does not follow naming conventions"

# Test to ensure cli_args.py does not contain unused imports
def test_cli_args_no_unused_imports():
    with CLI_ARGS_PATH.open("r") as f:
        tree = ast.parse(f.read())

    imports = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}

    unused_imports = imports - used_names
    assert not unused_imports, f"Unused imports found in cli_args.py: {unused_imports}"