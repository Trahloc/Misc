# FILE: src/zeroth_law/analyzer/python/analyzer.py
"""Main Python code analyzer for Zeroth Law compliance.

Orchestrates various checks like header, footer, complexity, docstrings, etc.
"""

import logging
from pathlib import Path

# Import analysis functions from submodules
from .complexity import ComplexityViolation, analyze_complexity
from .docstrings import DocstringViolation, analyze_docstrings
from .line_counts import LineCountViolation, analyze_line_counts
from .parameters import ParameterViolation, analyze_parameters
from .statements import StatementViolation, analyze_statements

# Keep header/footer checks here as they are simple file content checks
# (ast_utils are used internally by other analyzers)

log = logging.getLogger(__name__)

# Constants removed - should be passed in or loaded from config by caller
# EXPECTED_HEADER_LINES = 2 # Still needed internally?
# DEFAULT_MAX_COMPLEXITY = 10
# DEFAULT_MAX_PARAMS = 5
# DEFAULT_MAX_STATEMENTS = 50
# DEFAULT_MAX_EXECUTABLE_LINES = 100

# --- Header and Footer Checks ---


def check_header_compliance(file_path: str | Path) -> list[str]:
    """Check if a file starts with the required Zeroth Law header.

    Args:
    ----
        file_path: The path to the Python file.

    Returns:
    -------
        A list of error codes if non-compliant, empty list otherwise.
        Possible error codes: HEADER_MISSING_FILE_LINE, HEADER_MISSING_DOCSTRING_START,
                          FILE_NOT_FOUND, HEADER_CHECK_OS_ERROR, HEADER_CHECK_UNEXPECTED_ERROR.

    """
    errors: list[str] = []
    try:
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            # Read line 1, strip whitespace, check existence
            line1_raw = f.readline()
            if not line1_raw:
                errors.append("HEADER_MISSING_FILE_LINE")
                errors.append("HEADER_MISSING_DOCSTRING_START")
                return errors

            line1 = line1_raw.strip()
            if not line1.startswith("# FILE:"):
                errors.append("HEADER_MISSING_FILE_LINE")

            # Read line 2, strip whitespace, check existence
            line2_raw = f.readline()
            if not line2_raw:
                errors.append("HEADER_MISSING_DOCSTRING_START")
                return errors

            line2 = line2_raw.strip()
            if not line2.startswith('"""'):
                errors.append("HEADER_MISSING_DOCSTRING_START")

    except FileNotFoundError:
        errors.append("FILE_NOT_FOUND")
        log.warning(f"Header check failed: File not found {file_path}")
    except OSError as e:
        errors.append(f"HEADER_CHECK_OS_ERROR: {e}")
        log.error(f"Header check failed for {file_path}: {e}")
    except Exception as e:
        log.exception(f"Unexpected error during header check for {file_path}", exc_info=e)
        errors.append("HEADER_CHECK_UNEXPECTED_ERROR")

    return errors


def check_footer_compliance(file_path: str | Path) -> list[str]:
    """Check if a file contains the required Zeroth Law footer marker.

    Args:
    ----
        file_path: The path to the Python file.

    Returns:
    -------
        A list containing 'FOOTER_MISSING' if not found, empty list otherwise.
        Possible error codes: FOOTER_MISSING, FILE_NOT_FOUND, FOOTER_CHECK_OS_ERROR, FOOTER_CHECK_UNEXPECTED_ERROR.

    """
    errors: list[str] = []
    required_footer_marker = "# <<< ZEROTH LAW FOOTER >>>"
    try:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        if required_footer_marker not in content:
            errors.append("FOOTER_MISSING")
    except FileNotFoundError:
        errors.append("FILE_NOT_FOUND")
        log.warning(f"Footer check failed: File not found {file_path}")
    except OSError as e:
        errors.append(f"FOOTER_CHECK_OS_ERROR: {e}")
        log.error(f"Footer check failed for {file_path}: {e}")
    except Exception as e:
        log.exception(f"Unexpected error during footer check for {file_path}", exc_info=e)
        errors.append("FOOTER_CHECK_UNEXPECTED_ERROR")

    return errors


# --- Main Orchestration Function ---

