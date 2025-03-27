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
 - datetime
 - fnmatch
"""
import ast
import os
import shutil
import tempfile
from typing import Dict, List, Any
import logging
from datetime import datetime
import re
import fnmatch

from zeroth_law.metrics import (
    calculate_file_size_metrics,
    calculate_function_size_metrics,
    calculate_cyclomatic_complexity,
    calculate_docstring_coverage,
    calculate_naming_score,
    calculate_import_metrics,
)
from zeroth_law.utils import find_header_footer, count_executable_lines, replace_footer
from zeroth_law.exceptions import (
    ZerothLawError,
    FileNotFoundError,
    NotPythonFileError,
    AnalysisError,
)

logger = logging.getLogger(__name__)


def should_ignore(file_path: str, base_path: str, ignore_patterns: List[str]) -> bool:
    """Check if a file should be ignored based on the ignore patterns.

    This function determines whether a file should be excluded from analysis based on
    a list of glob patterns. It normalizes both the file path and patterns to ensure
    consistent matching across different operating systems.

    Args:
        file_path (str): The absolute path of the file to check.
        base_path (str): The base directory path to make paths relative to.
        ignore_patterns (List[str]): List of glob patterns to match against.
            Patterns should use forward slashes and can include wildcards.

    Returns:
        bool: True if the file should be ignored, False otherwise.

    Examples:
        >>> should_ignore("/path/to/file.py", "/path", ["*.pyc", "test/*"])
        False
        >>> should_ignore("/path/to/test/file.py", "/path", ["test/*"])
        True
    """
    try:
        # Get path relative to the base directory
        rel_path = os.path.relpath(file_path, base_path)
        # Convert path to use forward slashes for consistent matching
        normalized_path = rel_path.replace(os.sep, "/")

        # Add a leading ./ to match patterns that start with . like .old/
        if not normalized_path.startswith("./"):
            normalized_path = "./" + normalized_path

        for pattern in ignore_patterns:
            # Normalize pattern to use forward slashes
            norm_pattern = pattern.replace(os.sep, "/")
            # Add ./ prefix to pattern if it starts with a dot directory
            if norm_pattern.startswith(".") and not norm_pattern.startswith("./"):
                norm_pattern = "./" + norm_pattern

            if fnmatch.fnmatch(normalized_path, norm_pattern):
                logger.debug(
                    f"Path '{normalized_path}' matched pattern '{norm_pattern}'"
                )
                return True
        return False
    except ValueError:
        # Handle case where file_path is on different drive than base_path (Windows)
        return False


def analyze_file(
    file_path: str, update: bool = False, config: dict = None
) -> Dict[str, Any]:
    """Analyze a single Python file for Zeroth Law compliance.

    This function performs a comprehensive analysis of a Python file, checking various
    metrics including code size, complexity, docstring coverage, naming conventions,
    and import usage. For template files, it performs a simplified analysis.

    Args:
        file_path (str): Path to the Python file to analyze.
        update (bool, optional): Whether to update the file's footer with analysis results.
            Defaults to False.
        config (dict, optional): Configuration dictionary containing analysis thresholds
            and settings. If None, default values are used.

    Returns:
        Dict[str, Any]: A dictionary containing analysis metrics including:
            - file_path: Path to the analyzed file
            - file_name: Base name of the file
            - is_template: Whether the file is a template
            - header_footer_status: Status of header and footer ("complete", "missing_header", or "missing_footer")
            - executable_lines: Number of executable lines
            - functions: List of function-level metrics
            - penalties: List of compliance penalties
            - overall_score: Numerical compliance score
            - compliance_level: String indicating compliance level

    Raises:
        FileNotFoundError: If the specified file does not exist.
        NotPythonFileError: If the file is not a Python file (.py extension).
        AnalysisError: If an error occurs during analysis (e.g., syntax error).

    Examples:
        >>> metrics = analyze_file("example.py")
        >>> print(metrics["compliance_level"])
        'High'
    """
    logger.info(f"Analyzing file: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.endswith(".py"):
        logger.warning(f"Skipping non-Python file: {file_path}")
        raise NotPythonFileError(f"Not a Python file: {file_path}")

    # Check if this is a template file
    normalized_path = os.path.normpath(file_path)
    templates_directory = os.path.normpath("templates")  # Update to just "templates"
    is_template = normalized_path.startswith(
        templates_directory
    )  # Only consider files in the templates directory

    # Exclude specific files from being flagged as templates
    excluded_files = ["template_converter.py", "test_coverage.py", "conftest.py"]
    if os.path.basename(file_path) in excluded_files:
        is_template = False

    # Debug logging to verify exclusion logic
    logger.debug(f"Analyzing file: {file_path}, is_template: {is_template}")

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
                "header_footer_status": (
                    "complete"
                    if header and footer
                    else ("missing_header" if not header else "missing_footer")
                ),
                "executable_lines": executable_lines,
                "overall_score": "N/A - Template File",
                "compliance_level": "Template File",
                "functions": [],
                "penalties": [],
            }

        # Allow specific files to contain unrendered template variables without raising an error
        if os.path.basename(file_path) in excluded_files:
            logger.debug(f"Allowing unrendered templates in file: {file_path}")
        elif (
            not is_template
            and not file_path.endswith("analyzer.py")
            and re.search(r"\{\{.*?\}\}", source_code)
        ):
            logger.warning(f"Skipping unrendered template file: {file_path}")
            raise AnalysisError(f"Unrendered template detected in file: {file_path}")

        # Regular analysis for non-template files
        tree = ast.parse(source_code)
        header, footer = find_header_footer(source_code)
        executable_lines = count_executable_lines(source_code)

        metrics: Dict[str, Any] = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "header_footer_status": (
                "complete"
                if header and footer
                else ("missing_header" if not header else "missing_footer")
            ),
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


def analyze_directory(
    dir_path: str, recursive: bool = False, update: bool = False, config: dict = None
) -> List[Dict[str, Any]]:
    """Analyze all Python files in a directory for Zeroth Law compliance.

    This function walks through a directory and analyzes all Python files found.
    It can optionally recurse into subdirectories and update file footers with
    analysis results.

    Args:
        dir_path (str): Path to the directory to analyze.
        recursive (bool, optional): Whether to analyze files in subdirectories.
            Defaults to False.
        update (bool, optional): Whether to update file footers with analysis results.
            Defaults to False.
        config (dict, optional): Configuration dictionary containing analysis thresholds
            and settings. If None, default values are used.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing metrics for one file.
            See analyze_file() for details of the metrics dictionary structure.

    Raises:
        NotADirectoryError: If dir_path is not a directory.
        FileNotFoundError: If dir_path does not exist.

    Examples:
        >>> metrics = analyze_directory("src/", recursive=True)
        >>> print(len(metrics))  # Number of files analyzed
        5
    """
    logger.info(f"Analyzing directory: {dir_path}")

    if not os.path.exists(dir_path):
        raise FileNotFoundError(f"Directory not found: {dir_path}")
    if not os.path.isdir(dir_path):
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    if config is None:
        config = {}

    ignore_patterns = config.get("ignore_patterns", [])
    logger.debug(f"Loaded ignore patterns: {ignore_patterns}")
    all_metrics = []

    # Convert dir_path to absolute path for consistent relative path calculation
    abs_dir_path = os.path.abspath(dir_path)

    for root, _, files in os.walk(dir_path):
        # Skip the directory if it matches any ignore pattern
        if should_ignore(root, abs_dir_path, ignore_patterns):
            logger.debug(f"Ignoring directory: {os.path.relpath(root, abs_dir_path)}")
            continue

        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)

            # Skip the file if it matches any ignore pattern
            if should_ignore(file_path, abs_dir_path, ignore_patterns):
                logger.debug(
                    f"Ignoring file: {os.path.relpath(file_path, abs_dir_path)}"
                )
                continue

            try:
                metrics = analyze_file(file_path, update=update, config=config)
                all_metrics.append(metrics)
            except ZerothLawError as e:
                logger.error(str(e))
                all_metrics.append({"file_path": file_path, "error": str(e)})

        if not recursive:
            break

    return all_metrics


def evaluate_compliance(metrics: Dict[str, Any], config: dict) -> None:
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

    Note:
        This function modifies the metrics dictionary in place, adding:
        - penalties: List of compliance violations
        - overall_score: Numerical compliance score (0-100)
        - compliance_level: String indicating compliance level

    Examples:
        >>> metrics = {"functions": [], "executable_lines": 50}
        >>> evaluate_compliance(metrics, {})
        >>> print(metrics["compliance_level"])
        'High'
    """
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
        deduction = min(50, metrics["executable_lines"] - max_executable_lines) // 5
        score -= deduction
        penalties.append(
            {"reason": "Exceeded max executable lines", "deduction": deduction}
        )

    if metrics["header_footer_status"] == "missing_header":
        score -= missing_header_penalty
        penalties.append(
            {"reason": "Missing header", "deduction": missing_header_penalty}
        )
    elif metrics["header_footer_status"] == "missing_footer":
        score -= missing_footer_penalty
        penalties.append(
            {"reason": "Missing footer", "deduction": missing_footer_penalty}
        )
    elif metrics["header_footer_status"] == "missing_both":
        score -= missing_header_penalty + missing_footer_penalty
        penalties.append(
            {
                "reason": "Missing header and footer",
                "deduction": missing_header_penalty + missing_footer_penalty,
            }
        )

    function_deductions = 0
    for func in metrics["functions"]:
        if func["lines"] > max_function_lines:
            function_deductions += 5
            penalties.append(
                {"reason": f"Function {func['name']} exceeds max lines", "deduction": 5}
            )
        if func["cyclomatic_complexity"] > max_cyclomatic_complexity:
            function_deductions += 5
            penalties.append(
                {
                    "reason": f"Function {func['name']} exceeds max cyclomatic complexity",
                    "deduction": 5,
                }
            )
        if func["parameter_count"] > max_parameters:
            function_deductions += 5
            penalties.append(
                {
                    "reason": f"Function {func['name']} exceeds max parameters",
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
    score -= 100 - metrics.get("imports_score", 100)

    metrics["overall_score"] = max(0, score)
    metrics["compliance_level"] = determine_compliance_level(metrics["overall_score"])


def determine_compliance_level(score: int) -> str:
    """Convert a numerical compliance score to a descriptive level.

    Args:
        score (int): The numerical compliance score (0-100).

    Returns:
        str: One of "Critical", "Low", "Medium", or "High" based on the score:
            - "Critical": score < 60
            - "Low": 60 <= score < 75
            - "Medium": 75 <= score < 90
            - "High": score >= 90

    Examples:
        >>> determine_compliance_level(95)
        'High'
        >>> determine_compliance_level(50)
        'Critical'
    """
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 50:
        return "Adequate"
    else:
        return "Needs Improvement"


def update_file_footer(file_path: str, metrics: Dict[str, Any]) -> None:
    """Update a file's footer with new compliance metrics.

    This function generates a new footer containing compliance information
    and updates the file in place, preserving the original content and header.

    Args:
        file_path (str): Path to the file to update.
        metrics (Dict[str, Any]): Dictionary containing the metrics to include
            in the footer. Must include compliance_level and overall_score.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there are issues reading or writing the file.

    Note:
        This function creates a backup of the original file before making changes.
        If an error occurs during the update, the original file is restored.
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as tmp_file:
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
    """Generate a standardized footer containing compliance metrics.

    This function creates a formatted footer string containing compliance
    information and metrics from the analysis.

    Args:
        metrics (Dict[str, Any]): Dictionary containing metrics to include
            in the footer. Must include:
            - compliance_level: Overall compliance level
            - overall_score: Numerical compliance score
            - penalties: List of compliance violations

    Returns:
        str: A formatted footer string containing:
            - Current timestamp
            - Compliance level and score
            - List of penalties (if any)
            - Standard footer markers

    Examples:
        >>> metrics = {"compliance_level": "High", "overall_score": 95, "penalties": []}
        >>> footer = generate_footer(metrics)
        >>> "Compliance Level: High" in footer
        True
    """
    footer = f'''"""
## KNOWN ERRORS: [List with severity.]

## IMPROVEMENTS: [This session's improvements.]

## FUTURE TODOs: [For next session. Consider further decomposition.]

## ZEROTH LAW COMPLIANCE:
    - Overall Score: {metrics["overall_score"]}/100 - {metrics["compliance_level"]}
    - Penalties:'''

    for penalty in metrics["penalties"]:
        footer += f"""\n      - {penalty["reason"]}: -{penalty["deduction"]}"""

    footer += f'''\n    - Analysis Timestamp: {datetime.now().isoformat()}
"""'''
    return footer
