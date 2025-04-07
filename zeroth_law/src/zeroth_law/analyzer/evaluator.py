"""Compliance evaluation utilities for the Zeroth Law analyzer.

This module provides functions to evaluate code compliance based on various metrics
and determine compliance levels.

# PURPOSE: Compliance evaluation for Zeroth Law.

## INTERFACES:
 - evaluate_compliance: Evaluate file compliance with Zeroth Law
 - determine_compliance_level: Determine compliance level from score

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
"""

import logging
from typing import Dict, Any, List
from zeroth_law.utils.config import load_config

logger = logging.getLogger(__name__)


def evaluate_compliance(metrics: Dict[str, Any], config: dict, is_update: bool = False) -> None:
    """Evaluate the compliance level of a Python file based on its metrics.

    This function analyzes various metrics and assigns penalties based on
    violations of Zeroth Law principles. It updates the metrics dictionary
    in place with compliance scores and levels.

    Args:
        metrics (Dict[str, Any]): Dictionary containing file metrics to evaluate.
            Must include keys for functions, executable_lines, and other metrics
            collected by analyze_file().
        config (dict): Configuration dictionary containing thresholds and weights
            for compliance evaluation. If empty, default values are used.
        is_update (bool): Whether this evaluation is part of an update operation.
            If True, footer penalties are not applied.

    Note:
        This function modifies the metrics dictionary in place, adding:
        - penalties: List of compliance violations
        - overall_score: Numerical compliance score (0-100)
        - compliance_level: String indicating compliance level

    Examples:
        >>> metrics = {"functions": [], "executable_lines": 50, "penalties": []}
        >>> evaluate_compliance(metrics, {})
        >>> print(metrics["compliance_level"])
        'Excellent'
    """
    score = 100
    metrics["penalties"] = []  # Clear any existing penalties
    penalties = metrics["penalties"]

    # Retrieve configuration values, using defaults if not provided
    max_executable_lines = config.get("max_executable_lines")
    max_function_lines = config.get("max_function_lines")
    max_cyclomatic_complexity = config.get("max_cyclomatic_complexity")
    max_parameters = config.get("max_parameters")
    max_locals = config.get("max_locals")
    max_line_length = config.get("max_line_length")
    missing_header_penalty = config.get("missing_header_penalty")
    missing_footer_penalty = config.get("missing_footer_penalty")
    missing_docstring_penalty = config.get("missing_docstring_penalty")

    if metrics["executable_lines"] > max_executable_lines:
        deduction = min(50, metrics["executable_lines"] - max_executable_lines) // 5
        score -= deduction
        penalties.append({"reason": f"Exceeded max_executable_lines ({metrics['executable_lines']}/{max_executable_lines})", "deduction": deduction})

    if metrics["header_footer_status"] == "missing_header":
        score -= missing_header_penalty
        penalties.append({"reason": "Missing header", "deduction": missing_header_penalty})
    elif metrics["header_footer_status"] == "missing_footer" and not is_update:
        score -= missing_footer_penalty
        penalties.append({"reason": "Missing footer", "deduction": missing_footer_penalty})
    elif metrics["header_footer_status"] == "missing_both":
        score -= missing_header_penalty
        if not is_update:
            score -= missing_footer_penalty
        penalties.append(
            {
                "reason": "Missing header and footer",
                "deduction": missing_header_penalty + (missing_footer_penalty if not is_update else 0),
            }
        )

    function_deductions = 0
    for func in metrics["functions"]:
        if func["lines"] > max_function_lines:
            function_deductions += 5
            penalties.append(
                {"reason": f"Function {func['name']} exceeds max_function_lines ({func['lines']}/{max_function_lines})", "deduction": 5}
            )
        if func["cyclomatic_complexity"] > max_cyclomatic_complexity:
            function_deductions += 5
            penalties.append(
                {
                    "reason": f"Function {func['name']} exceeds max_cyclomatic_complexity ({func['cyclomatic_complexity']}/{max_cyclomatic_complexity})",
                    "deduction": 5,
                }
            )
        if func["parameter_count"] > max_parameters:
            function_deductions += 5
            penalties.append(
                {
                    "reason": f"Function {func['name']} exceeds max_parameters ({func['parameter_count']}/{max_parameters})",
                    "deduction": 5,
                }
            )
        if not func["has_docstring"]:
            function_deductions += missing_docstring_penalty
            penalties.append(
                {
                    "reason": f"Function {func['name']} is missing docstring",
                    "deduction": missing_docstring_penalty,
                }
            )

    score -= min(50, function_deductions)  # Max penalty for functions

    # Add imports penalty
    imports_score = metrics.get("imports_score", 100)
    if imports_score < 100:
        import_deduction = 100 - imports_score
        import_count = metrics.get("import_count", 0)
        score -= import_deduction
        penalties.append(
            {
                "reason": f"Too many imports ({import_count} imports)",
                "deduction": import_deduction,
            }
        )

    metrics["overall_score"] = max(0, score)
    metrics["compliance_level"] = determine_compliance_level(metrics["overall_score"])


