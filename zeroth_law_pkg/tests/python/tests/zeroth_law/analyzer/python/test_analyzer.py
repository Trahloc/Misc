# FILE: tests/analyzer/python/test_analyzer.py
"""Tests for the Python analyzer using data-driven test cases."""

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
from zeroth_law.analyzer.python.analyzer import (  # noqa: E402
    analyze_complexity,
    analyze_docstrings,
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