AnalysisResult = dict[
    str,
    list[
        str  # For simple string error codes like header/footer
        | ComplexityViolation
        | DocstringViolation
        | LineCountViolation
        | ParameterViolation
        | StatementViolation
    ],
]


def analyze_file_compliance(
    file_path: str | Path,
    # Thresholds are now mandatory arguments
    max_complexity: int,
    max_params: int,
    max_statements: int,
    max_lines: int,
    ignore_rules: list[str] | None = None,
) -> AnalysisResult:
    """Analyzes a single Python file for Zeroth Law compliance.

    Runs various checks using the provided thresholds and ignores specified rules.

    Args:
    ----
        file_path: Path to the Python file.
        max_complexity: Maximum allowed cyclomatic complexity.
        max_params: Maximum allowed function parameters.
        max_statements: Maximum allowed function statements.
        max_lines: Maximum allowed executable lines in the file.
        ignore_rules: A list of rule codes (strings) to ignore. Violations matching
                      these codes will not be reported.

    Returns:
    -------
        A dictionary where keys are violation categories (e.g., 'header', 'complexity')
        and values are lists of violation details.
        Returns an empty dictionary if the file is compliant.

    """
    results: AnalysisResult = {}
    p_file_path = Path(file_path)
    processed_ignore_rules = set(ignore_rules) if ignore_rules else set()

    log.debug(f"Analyzing file: {p_file_path} (Ignoring: {processed_ignore_rules or 'None'})")

    # --- File Content Checks (Header/Footer) ---
    header_errors = check_header_compliance(p_file_path)
    if header_errors:
        results["header"] = header_errors

    footer_errors = check_footer_compliance(p_file_path)
    if footer_errors:
        results["footer"] = footer_errors

    # If basic structure is wrong, maybe skip deeper analysis?
    # For now, analyze everything regardless.

    # --- AST-based and Token-based Checks ---
    try:
        # Pass the mandatory thresholds to the analysis functions
        line_count_errors = analyze_line_counts(p_file_path, max_lines)
        if line_count_errors:
            results["line_counts"] = line_count_errors

        docstring_errors = analyze_docstrings(p_file_path)
        if docstring_errors:
            results["docstrings"] = docstring_errors

        complexity_errors = analyze_complexity(p_file_path, max_complexity)
        if complexity_errors:
            results["complexity"] = complexity_errors

        parameter_errors = analyze_parameters(p_file_path, max_params)
        if parameter_errors:
            results["parameters"] = parameter_errors

        statement_errors = analyze_statements(p_file_path, max_statements)
        if statement_errors:
            results["statements"] = statement_errors

    except (FileNotFoundError, SyntaxError, OSError) as e:
        # Errors during AST/Token analysis for a specific category are logged within
        # the respective analyze_* function. Here, catch errors that prevent any
        # AST analysis from starting.
        log.error(f"Cannot perform AST/Token analysis on {p_file_path}: {e}")
        results["analysis_error"] = [f"File cannot be parsed: {e}"]
    except Exception as e:
        # Catch-all for unexpected errors during the analysis phase
        log.exception(f"Unexpected error during detailed analysis of {p_file_path}", exc_info=e)
        results["analysis_error"] = [f"Unexpected analysis failure: {e}"]

    # --- Filter results based on ignore_rules ---
    if not processed_ignore_rules:
        # No filtering needed if ignore list is empty
        pass
    else:
        filtered_results: AnalysisResult = {}
        for category, violations in results.items():
            filtered_violations = []
            for violation in violations:
                # Simple check: If the violation is a string code, check if it's ignored.
                if isinstance(violation, str) and violation in processed_ignore_rules:
                    continue  # Ignore this specific string violation code
                # TODO: Add more sophisticated filtering for tuple-based violations later
                filtered_violations.append(violation)

            # Only add category back if there are remaining violations
            if filtered_violations:
                filtered_results[category] = filtered_violations
        results = filtered_results  # Replace original results with filtered ones

    if results:
        log.debug(f"Violations found in {p_file_path}: {list(results.keys())}")
    else:
        log.debug(f"No violations found in {p_file_path}")

    return results


# <<< ZEROTH LAW FOOTER >>>
