"""
# PURPOSE: Core analysis functionality for Zeroth Law.

## INTERFACES:
 - analyze_directory: Analyze all files in a directory
 - analyze_file: Analyze a single file
 - analyze_regular_file: Analyze non-template files

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
 - ast
 - metrics modules
"""

import ast
import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from zeroth_law.analyzer.file_validator import check_file_validity, should_ignore, check_for_unrendered_templates
from zeroth_law.analyzer.template_handler import is_template_file, analyze_template_file
from zeroth_law.analyzer.evaluator import evaluate_compliance

from zeroth_law.metrics import (
    calculate_file_size_metrics,
    calculate_function_size_metrics,
    calculate_cyclomatic_complexity,
    calculate_docstring_coverage,
    calculate_naming_score,
    calculate_import_metrics,
)
from zeroth_law.utils.file_utils import find_header_footer, count_executable_lines
from zeroth_law.reporting.updater import update_file_footer
from zeroth_law.exceptions import (
    ZerothLawError,
    FileNotFoundError,
    NotPythonFileError,
    AnalysisError,
)
from zeroth_law.utils.config import load_config
from zeroth_law.utils.file_utils import get_file_lines, is_ignored_file
from zeroth_law.metrics.function_size import calculate_function_size_metrics
from zeroth_law.analyzer.evaluator import evaluate_metrics

logger = logging.getLogger(__name__)


def analyze_regular_file(file_path: str, source_code: str, config: dict) -> Dict[str, Any]:
    """Analyze a regular Python file with full metrics.

    Args:
        file_path (str): Path to the file to analyze.
        source_code (str): Content of the file.
        config (dict): Configuration dictionary.

    Returns:
        Dict[str, Any]: Full metrics for the file.

    Raises:
        AnalysisError: If there are issues parsing or analyzing the file.
    """
    tree = ast.parse(source_code)
    header, footer = find_header_footer(source_code)
    executable_lines = count_executable_lines(source_code)

    metrics: Dict[str, Any] = {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "header_footer_status": ("complete" if header and footer else ("missing_header" if not header else "missing_footer")),
        "executable_lines": executable_lines,
        **calculate_file_size_metrics(source_code, header, footer),
        "functions": [],
        "penalties": [],
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_metrics = {
                "name": node.name,
                **calculate_function_size_metrics(node, config),
                **calculate_cyclomatic_complexity(node),
                **calculate_docstring_coverage(node),
                **calculate_naming_score(node),
                "parameter_count": len(node.args.args),
            }
            metrics["functions"].append(function_metrics)

    metrics.update(calculate_import_metrics(tree))
    evaluate_compliance(metrics, config)
    return metrics


def analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a single file.

    Args:
        file_path (str): Path to the file to analyze

    Returns:
        Dict[str, Any]: Dictionary containing analysis results

    Raises:
        FileNotFoundError: If the file does not exist
        NotPythonFileError: If the file is not a Python file
        AnalysisError: If there are issues analyzing the file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.endswith(".py"):
        raise NotPythonFileError(f"Not a Python file: {file_path}")

    config = load_config()

    try:
        with open(file_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)

        # Find header and footer
        header, footer = find_header_footer(source)

        # Count executable lines
        executable_lines = count_executable_lines(source)

        results = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "functions": [],
            "metrics": {},
            "overall_score": 100,  # Start with perfect score
            "penalties": [],  # List to track penalties
            "compliance_level": "Excellent",  # Start with highest compliance level
            "executable_lines": executable_lines,
            "header_footer_status": ("complete" if header and footer else ("missing_header" if not header else "missing_footer")),
        }

        # Calculate file size metrics
        file_size_metrics = calculate_file_size_metrics(source, header, footer)
        results.update(file_size_metrics)

        # Analyze functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_metrics = calculate_function_size_metrics(node, config)
                docstring_metrics = calculate_docstring_coverage(node)
                parameter_count = len(node.args.args)
                
                if function_metrics["exceeds_max_lines"]:
                    results["overall_score"] -= 5
                    results["penalties"].append({"reason": f"Function {node.name} exceeds max_function_lines ({function_metrics['lines']}/{config['max_function_lines']})", "deduction": 5})
                
                if parameter_count > config["max_parameters"]:
                    results["overall_score"] -= 5
                    results["penalties"].append({"reason": f"Function {node.name} exceeds max_parameters ({parameter_count}/{config['max_parameters']})", "deduction": 5})
                
                if not docstring_metrics["has_docstring"]:
                    results["overall_score"] -= config["missing_docstring_penalty"]
                    results["penalties"].append({"reason": f"Function {node.name} is missing docstring", "deduction": config["missing_docstring_penalty"]})
                
                results["functions"].append({
                    "name": node.name,
                    "metrics": {
                        **function_metrics,
                        **calculate_cyclomatic_complexity(node),
                        **docstring_metrics,
                        **calculate_naming_score(node),
                        "parameter_count": parameter_count
                    }
                })

        # Analyze file metrics
        file_metrics = {"function_size": {"lines": sum(f["metrics"].get("lines", 0) for f in results["functions"])}}
        results["metrics"] = evaluate_metrics(file_metrics)

        # Calculate import metrics
        import_metrics = calculate_import_metrics(tree)
        results.update(import_metrics)

        # Check for header and footer
        if not header:
            results["overall_score"] -= config["missing_header_penalty"]
            results["penalties"].append({"reason": "Missing header", "deduction": config["missing_header_penalty"]})
        if not footer:
            results["overall_score"] -= config["missing_footer_penalty"]
            results["penalties"].append({"reason": "Missing footer", "deduction": config["missing_footer_penalty"]})

        # Ensure score doesn't go below 0
        results["overall_score"] = max(0, results["overall_score"])

        # Update compliance level based on score
        if results["overall_score"] >= 90:
            results["compliance_level"] = "Excellent"
        elif results["overall_score"] >= 80:
            results["compliance_level"] = "Good"
        elif results["overall_score"] >= 70:
            results["compliance_level"] = "Fair"
        else:
            results["compliance_level"] = "Poor"

        return results

    except SyntaxError as e:
        raise AnalysisError(f"Syntax error in {file_path}: {str(e)}")
    except Exception as e:
        raise AnalysisError(f"Error analyzing {file_path}: {str(e)}")


