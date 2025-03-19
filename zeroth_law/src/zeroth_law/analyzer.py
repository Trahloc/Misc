# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/analyzer.py (CORRECTED)
"""
# PURPOSE: Orchestrate the analysis of Python files for Zeroth Law compliance.

## INTERFACES:
  - analyze_file(file_path: str, update: bool = False, config: dict = None) -> dict: Analyze a single file.
  - analyze_directory(dir_path: str, recursive: bool = False, update: bool = False, config: dict = None) -> list: Analyze a directory.

## DEPENDENCIES:
 - zeroth_law.metrics: For calculating individual metrics.
 - zeroth_law.reporting: For generating reports.
 - zeroth_law.utils: Utility functions.
 - zeroth_law.exceptions: Custom exceptions.
 - logging
 - datetime #Import correctly
"""
import ast
import os
import shutil
import tempfile
from typing import Dict, List, Any
import logging
from datetime import datetime #Import correctly
import re

from zeroth_law.metrics import (
    calculate_file_size_metrics,
    calculate_function_size_metrics,
    calculate_cyclomatic_complexity,
    calculate_docstring_coverage,
    calculate_naming_score,
    calculate_import_metrics
)
from zeroth_law.reporting import generate_report, generate_summary_report
from zeroth_law.utils import find_header_footer, count_executable_lines, replace_footer
from zeroth_law.exceptions import ZerothLawError, FileNotFoundError, NotPythonFileError, AnalysisError, ConfigError

logger = logging.getLogger(__name__)

def analyze_file(file_path: str, update: bool = False, config: dict = None) -> Dict[str, Any]:
    """Analyzes a single Python file for Zeroth Law compliance.

    Args:
        file_path: The path to the Python file.
        update: Whether to update the file's footer.
        config: Configuration dictionary.

    Returns:
        A dictionary containing the analysis metrics.

    Raises:
        FileNotFoundError: If the file does not exist.
        NotPythonFileError: If the file is not a Python file.
        AnalysisError: If any error occurs during analysis.
    """
    logger.info(f"Analyzing file: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.endswith(".py"):
        logger.warning(f"Skipping non-Python file: {file_path}")
        raise NotPythonFileError(f"Not a Python file: {file_path}")

    # Check if this is a template file
    normalized_path = os.path.normpath(file_path)
    is_template = (
        "cookiecutter-template" in normalized_path or
        any(part.startswith("{{") and part.endswith("}}") for part in normalized_path.split(os.sep)) or
        os.path.basename(file_path).startswith("fix_cookiecutter") or
        os.path.basename(file_path).startswith("convert_templates_to_cookiecutter")
    )

    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    if config is None:
        config = {}

    try:
        # For template files, only do basic analysis without AST parsing
        if is_template:
            logger.info(f"Processing template file: {file_path}")
            header, footer = find_header_footer(source_code)
            executable_lines = count_executable_lines(source_code)

            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "is_template": True,
                "header_footer_status": "complete" if header and footer else ("missing_header" if not header else "missing_footer"),
                "executable_lines": executable_lines,
                "overall_score": "N/A - Template File",
                "compliance_level": "Template File",
                "functions": [],
                "penalties": []
            }

        # Check for unrendered templates in non-template files, but skip analyzer.py
        if not is_template and not file_path.endswith("analyzer.py") and re.search(r"\{\{.*?\}\}", source_code):
            logger.warning(f"Skipping unrendered template file: {file_path}")
            raise AnalysisError(f"Unrendered template detected in file: {file_path}")

        # Regular analysis for non-template files
        tree = ast.parse(source_code)
        header, footer = find_header_footer(source_code)
        executable_lines = count_executable_lines(source_code)

        metrics: Dict[str, Any] = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "header_footer_status": "complete" if header and footer else ("missing_header" if not header else "missing_footer"),
            "executable_lines": executable_lines,
            **calculate_file_size_metrics(source_code, header, footer),
            "functions": [],
            "penalties": [],
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_metrics = {
                    "name": node.name,
                    **calculate_function_size_metrics(node),
                    **calculate_cyclomatic_complexity(node),
                    **calculate_docstring_coverage(node),
                    **calculate_naming_score(node),
                    "parameter_count": len(node.args.args),
                }
                metrics["functions"].append(function_metrics)

        metrics.update(calculate_import_metrics(tree))
        evaluate_compliance(metrics, config)

        if update:
            update_file_footer(file_path, metrics)

        return metrics

    except SyntaxError as e:
        raise AnalysisError(f"Syntax error in file: {file_path}: {e}") from e
    except Exception as e:
        raise AnalysisError(f"Error analyzing file: {file_path}: {e}") from e