def determine_compliance_level(score: int) -> str:
    """Convert a numerical compliance score to a descriptive level.

    Args:
        score (int): The numerical compliance score (0-100).

    Returns:
        str: One of "Needs Improvement", "Adequate", "Ok", "Good", or "Excellent" based on the score:
            - "Excellent": score == 100
            - "Good": 90 <= score < 100
            - "Ok": 75 <= score < 90
            - "Adequate": 50 <= score < 75
            - "Needs Improvement": score < 50

    Examples:
        >>> determine_compliance_level(100)
        'Excellent'
        >>> determine_compliance_level(95)
        'Good'
    """
    if score == 100:
        return "Excellent"
    elif score >= 90:
        return "Good"
    elif score >= 75:
        return "Ok"
    elif score >= 50:
        return "Adequate"
    else:
        return "Needs Improvement"


def evaluate_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate code quality metrics against configured thresholds.

    Args:
        metrics (Dict[str, Any]): Dictionary of metrics to evaluate

    Returns:
        Dict[str, Any]: Dictionary containing evaluation results
    """
    config = load_config()

    results = {}

    # Evaluate function size metrics
    if "function_size" in metrics:
        max_lines = config.get("max_function_lines")
        results["function_size"] = {"exceeds_max_lines": metrics["function_size"]["lines"] > max_lines, "max_lines": max_lines}

    # Evaluate cyclomatic complexity
    if "cyclomatic_complexity" in metrics:
        max_complexity = config.get("max_cyclomatic_complexity")
        results["cyclomatic_complexity"] = {
            "exceeds_max_complexity": metrics["cyclomatic_complexity"] > max_complexity,
            "max_complexity": max_complexity,
        }

    # Evaluate parameter count
    if "parameter_count" in metrics:
        max_parameters = config.get("max_parameters")
        results["parameter_count"] = {
            "exceeds_max_parameters": metrics["parameter_count"] > max_parameters,
            "max_parameters": max_parameters,
        }

    # Evaluate docstring coverage
    if "docstring_coverage" in metrics:
        missing_docstring_penalty = config.get("missing_docstring_penalty")
        results["docstring_coverage"] = {"penalty": missing_docstring_penalty if not metrics["docstring_coverage"] else 0}

    # Evaluate header/footer
    if "header_footer" in metrics:
        missing_header_penalty = config.get("missing_header_penalty")
        missing_footer_penalty = config.get("missing_footer_penalty")

        results["header_footer"] = {
            "header_penalty": missing_header_penalty if not metrics["header_footer"]["has_header"] else 0,
            "footer_penalty": missing_footer_penalty if not metrics["header_footer"]["has_footer"] else 0,
        }

    return results
