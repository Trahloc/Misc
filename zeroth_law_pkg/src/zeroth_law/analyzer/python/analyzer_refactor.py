# <<< ZEROTH LAW HEADER >>>
# FILE: src/zeroth_law/analyzer/python/analyzer_refactor.py
"""Main Python code analyzer for Zeroth Law compliance.

Orchestrates various checks like header, footer, complexity, docstrings, etc.
This is a refactored version with better separation of concerns.
"""

import logging
from pathlib import Path
from typing import TypeVar

# Replace deprecated typing imports with Python 3.13+ syntax
# from typing import Dict, List, Optional, Set, Tuple, Union
# Import analysis functions from submodules
from .complexity import ComplexityViolation, analyze_complexity
from .docstrings import DocstringViolation, analyze_docstrings
from .line_counts import LineCountViolation, analyze_line_counts
from .parameters import ParameterViolation, analyze_parameters
from .statements import StatementViolation, analyze_statements

# Setup logging
log = logging.getLogger(__name__)

# Constants
EXPECTED_HEADER_LINE_1 = "# <<< ZEROTH LAW HEADER >>>"
REQUIRED_FOOTER_MARKER = "# <<< ZEROTH LAW FOOTER >>>"

# Type definitions using modern Python 3.13+ syntax
ViolationType = (
    str  # For simple string error codes like header/footer
    | ComplexityViolation
    | DocstringViolation
    | LineCountViolation
    | ParameterViolation
    | StatementViolation
)

ViolationCollection = list[ViolationType]
AnalysisResult = dict[str, ViolationCollection]
T = TypeVar("T")


def safe_file_operation(file_path: Path, operation: callable, error_prefix: str) -> tuple[T | None, list[str]]:
    """Safely perform a file operation with standardized error handling.

    Args:
    ----
        file_path: Path to the file to operate on
        operation: Function that performs the actual file operation
        error_prefix: Prefix for error codes

    Returns:
    -------
        Tuple containing:
            - The result of the operation if successful, None otherwise
            - List of error codes if any occurred

    """
    errors: list[str] = []
    result = None

    try:
        result = operation(file_path)
    except FileNotFoundError:
        errors.append("FILE_NOT_FOUND")
        log.warning(f"{error_prefix} failed: File not found {file_path}")
    except OSError as e:
        errors.append(f"{error_prefix}_OS_ERROR: {e}")
        log.error(f"{error_prefix} failed for {file_path}: {e}")
    except Exception as e:
        log.exception(
            f"Unexpected error during {error_prefix.lower()} for {file_path}",
            exc_info=e,
        )
        errors.append(f"{error_prefix}_UNEXPECTED_ERROR")

    return result, errors


def check_header_compliance(file_path: str | Path) -> list[str]:
    """Check if a file starts with the required Zeroth Law header.

    Checks for:
        1. Line 1 matches EXPECTED_HEADER_LINE_1
        2. Line 2 starts with "# FILE:"
        3. Line 3 starts with '\"\"\"'

    Args:
    ----
        file_path: The path to the Python file.

    Returns:
    -------
        A list of error codes if non-compliant, empty list otherwise.
        Possible error codes:
          - HEADER_LINE_1_MISMATCH
          - HEADER_MISSING_FILE_LINE
          - HEADER_MISSING_DOCSTRING_START
          - FILE_NOT_FOUND
          - HEADER_CHECK_OS_ERROR
          - HEADER_CHECK_UNEXPECTED_ERROR

    """
    p_file_path = Path(file_path)

    def _check_header(path: Path) -> list[str]:
        errors: list[str] = []
        with path.open("r", encoding="utf-8") as f:
            # Read the first three lines
            line1_raw = f.readline()
            line2_raw = f.readline()
            line3_raw = f.readline()

            # Check Line 1 for exact header marker
            if not line1_raw or line1_raw.strip() != EXPECTED_HEADER_LINE_1:
                errors.append("HEADER_LINE_1_MISMATCH")
                return errors

            # Check Line 2 for # FILE:
            if not line2_raw or not line2_raw.strip().startswith("# FILE:"):
                errors.append("HEADER_MISSING_FILE_LINE")
                return errors

            # Check Line 3 for """
            if not line3_raw or not line3_raw.strip().startswith('"""'):
                errors.append("HEADER_MISSING_DOCSTRING_START")
                return errors

        return errors

    result, errors = safe_file_operation(p_file_path, _check_header, "HEADER_CHECK")
    return result if result else errors


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
    p_file_path = Path(file_path)

    def _check_footer(path: Path) -> list[str]:
        # import time # Keep commented out for now
        # time.sleep(3) # Keep commented out for now
        log.debug(f"Executing _check_footer for {path}")

        # content, errors = safe_file_operation(path, lambda p: p.read_text(), "Footer")
        # log.debug(f"_check_footer: Content read: {content is not None}, Errors: {errors}")

        # Temporarily disable strict footer check to align with test expectation
        # if REQUIRED_FOOTER_MARKER not in content:
        #     errors.append("FOOTER_MISSING")
        #     log.debug(f"_check_footer: Footer missing. Errors: {errors}")
        content, errors = safe_file_operation(path, lambda p: p.read_text(), "Footer")
        log.debug(f"_check_footer: Content read: {content is not None}, Errors: {errors}")

        if content is None:
            log.error(f"Failed to read content for footer check in {path}")
            return errors  # Return early if content couldn't be read

        # Re-enable strict footer check
        if REQUIRED_FOOTER_MARKER not in content:
            errors.append("FOOTER_MISSING")
            log.debug(f"_check_footer: Footer missing based on marker. Errors: {errors}")

        # log.debug(f"_check_footer finished. Returning errors: {errors}")
        # print(f"_check_footer finished for {path}. Returning errors: {errors}")
        return errors

    result, errors = safe_file_operation(p_file_path, _check_footer, "FOOTER_CHECK")
    return result if result else errors


