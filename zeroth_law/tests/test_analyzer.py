"""Tests for the code analysis functionality."""

from pathlib import Path

import pytest
from zeroth_law.analyzer import analyze_docstrings, analyze_header_footer

# from zeroth_law.analyzer import analyze_docstrings # To be created


@pytest.fixture()
def sample_python_code() -> str:
    """Provide a sample Python code string for testing."""
    return """
import os

def public_func_with_docstring(arg1: int):
    '''This function has a docstring.'''
    pass

def public_func_missing_docstring(arg2: str):
    pass

def _private_func_missing_docstring():
    # Should be ignored as it's private
    pass

async def async_public_func_missing_docstring():
    pass

class MyClass:
    def public_method_missing_docstring(self):
        pass

    def _private_method_missing_docstring(self):
        pass
"""


def test_find_missing_public_function_docstrings(tmp_path: Path, sample_python_code: str) -> None:
    """Verify finding public functions missing docstrings (D103)."""
    # Arrange
    file_path = tmp_path / "sample_module.py"
    file_path.write_text(sample_python_code, encoding="utf-8")

    # Expected: List of tuples (function_name, line_number)
    expected_missing = [
        ("public_func_missing_docstring", 8),
        ("async_public_func_missing_docstring", 15),
    ]

    # Act
    actual_missing = analyze_docstrings(file_path)

    # Assert
    assert sorted(actual_missing) == sorted(expected_missing)


def test_missing_header(tmp_path: Path) -> None:
    """Verify detection of a missing header (module docstring)."""
    # Arrange
    code_without_header = "import os\n\ndef func():\n    pass\n"
    file_path = tmp_path / "no_header.py"
    file_path.write_text(code_without_header, encoding="utf-8")

    expected_issues = [("missing_header", 1)]  # Issue type and line number

    # Act
    actual_issues = analyze_header_footer(file_path)

    # Assert
    assert actual_issues == expected_issues


def test_missing_footer(tmp_path: Path) -> None:
    """Verify detection of a missing Zeroth Law footer comment."""
    # Arrange - File HAS a header, but NO footer
    code_with_header_no_footer = '"""Module docstring (Header)."""\nimport os\ndef func():\n    pass\n'
    file_path = tmp_path / "no_footer.py"
    file_path.write_text(code_with_header_no_footer, encoding="utf-8")

    # Expected issue: missing footer. Line number might be EOF or last line of code.
    # Let's target the end-of-file for now, represented by line number of last line + 1
    last_line_num = len(code_with_header_no_footer.splitlines())
    expected_issues = [("missing_footer", last_line_num + 1)]

    # Act
    actual_issues = analyze_header_footer(file_path)

    # Assert
    assert actual_issues == expected_issues


# Next steps: Add tests for empty files, syntax errors, nested functions/classes
