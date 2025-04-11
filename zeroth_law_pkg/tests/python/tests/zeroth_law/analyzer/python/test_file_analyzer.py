# File: tests/python/tests/zeroth_law/analyzer/python/test_file_analyzer.py
"""Tests for the Python file analyzer using data-driven test cases."""

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
from zeroth_law.analyzer.python.analyzer import analyze_file_compliance  # noqa: E402


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
