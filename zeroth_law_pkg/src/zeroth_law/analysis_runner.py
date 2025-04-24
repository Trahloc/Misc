# New file: src/zeroth_law/analysis_runner.py
"""
Handles running analysis on files and formatting/reporting violations.
"""

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, List, Tuple  # Corrected import for Dict, List, Tuple

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
) -> tuple[dict[Path, dict[str, list[Any]]], dict[str, int]]:
    """Analyzes multiple files for compliance using the provided analyzer function.

    Args:
    ----
        files: List of files to analyze.
        config: The loaded configuration.
        analyzer_func: Function to analyze each file.

    Returns:
    -------
        A tuple containing violations by file and statistics.

    """
    violations_by_file: dict[Path, dict[str, list[Any]]] = {}
    stats: dict[str, int] = {
        "files_analyzed": len(files),
        "files_with_violations": 0,
        "compliant_files": 0,
    }

    for file_path in files:
        try:
            violations = analyzer_func(file_path, **config.get("analyzer_settings", {}))
            if violations:
                violations_by_file[file_path] = violations
                stats["files_with_violations"] += 1
            else:
                stats["compliant_files"] += 1
        except FileNotFoundError:
            violations_by_file[file_path] = {"error": ["File not found during analysis"]}
            stats["files_with_violations"] += 1
        except SyntaxError as e:
            violations_by_file[file_path] = {"error": [f"SyntaxError: {e} during analysis"]}
            stats["files_with_violations"] += 1
        except Exception as e:
            log.exception(f"Unexpected error analyzing file {file_path}", exc_info=e)  # Improved logging
            violations_by_file[file_path] = {"error": [f"{e.__class__.__name__}: {e} during analysis"]}
            stats["files_with_violations"] += 1

    return violations_by_file, stats


def format_violations_as_json(
    violations_by_file: dict[Path, dict[str, list[Any]]],
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
    violations_by_file: dict[Path, dict[str, list[Any]]],
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
