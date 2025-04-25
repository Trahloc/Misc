# File: tests/python/tests/zeroth_law/analyzer/python/test_analyzer_refactor_errors.py
"""Tests for error handling in the refactored Python analyzer."""

import os
import sys
from pathlib import Path

# Ensure the src directory is in the path for imports
current_dir = Path(__file__).parent
src_path = current_dir.parent.parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import the functions to test
from zeroth_law.analyzer.python.analyzer_refactor import (  # noqa: E402
    analyze_file_compliance,
    perform_ast_analysis,
    safe_file_operation,
)


def test_safe_file_operation_file_not_found():
    """Test safe_file_operation when file is not found."""
    non_existent_file = Path("/path/to/non/existent/file.py")

    # Define an operation that attempts to open the file, triggering FileNotFoundError
    def read_op(path):
        with path.open("r") as f:
            return f.read()

    result, errors = safe_file_operation(non_existent_file, read_op, "TEST")

    assert result is None
    assert "FILE_NOT_FOUND" in errors


def test_safe_file_operation_os_error(tmp_path):
    """Test safe_file_operation when an OS error occurs."""
    test_file = tmp_path / "test.py"
    test_file.write_text("test content", encoding="utf-8")

    # Make the file non-readable
    os.chmod(test_file, 0)

    # Define an operation that will trigger an OS error
    def read_op(path):
        with path.open("r") as f:
            return f.read()

    result, errors = safe_file_operation(test_file, read_op, "TEST")

    assert result is None
    assert any(error.startswith("TEST_OS_ERROR") for error in errors)

    # Restore permissions for cleanup
    os.chmod(test_file, 0o644)


def test_safe_file_operation_generic_exception():
    """Test safe_file_operation when a generic exception occurs."""
    test_file = Path("dummy.py")

    # Define an operation that raises a custom exception
    def failing_op(path):
        raise ValueError("Custom error")

    result, errors = safe_file_operation(test_file, failing_op, "TEST")

    assert result is None
    assert "TEST_UNEXPECTED_ERROR" in errors


def test_perform_ast_analysis_syntax_error(tmp_path):
    """Test perform_ast_analysis with a file containing syntax errors."""
    test_file = tmp_path / "syntax_error.py"
    test_file.write_text("def invalid_syntax(:\n    pass", encoding="utf-8")

    result = perform_ast_analysis(
        test_file,
        max_complexity=10,
        max_params=5,
        max_statements=50,
        max_lines=100,
    )

    assert "analysis_error" in result
    assert any("File cannot be parsed" in str(error) for error in result["analysis_error"])


def test_analyze_file_compliance_with_errors(tmp_path):
    """Test analyze_file_compliance with files causing real errors (no mocking)."""

    config = {
        "max_complexity": 10,
        "max_params": 5,
        "max_statements": 50,
        "max_lines": 100,
    }

    # --- Test Case 1: Syntax Error --- #
    syntax_error_content = "def invalid_syntax(:\n    pass"
    syntax_error_file = tmp_path / "syntax_error.py"
    syntax_error_file.write_text(syntax_error_content, encoding="utf-8")

    result_syntax = analyze_file_compliance(
        syntax_error_file,
        max_complexity=config["max_complexity"],
        max_params=config["max_params"],
        max_statements=config["max_statements"],
        max_lines=config["max_lines"],
    )

    # Expect header/footer errors because the file is invalid
    assert "header" in result_syntax
    assert result_syntax["header"]  # Should not be empty
    assert "footer" in result_syntax
    assert result_syntax["footer"]  # Should not be empty

    # Expect analysis_error due to SyntaxError from perform_ast_analysis
    assert "analysis_error" in result_syntax
    assert any("File cannot be parsed" in str(e) for e in result_syntax["analysis_error"])
    assert any("invalid syntax" in str(e).lower() for e in result_syntax["analysis_error"])

    # --- Test Case 2: File Not Found --- #
    non_existent_file = tmp_path / "i_do_not_exist.py"

    result_not_found = analyze_file_compliance(
        non_existent_file,
        max_complexity=config["max_complexity"],
        max_params=config["max_params"],
        max_statements=config["max_statements"],
        max_lines=config["max_lines"],
    )

    # Expect header/footer errors related to file not found
    assert "header" in result_not_found
    assert any("FILE_NOT_FOUND" in str(e) for e in result_not_found["header"])
    assert "footer" in result_not_found
    assert any("FILE_NOT_FOUND" in str(e) for e in result_not_found["footer"])

    # Expect analysis_error due to FileNotFoundError from perform_ast_analysis
    assert "analysis_error" in result_not_found
    assert any("File cannot be parsed" in str(e) for e in result_not_found["analysis_error"])
    # Check for the specific OS error message components
    assert any("No such file or directory" in str(e) for e in result_not_found["analysis_error"])
    # assert any("FileNotFoundError" in str(e) for e in result_not_found["analysis_error"]) # Don't check for exception type string
