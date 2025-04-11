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


def test_perform_ast_analysis_generic_exception(monkeypatch):
    """Test perform_ast_analysis when a generic exception occurs during analysis."""
    test_file = Path("dummy.py")

    # Mock analyze_line_counts to raise an exception
    def mock_analyze_line_counts(*args, **kwargs):
        raise Exception("Test exception")

    monkeypatch.setattr(
        "zeroth_law.analyzer.python.analyzer_refactor.analyze_line_counts",
        mock_analyze_line_counts,
    )

    result = perform_ast_analysis(
        test_file,
        max_complexity=10,
        max_params=5,
        max_statements=50,
        max_lines=100,
    )

    assert "analysis_error" in result
    assert any("Unexpected analysis failure" in str(error) for error in result["analysis_error"])


def test_analyze_file_compliance_with_errors(tmp_path, monkeypatch):
    """Test analyze_file_compliance with files causing errors."""
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Hello')", encoding="utf-8")

    # First test that header/footer violations are properly detected
    result = analyze_file_compliance(
        test_file,
        max_complexity=10,
        max_params=5,
        max_statements=50,
        max_lines=100,
    )

    assert "header" in result
    assert "HEADER_LINE_1_MISMATCH" in result["header"]

    # Now test AST analysis errors by mocking the perform_ast_analysis function
    def mock_ast_analysis(*args, **kwargs):
        return {"analysis_error": ["File cannot be parsed: SyntaxError in test_file"]}

    # Mock both header/footer checks and AST analysis
    monkeypatch.setattr(
        "zeroth_law.analyzer.python.analyzer_refactor.check_header_compliance",
        lambda x: [],
    )
    monkeypatch.setattr(
        "zeroth_law.analyzer.python.analyzer_refactor.check_footer_compliance",
        lambda x: [],
    )
    monkeypatch.setattr(
        "zeroth_law.analyzer.python.analyzer_refactor.perform_ast_analysis",
        mock_ast_analysis,
    )

    # Now when we call analyze_file_compliance, it should use our mocked functions
    result = analyze_file_compliance(
        test_file,
        max_complexity=10,
        max_params=5,
        max_statements=50,
        max_lines=100,
    )

    # Verify that the analysis error is present
    assert "analysis_error" in result
    assert "File cannot be parsed" in result["analysis_error"][0]
