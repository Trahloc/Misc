# New file: src/zeroth_law/analysis_runner.py
"""
Handles running analysis on files and formatting/reporting violations.
"""

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, List, Tuple, Set

log = logging.getLogger(__name__)


# --- Placeholder Analyzer Function ---
def run_all_checks(file_path: Path, **kwargs: Any) -> dict[str, list[Any]]:
    """Placeholder function to run all configured checks. TODO: Implement actual checks."""
    log.debug(f"Running placeholder analysis on: {file_path}")
    # In the future, this function would:
    # 1. Load specific check functions (header, footer, complexity, etc.)
    # 2. Call each enabled check function on the file_path.
    # 3. Aggregate violations from all checks.
    # 4. Return the aggregated violations dictionary.
    return {}  # Return empty dict for now (no violations)


# --- Core Analysis Logic ---
def analyze_files(
    files: list[Path], config: dict[str, Any], analyzer_func: Callable
) -> tuple[dict[Path, dict[str, list]], dict[str, int]]:
    """
    Analyzes a list of files using the provided analyzer function and configuration.

    Args:
        files: A list of Path objects representing the files to analyze.
        config: A dictionary containing configuration for the analyzer.
        analyzer_func: The function to use for analyzing each file.

    Returns:
        A tuple containing:
        - A dictionary mapping file paths to their violation results.
        - A dictionary containing statistics about the analysis run.
    """
    violations_by_file: dict[Path, dict[str, list]] = {}
    unique_files: list[Path] = sorted(list(set(files)))  # Ensure uniqueness and order
    total_files: int = len(unique_files)

    stats = {
        "files_analyzed": 0,  # Total files attempted (will match total_files if no errors)
        "files_with_violations": 0,  # Files with actual violations reported by analyzer
        "compliant_files": 0,  # Files with no violations reported
        "files_with_errors": 0,  # Files that caused an error during analysis
    }

    log.info(f"Starting analysis of {total_files} unique files.")  # Log total unique files

    for i, file_path in enumerate(unique_files):  # Iterate over unique files
        log.debug(f"Analyzing file {i + 1}/{total_files}: {file_path}")  # Use total_files
        error_occurred = False
        violations = {}  # Initialize violations for the current file scope
        error_msg = ""  # Initialize error message

        try:
            # Ensure file exists before attempting analysis
            if not file_path.is_file():
                raise FileNotFoundError(f"File not found: {file_path}")

            violations = analyzer_func(file_path, **config.get("analyzer_settings", {}))

        except FileNotFoundError as e:
            error_occurred = True
            error_msg = str(e)
            log.error(error_msg)  # Log the specific error
        except SyntaxError as e:
            error_occurred = True
            error_msg = f"Syntax error: {e}"
            log.error(f"Syntax error analyzing {file_path}: {e}")
        except Exception as e:
            # Catch unexpected errors during analysis
            error_occurred = True
            error_msg = f"Unexpected error analyzing {file_path}: {type(e).__name__}: {e}"
            log.exception(error_msg)  # Use logger.exception to include stack trace
        finally:
            # This ensures files_analyzed is always incremented
            stats["files_analyzed"] += 1

        # Process results and update stats *after* try-except-finally
        if error_occurred:
            violations_by_file[file_path] = {"error": [error_msg]}
            stats["files_with_errors"] += 1
        elif violations:  # Check the result from the try block if no error occurred
            violations_by_file[file_path] = violations
            stats["files_with_violations"] += 1
        else:  # No error and no violations
            stats["compliant_files"] += 1

    log.info(f"Analysis complete. Stats: {stats}")
    return violations_by_file, stats


def format_violations_as_json(
    violations_by_file: dict[Path, dict[str, list]],
    total_files: int,
    files_with_violations: int,
    compliant_files: int,
) -> dict[str, Any]:
    """Format violations data as a JSON-serializable dictionary.

    Args:
    ----
        violations_by_file: Dictionary mapping file paths to violation dictionaries.
        total_files: Total number of files analyzed.
        files_with_violations: Number of files with violations.
        compliant_files: Number of compliant files.

    Returns:
    -------
        A JSON-serializable dictionary containing formatted violations data.

    """
    json_output = {
        "summary": {
            "total_files": total_files,
            "files_with_violations": files_with_violations,
            "compliant_files": compliant_files,
        },
        "violations": {},
    }

    # Convert Path objects to strings and tuples to lists for JSON serialization
    for file_path, violations in violations_by_file.items():
        file_path_str = str(file_path)
        json_output["violations"][file_path_str] = {}

        for category, issues in violations.items():
            json_output["violations"][file_path_str][category] = []

            for issue in issues:
                if isinstance(issue, tuple):
                    # Convert tuple to list for JSON serialization
                    json_output["violations"][file_path_str][category].append(list(issue))
                else:
                    json_output["violations"][file_path_str][category].append(issue)

    return json_output


def log_violations_as_text(
    violations_by_file: dict[Path, dict[str, list]],
) -> None:
    """Log violations as formatted text using the logger.

    Args:
    ----
        violations_by_file: Dictionary mapping file paths to violation dictionaries.

    """
    log.warning("\nDetailed Violations:")
    for file_path, violations in sorted(violations_by_file.items()):
        rel_path = file_path
        try:
            # Attempt to get relative path, fallback to original if error
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            pass  # Keep original absolute path
        log.warning("\nFile: %s", rel_path)
        for category, issues in sorted(violations.items()):
            log.warning("  %s:", category.capitalize())
            if not issues:
                log.warning("    (No specific issues listed for this category)")
                continue
            for issue in issues:
                # Format issue nicely (handle tuples vs strings)
                if isinstance(issue, tuple):
                    issue_str = ", ".join(map(str, issue))
                    log.warning("    - (%s)", issue_str)
                elif isinstance(issue, str):
                    log.warning("    - %s", issue)
                else:
                    log.warning("    - %s", str(issue))