def perform_ast_analysis(
    file_path: str | Path,
    max_complexity: int,
    max_params: int,
    max_statements: int,
    max_lines: int,
) -> AnalysisResult:
    """Perform AST and token-based analyses on a Python file.

    This includes complexity, docstrings, line counts, parameters, and statements.

    Args:
    ----
        file_path: Path to the Python file
        max_complexity: Maximum allowed cyclomatic complexity
        max_params: Maximum allowed function parameters
        max_statements: Maximum allowed function statements
        max_lines: Maximum allowed executable lines in the file

    Returns:
    -------
        A dictionary where keys are violation categories and values are lists of violations

    """
    p_file_path = Path(file_path)
    results: AnalysisResult = {}
    log.debug(f"[{p_file_path.name}] Starting AST/Token analysis...")

    try:
        # Line count checks
        log.debug(f"[{p_file_path.name}] Analyzing line counts (max: {max_lines})...")
        line_count_errors = analyze_line_counts(p_file_path, max_lines)
        log.debug(f"[{p_file_path.name}] Line count analysis complete. Errors: {line_count_errors}")
        if line_count_errors:
            results["line_counts"] = line_count_errors

        # Docstring checks
        log.debug(f"[{p_file_path.name}] Analyzing docstrings...")
        docstring_errors = analyze_docstrings(p_file_path)
        log.debug(f"[{p_file_path.name}] Docstring analysis complete. Errors: {docstring_errors}")
        if docstring_errors:
            results["docstrings"] = docstring_errors

        # Complexity checks
        log.debug(f"[{p_file_path.name}] Analyzing complexity (max: {max_complexity})...")
        complexity_errors = analyze_complexity(p_file_path, max_complexity)
        log.debug(f"[{p_file_path.name}] Complexity analysis complete. Errors: {complexity_errors}")
        if complexity_errors:
            results["complexity"] = complexity_errors

        # Parameter checks
        log.debug(f"[{p_file_path.name}] Analyzing parameters (max: {max_params})...")
        parameter_errors = analyze_parameters(p_file_path, max_params)
        log.debug(f"[{p_file_path.name}] Parameter analysis complete. Errors: {parameter_errors}")
        if parameter_errors:
            results["parameters"] = parameter_errors

        # Statement checks
        log.debug(f"[{p_file_path.name}] Analyzing statements (max: {max_statements})...")
        statement_errors = analyze_statements(p_file_path, max_statements)
        log.debug(f"[{p_file_path.name}] Statement analysis complete. Errors: {statement_errors}")
        if statement_errors:
            results["statements"] = statement_errors

    except (FileNotFoundError, SyntaxError, OSError) as e:
        log.error(f"[{p_file_path.name}] Cannot perform AST/Token analysis: {e}")
        results["analysis_error"] = [f"File cannot be parsed: {e}"]
    except Exception as e:
        log.exception(f"[{p_file_path.name}] Unexpected error during detailed analysis", exc_info=e)
        results["analysis_error"] = [f"Unexpected analysis failure: {e}"]

    log.debug(f"[{p_file_path.name}] AST/Token analysis finished. Results: {results}")
    return results


