# FILE: tests/analyzer/python/test_analyzer.py
"""Tests for the Python analyzer using data-driven test cases."""

import sys
from pathlib import Path

import pytest

# Ensure the src directory is in the path for imports
current_dir = Path(__file__).parent
src_path = current_dir.parent.parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from tests.test_data.test_analyzer.python.analyzer_test_cases import (  # noqa: E402
    complexity_test_cases,
    docstring_test_cases,
    footer_test_cases,
    header_test_cases,
    line_test_cases,
    parameter_test_cases,
    statement_test_cases,
)
from tests.test_data.test_analyzer.python.case_types import AnalyzerCase  # noqa: E402
from zeroth_law.analyzer.python.analyzer import (  # noqa: E402
    analyze_complexity,
    analyze_docstrings,
    analyze_file_compliance,
    analyze_line_counts,
    analyze_parameters,
    analyze_statements,
    check_footer_compliance,
    check_header_compliance,
)

# Import specific analyzers needed by tests
# Remove redundant imports below as they are already imported from analyzer.py above
# from zeroth_law.analyzer.python.complexity import analyze_complexity  # noqa: E402
# from zeroth_law.analyzer.python.line_counts import analyze_line_counts  # noqa: E402
# from zeroth_law.analyzer.python.parameters import analyze_parameters  # noqa: E402
# from zeroth_law.analyzer.python.statements import analyze_statements  # noqa: E402


# Helper to create a file with content
def create_test_file(tmp_path: Path, filename: str, content: str) -> Path:
    """Creates a file in the temporary directory."""
    file_path = tmp_path / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


# Helper to get path to test data file
def get_test_data_path(filename: str) -> Path:
    """Get the path to a test data file."""
    return Path(__file__).parent.parent.parent / "test_data" / "zeroth_law" / "analyzer" / "python" / filename


# --- Combine all test cases for full file analysis --- #
# Ensure all imported lists are actually lists before combining
all_test_cases = (
    header_test_cases
    + footer_test_cases
    + docstring_test_cases
    + complexity_test_cases
    + parameter_test_cases
    + statement_test_cases
    + line_test_cases
)


# --- Tests for individual analyzer components --- #


# Data-driven tests for each analyzer component
@pytest.mark.parametrize("test_case", header_test_cases)
def test_header_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test header analysis with data-driven test cases."""
    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())
    result = check_header_compliance(file_path)
    assert result == test_case.expected_violations


@pytest.mark.parametrize("test_case", footer_test_cases)
def test_footer_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test footer analysis with data-driven test cases."""
    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())
    result = check_footer_compliance(file_path)
    assert result == test_case.expected_violations


@pytest.mark.parametrize("test_case", docstring_test_cases)
def test_docstring_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test docstring analysis with data-driven test cases."""
    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())
    result = analyze_docstrings(file_path)
    assert result == test_case.expected_violations


@pytest.mark.parametrize("test_case", complexity_test_cases)
def test_complexity_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test complexity analysis with data-driven test cases."""
    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())
    result = analyze_complexity(file_path, threshold=test_case.config["max_complexity"])
    assert result == test_case.expected_violations


@pytest.mark.parametrize("test_case", parameter_test_cases)
def test_parameter_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test parameter analysis with data-driven test cases."""
    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())
    result = analyze_parameters(file_path, threshold=test_case.config["max_params"])
    assert result == test_case.expected_violations


@pytest.mark.parametrize("test_case", statement_test_cases)
def test_statement_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test statement analysis with data-driven test cases."""
    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())
    result = analyze_statements(file_path, threshold=test_case.config["max_statements"])
    assert result == test_case.expected_violations


@pytest.mark.parametrize("test_case", line_test_cases)
def test_line_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test line analysis with data-driven test cases."""
    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())
    result = analyze_line_counts(file_path, test_case.config["max_lines"])
    assert result == test_case.expected_violations


# --- Test for the main orchestration function --- #


@pytest.mark.parametrize("test_case", all_test_cases)
def test_file_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test full file analysis orchestration with data-driven test cases."""
    # NOTE: This test relies on the structure of AnalyzerCase and the combined test cases.
    # It assumes the necessary test case files exist at the imported path.

    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())

    # Call the main orchestration function
    result = analyze_file_compliance(
        file_path,
        max_complexity=test_case.config["max_complexity"],
        max_params=test_case.config["max_params"],
        max_statements=test_case.config["max_statements"],
        max_lines=test_case.config["max_lines"],
        # ignore_rules=test_case.config.get("ignore_rules") # Optional: If ignore rules are part of test cases
    )

    # Assert based on the combined expected violations across all relevant categories for this case.
    # This assertion logic needs to be carefully defined based on how expected violations
    # are structured in the AnalyzerCase objects for combined tests.
    # Example (simple check for *any* expected violation type defined in the case):
    expected_violation_found = False
    for category, expected in test_case.expected_violations.items():
        if expected:  # If there are expected violations for this category
            assert (
                result.get(category, []) == expected
            ), f"Mismatch in category '{category}' for test case {test_case.name}"
            expected_violation_found = True

    # If the case expected violations but none were matched above, fail.
    # Also check if the result contained unexpected violations.
    if test_case.expected_violations and not expected_violation_found:
        pytest.fail(
            f"Test case {test_case.name} expected violations but none matched categories: {list(test_case.expected_violations.keys())}"
        )

    # Check for unexpected violation categories in the result
    unexpected_categories = set(result.keys()) - set(test_case.expected_violations.keys())
    # Filter out categories that might have empty lists if no violations were found
    unexpected_categories = {cat for cat in unexpected_categories if result[cat]}
    assert (
        not unexpected_categories
    ), f"Found unexpected violation categories {unexpected_categories} for test case {test_case.name}"