def analyze_directory(directory: str, recursive: bool = False, summary: bool = False, config_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a directory.

    Args:
        directory (str): Path to the directory to analyze
        recursive (bool): Whether to analyze subdirectories
        summary (bool): Whether to generate a summary report
        config_path (Optional[str]): Path to configuration file

    Returns:
        Dict[str, Any]: Dictionary containing analysis results

    Raises:
        FileNotFoundError: If the directory does not exist
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

    config = load_config(config_path)

    results = {
        "files": [],
        "metrics": {
            "total_files": 0,
            "total_functions": 0,
            "total_lines": 0,
            "average_score": 0,
            "files_with_issues": 0,
            "common_issues": {},
        },
    }

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    logger.info(f"Analyzing file: {file_path}")
                    file_results = analyze_file(file_path)
                    results["files"].append({"path": file_path, "results": file_results})

                    # Update metrics
                    results["metrics"]["total_files"] += 1
                    results["metrics"]["total_functions"] += len(file_results["functions"])
                    results["metrics"]["total_lines"] += sum(f["metrics"].get("lines", 0) for f in file_results["functions"])
                    results["metrics"]["average_score"] += file_results["overall_score"]

                    if file_results["penalties"]:
                        results["metrics"]["files_with_issues"] += 1
                        for penalty in file_results["penalties"]:
                            reason = penalty["reason"]
                            if reason not in results["metrics"]["common_issues"]:
                                results["metrics"]["common_issues"][reason] = 0
                            results["metrics"]["common_issues"][reason] += 1

                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {e}")

        if not recursive:
            break

    # Calculate average score
    if results["metrics"]["total_files"] > 0:
        results["metrics"]["average_score"] /= results["metrics"]["total_files"]

    return results
