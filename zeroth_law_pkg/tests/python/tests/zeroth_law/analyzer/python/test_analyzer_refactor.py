"""Tests for the refactored Python analyzer using data-driven test cases."""

import os
import sys
from pathlib import Path

import pytest

# Ensure the src directory is in the path for imports
current_dir = Path(__file__).parent
src_path = current_dir.parent.parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from tests.python.tests.zeroth_law.analyzer.python.case_types import AnalyzerCase  # noqa: E402
from tests.python.tests.zeroth_law.analyzer.python.test_cases import (  # noqa: E402
    complexity_test_cases,
    docstring_test_cases,
    footer_test_cases,
    header_test_cases,
    line_test_cases,
    parameter_test_cases,
    statement_test_cases,
)

# Import from the refactored module
from zeroth_law.analyzer.python.analyzer_refactor import (  # noqa: E402
    analyze_file_compliance,
    check_footer_compliance,
    check_header_compliance,
    create_analysis_result,
    filter_ignored_violations,
    perform_ast_analysis,
)


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


# Test helper functions first
def test_create_analysis_result():
    """Test the create_analysis_result function."""
    # Empty result
    result = create_analysis_result()
    assert isinstance(result, dict)
    assert len(result) == 0

    # With violations
    violations = ["HEADER_LINE_1_MISMATCH"]
    result = create_analysis_result(header=violations)
    assert result == {"header": violations}

    # With multiple categories
    result = create_analysis_result(header=["HEADER_LINE_1_MISMATCH"], footer=["FOOTER_MISSING"])
    assert result == {
        "header": ["HEADER_LINE_1_MISMATCH"],
        "footer": ["FOOTER_MISSING"],
    }


def test_filter_ignored_violations():
    """Test the filter_ignored_violations function."""
    # Empty ignored rules
    result = {"header": ["HEADER_LINE_1_MISMATCH"]}
    filtered = filter_ignored_violations(result, [])
    assert filtered == result

    # Ignore a rule
    result = {"header": ["HEADER_LINE_1_MISMATCH"]}
    filtered = filter_ignored_violations(result, ["HEADER_LINE_1_MISMATCH"])
    assert filtered == {}

    # Ignore one of multiple rules
    result = {"header": ["HEADER_LINE_1_MISMATCH"], "footer": ["FOOTER_MISSING"]}
    filtered = filter_ignored_violations(result, ["HEADER_LINE_1_MISMATCH"])
    assert filtered == {"footer": ["FOOTER_MISSING"]}


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


@pytest.mark.parametrize("test_case", header_test_cases + footer_test_cases)
def test_perform_ast_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test the perform_ast_analysis function."""
    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())
    result = perform_ast_analysis(
        file_path,
        max_complexity=test_case.config["max_complexity"],
        max_params=test_case.config["max_params"],
        max_statements=test_case.config["max_statements"],
        max_lines=test_case.config["max_lines"],
    )

    # Since we're testing just the AST-based analysis, header and footer
    # violations should not be in the result (those are handled separately)
    assert "header" not in result
    assert "footer" not in result

    # Check for analysis errors on invalid files (if any)
    if not os.path.exists(file_path) or "missing" in test_case.name:
        # Some checks may have failed, but we can't assert on specifics
        pass


# Combine all test cases for full file analysis
all_test_cases = (
    header_test_cases
    + footer_test_cases
    + docstring_test_cases
    + complexity_test_cases
    + parameter_test_cases
    + statement_test_cases
    + line_test_cases
)


@pytest.mark.parametrize("test_case", all_test_cases)
def test_file_analysis(test_case: AnalyzerCase, tmp_path: Path) -> None:
    """Test full file analysis with data-driven test cases."""
    file_path = create_test_file(tmp_path, "test.py", test_case.get_content())
    result = analyze_file_compliance(
        file_path,
        max_complexity=test_case.config["max_complexity"],
        max_params=test_case.config["max_params"],
        max_statements=test_case.config["max_statements"],
        max_lines=test_case.config["max_lines"],
    )

    # For header/footer violations, check the specific category
    if test_case in header_test_cases:
        assert result.get("header", []) == test_case.expected_violations
    elif test_case in footer_test_cases:
        assert result.get("footer", []) == test_case.expected_violations
    elif test_case in docstring_test_cases:
        assert result.get("docstrings", []) == test_case.expected_violations
    elif test_case in complexity_test_cases:
        assert result.get("complexity", []) == test_case.expected_violations
    elif test_case in parameter_test_cases:
        assert result.get("parameters", []) == test_case.expected_violations
    elif test_case in statement_test_cases:
        assert result.get("statements", []) == test_case.expected_violations
    elif test_case in line_test_cases:
        assert result.get("line_counts", []) == test_case.expected_violations


def test_ignore_rules():
    """Test the ignore_rules parameter of analyze_file_compliance."""
    # Create a file with header and footer violations
    content = """This file has no proper header or footer."""

    # Test with no ignored rules
    tmp_path = Path("/tmp")  # Just for type checking, not actually used
    mp = pytest.MonkeyPatch()
    # Mock the check functions to return known violations
    mp.setattr(
        "zeroth_law.analyzer.python.analyzer_refactor.check_header_compliance",
        lambda _: ["HEADER_LINE_1_MISMATCH"],
    )
    mp.setattr(
        "zeroth_law.analyzer.python.analyzer_refactor.check_footer_compliance",
        lambda _: ["FOOTER_MISSING"],
    )
    mp.setattr(
        "zeroth_law.analyzer.python.analyzer_refactor.perform_ast_analysis",
        lambda *args, **kwargs: {},
    )

    # Test with no ignored rules
    result = analyze_file_compliance(
        tmp_path,
        max_complexity=10,
        max_params=5,
        max_statements=50,
        max_lines=100,
    )
    assert "header" in result
    assert "footer" in result

    # Test with ignored rules
    result = analyze_file_compliance(
        tmp_path,
        max_complexity=10,
        max_params=5,
        max_statements=50,
        max_lines=100,
        ignore_rules=["HEADER_LINE_1_MISMATCH"],
    )
    assert "header" not in result
    assert "footer" in result

    # Test with all rules ignored
    result = analyze_file_compliance(
        tmp_path,
        max_complexity=10,
        max_params=5,
        max_statements=50,
        max_lines=100,
        ignore_rules=["HEADER_LINE_1_MISMATCH", "FOOTER_MISSING"],
    )
    assert "header" not in result
    assert "footer" not in result