def analyze_directory(dir_path: str, recursive: bool = False, update: bool = False, config: dict = None) -> List[Dict[str, Any]]:
    """Analyzes all Python files in a directory.

    Args:
        dir_path: Path to the directory.
        recursive: Analyze subdirectories.
        update: Update file footers.
        config: Configuration dictionary.

    Returns:
        List of analysis metrics for each file.

    Raises:
        FileNotFoundError: If the directory does not exist.
        AnalysisError: If any error occurs during analysis.
    """
    logger.info(f"Analyzing directory: {dir_path}")

    if not os.path.exists(dir_path):
        raise FileNotFoundError(f"Directory not found: {dir_path}")
    if not os.path.isdir(dir_path):
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    all_metrics = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    metrics = analyze_file(file_path, update=update, config=config)
                    all_metrics.append(metrics)
                except ZerothLawError as e:  # Catch any ZerothLawError
                    logger.error(str(e))  # Log the specific error
                    all_metrics.append({"file_path": file_path, "error": str(e)})
        if not recursive:
            break

    return all_metrics


def evaluate_compliance(metrics: Dict[str, Any], config: dict) -> None:
    """Calculates compliance scores."""
    score = 100
    penalties = metrics["penalties"]

    # Retrieve configuration values, using defaults if not provided
    max_executable_lines = config.get("max_executable_lines", 300)
    max_function_lines = config.get("max_function_lines", 30)
    max_cyclomatic_complexity = config.get("max_cyclomatic_complexity", 8)
    max_parameters = config.get("max_parameters", 4)
    missing_header_penalty = config.get("missing_header_penalty", 20)
    missing_footer_penalty = config.get("missing_footer_penalty", 10)
    missing_docstring_penalty = config.get("missing_docstring_penalty", 2)

    if metrics["executable_lines"] > max_executable_lines:
        deduction = (min(50, metrics["executable_lines"] - max_executable_lines) // 5)
        score -= deduction
        penalties.append({"reason": "Exceeded max executable lines", "deduction": deduction})

    if metrics["header_footer_status"] == "missing_header":
        score -= missing_header_penalty
        penalties.append({"reason": "Missing header", "deduction": missing_header_penalty})
    elif metrics["header_footer_status"] == "missing_footer":
        score -= missing_footer_penalty
        penalties.append({"reason": "Missing footer", "deduction": missing_footer_penalty})
    elif metrics["header_footer_status"] == "missing_both":
        score -= (missing_header_penalty + missing_footer_penalty)
        penalties.append({"reason": "Missing header and footer", "deduction": missing_header_penalty + missing_footer_penalty})

    function_deductions = 0
    for func in metrics["functions"]:
        if func["lines"] > max_function_lines:
            function_deductions += 5
            penalties.append({"reason": f"Function {func['name']} exceeds max lines", "deduction": 5})
        if func["cyclomatic_complexity"] > max_cyclomatic_complexity:
            function_deductions += 5
            penalties.append({"reason": f"Function {func['name']} exceeds max cyclomatic complexity", "deduction": 5})
        if func["parameter_count"] > max_parameters:
            function_deductions += 5
            penalties.append({"reason": f"Function {func['name']} exceeds max parameters", "deduction": 5})
        if not func["has_docstring"]:
            function_deductions += missing_docstring_penalty
            penalties.append({"reason": f"Function {func['name']} is missing docstring", "deduction": missing_docstring_penalty})


    score -= min(50, function_deductions)  # Max penalty for functions
    score -= (100 - metrics.get("imports_score", 100))

    metrics["overall_score"] = max(0, score)
    metrics["compliance_level"] = determine_compliance_level(metrics["overall_score"])


def determine_compliance_level(score: int) -> str:
    """Determines the compliance level."""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 50:
        return "Adequate"
    else:
        return "Needs Improvement"


def update_file_footer(file_path: str, metrics: Dict[str, Any]) -> None:
    """Updates the file footer with compliance information."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as tmp_file:
            with open(file_path, "r", encoding="utf-8") as original_file:
                content = original_file.read()

            header, old_footer = find_header_footer(content)
            new_footer = generate_footer(metrics)
            updated_content = replace_footer(content, new_footer)

            tmp_file.write(updated_content)

        shutil.move(tmp_file.name, file_path)
        logger.info(f"Updated footer for {file_path}")

    except OSError as e:
        logger.error(f"Error updating footer for {file_path}: {e}")
        if os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)


def generate_footer(metrics: Dict[str, Any]) -> str:
    """Generates the Zeroth Law footer content."""
    footer = f'''"""
## KNOWN ERRORS: [List with severity.]

## IMPROVEMENTS: [This session's improvements.]

## FUTURE TODOs: [For next session. Consider further decomposition.]

## ZEROTH LAW COMPLIANCE:
    - Overall Score: {metrics["overall_score"]}/100 - {metrics["compliance_level"]}
    - Penalties:'''

    for penalty in metrics["penalties"]:
        footer += f'''\n      - {penalty["reason"]}: -{penalty["deduction"]}'''

    footer += f'''\n    - Analysis Timestamp: {datetime.now().isoformat()}
"""'''
    return footer