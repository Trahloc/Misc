"""
# PURPOSE: Audit configuration usage in the codebase.

## INTERFACES:
  - find_hardcoded_configs(file_path: str) -> List[Tuple[int, str, Any]]: Find hardcoded configuration values
  - check_config_imports(file_path: str) -> bool: Check if file properly imports config.py
  - audit_config_usage(root_dir: str) -> Dict[str, Any]: Audit configuration usage in codebase

## DEPENDENCIES:
   - os
   - ast
   - typing
   - zeroth_law.utils.config
"""

import os
import ast
from typing import List, Tuple, Dict, Any
from zeroth_law.utils.config import load_config


def find_hardcoded_configs(file_path: str) -> List[Tuple[int, str, Any]]:
    """Find hardcoded configuration values in a file.

    Args:
        file_path (str): Path to the file to analyze

    Returns:
        List[Tuple[int, str, Any]]: List of tuples containing (line_number, config_key, value)
    """
    config = load_config()
    config_keys = list(config.keys())

    hardcoded_configs = []

    try:
        with open(file_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                value = node.value
                if isinstance(value, str) and value in config_keys:
                    hardcoded_configs.append((node.lineno, value, value))
            elif isinstance(node, ast.Name) and node.id in config_keys:
                hardcoded_configs.append((node.lineno, node.id, node.id))
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")

    return hardcoded_configs


def check_config_imports(file_path: str) -> bool:
    """Check if a file properly imports config.py.

    Args:
        file_path (str): Path to the file to check

    Returns:
        bool: True if file imports config.py, False otherwise
    """
    try:
        with open(file_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name == "zeroth_law.utils.config":
                        return True
            elif isinstance(node, ast.ImportFrom):
                if node.module == "zeroth_law.utils.config":
                    return True
    except Exception as e:
        print(f"Error checking imports in {file_path}: {e}")

    return False


def audit_config_usage(root_dir: str) -> Dict[str, Any]:
    """Audit configuration usage in the codebase.

    Args:
        root_dir (str): Root directory to start audit from

    Returns:
        Dict[str, Any]: Dictionary containing audit results
    """
    results = {"files_with_hardcoded_configs": {}, "files_missing_config_import": [], "files_using_config_correctly": []}

    for root, _, files in os.walk(root_dir):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)

            # Find hardcoded configs
            hardcoded_configs = find_hardcoded_configs(file_path)
            if hardcoded_configs:
                results["files_with_hardcoded_configs"][file_path] = hardcoded_configs

            # Check config imports
            has_config_import = check_config_imports(file_path)
            if has_config_import:
                results["files_using_config_correctly"].append(file_path)
            else:
                results["files_missing_config_import"].append(file_path)

    return results


def print_audit_report(results: Dict[str, Any]) -> None:
    """Print the audit report.

    Args:
        results (Dict[str, Any]): Audit results from audit_config_usage
    """
    print("\n=== Configuration Usage Audit Report ===\n")

    # Print files with hardcoded configs
    print("Files with hardcoded configuration values:\n")
    for file_path, configs in results["files_with_hardcoded_configs"].items():
        print(f"{file_path}:")
        for line_num, key, value in configs:
            print(f"  Line {line_num}: Found '{key}' with value '{value}'")
        print()

    # Print files missing config import
    print("Files missing config.py import:")
    for file_path in results["files_missing_config_import"]:
        print(f"  {file_path}")
    print()

    # Print summary
    print("Summary:")
    print(f"  Files with hardcoded configs: {len(results['files_with_hardcoded_configs'])}")
    print(f"  Files missing config import: {len(results['files_missing_config_import'])}")
    print(f"  Files using config correctly: {len(results['files_using_config_correctly'])}")


if __name__ == "__main__":
    # Get the root directory of the project
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Run the audit
    results = audit_config_usage(root_dir)

    # Print the report
    print_audit_report(results)