def create_analysis_result(**violations: ViolationCollection | None) -> AnalysisResult:
    """Create an analysis result dictionary from violation collections.

    Args:
    ----
        **violations: Keyword arguments where keys are violation categories
                      and values are lists of violations

    Returns:
    -------
        A dictionary where keys are violation categories and values are lists of violations

    """
    result: AnalysisResult = {}
    for category, violation_list in violations.items():
        if violation_list:
            result[category] = violation_list
    return result


def filter_ignored_violations(results: AnalysisResult, ignore_rules: list[str]) -> AnalysisResult:
    """Filter out ignored violations from analysis results.

    Args:
    ----
        results: The analysis results to filter
        ignore_rules: List of rule codes to ignore

    Returns:
    -------
        Filtered analysis results

    """
    if not ignore_rules:
        return results

    processed_ignore_rules = set(ignore_rules)
    filtered_results: AnalysisResult = {}

    for category, violations in results.items():
        filtered_violations = []
        for violation in violations:
            # Simple check: If the violation is a string code, check if it's ignored
            if isinstance(violation, str) and violation in processed_ignore_rules:
                continue  # Ignore this specific string violation code
            # Enhanced check: If the violation is a tuple, check if its first element (rule code) is ignored
            elif isinstance(violation, tuple) and violation and violation[0] in processed_ignore_rules:
                log.debug(f"Ignoring tuple violation based on rule code: {violation[0]}")
                continue  # Ignore tuple if first element matches an ignore rule
            # Keep the violation if it's not ignored
            filtered_violations.append(violation)

        # Only add category back if there are remaining violations
        if filtered_violations:
            filtered_results[category] = filtered_violations

    return filtered_results


def analyze_file_compliance(
    file_path: str | Path,
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
        file_path: Path to the Python file
        max_complexity: Maximum allowed cyclomatic complexity
        max_params: Maximum allowed function parameters
        max_statements: Maximum allowed function statements
        max_lines: Maximum allowed executable lines in the file
        ignore_rules: A list of rule codes (strings) to ignore

    Returns:
    -------
        A dictionary where keys are violation categories and values are lists of violations

    """
    p_file_path = Path(file_path)
    processed_ignore_rules = ignore_rules or []

    log.debug(f"Analyzing file: {p_file_path} (Ignoring: {processed_ignore_rules or 'None'})")

    # Perform header and footer checks
    log.debug(f"[{p_file_path.name}] Checking header...")
    header_errors = check_header_compliance(p_file_path)
    log.debug(f"[{p_file_path.name}] Header check complete. Errors: {header_errors}")

    log.debug(f"[{p_file_path.name}] Checking footer...")
    footer_errors = check_footer_compliance(p_file_path)
    log.debug(f"[{p_file_path.name}] Footer check complete. Errors: {footer_errors}")

    # Combine with AST analysis results
    log.debug(f"[{p_file_path.name}] Performing AST analysis...")
    ast_results = perform_ast_analysis(
        p_file_path,
        max_complexity=max_complexity,
        max_params=max_params,
        max_statements=max_statements,
        max_lines=max_lines,
    )
    log.debug(f"[{p_file_path.name}] AST analysis complete. Results: {ast_results}")

    # Combine all results
    results = create_analysis_result(header=header_errors, footer=footer_errors, **ast_results)
    log.debug(f"[{p_file_path.name}] Combined results before filtering: {results}")

    # Filter ignored rules
    filtered_results = filter_ignored_violations(results, processed_ignore_rules)
    log.debug(f"[{p_file_path.name}] Final results after filtering: {filtered_results}")

    if filtered_results:
        # log.debug(f"Violations found in {p_file_path}: {list(filtered_results.keys())}")
        pass  # Keep the structure, just remove the log
    else:
        # log.debug(f"No violations found in {p_file_path}")
        pass  # Keep the structure, just remove the log

    return filtered_results


# <<< ZEROTH LAW FOOTER >>>
