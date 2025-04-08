"""Tests for the compliance checker module."""

from pathlib import Path

import pytest

# Assuming the checker function/class will be in src.zeroth_law.analyzer.compliance_checker
# Updated import for new structure
from src.zeroth_law.analyzer.python.analyzer import (
    analyze_complexity,
    analyze_line_counts,
    analyze_parameters,
    analyze_statements,
    check_footer_compliance,
    check_header_compliance,
    check_test_file_existence,
)


# TODO: [test/header] Write test case for missing header comment.
def test_missing_header_comment_fails(tmp_path: Path) -> None:
    """Verify that a file missing the required header comment fails the check."""
    # Arrange
    content = "import os\n\ndef some_function():\n    pass\n"
    py_file = tmp_path / "missing_header.py"
    py_file.write_text(content, encoding="utf-8")

    # Act
    errors = check_header_compliance(py_file)

    # Assert
    assert "HEADER_MISSING_FILE_LINE" in errors
    assert "HEADER_MISSING_DOCSTRING_START" in errors
    # Explicitly check for absence of other potential errors if needed
    # assert "FILE_NOT_FOUND" not in errors


# TODO: Add test case for file with correct header.
# TODO: Add test case for file with < 2 lines.
# TODO: Add test case for file that exists but isn't readable (permissions?).
# TODO: Add test case for file with correct line 1 but incorrect line 2.
# TODO: Add test case for file with incorrect line 1 but correct line 2.


def test_missing_footer_comment_fails(tmp_path: Path) -> None:
    """Verify that a file missing the required footer comment fails the check."""
    # Arrange: File has correct header but no footer
    content = (
        "# FILE: correct_header_no_footer.py\n"
        '"""Module docstring."""\n'
        "import os\n"
        "\n"
        "def some_function():\n"
        "    pass\n"
        "# Missing the crucial footer section\n"
    )
    py_file = tmp_path / "no_footer.py"
    py_file.write_text(content, encoding="utf-8")

    # Act
    errors = check_footer_compliance(py_file)

    # Assert
    assert "FOOTER_MISSING" in errors
    # pytest.fail("Test not implemented yet, footer compliance check function needs to be called.")


# TODO: Add test case for file with correct header AND footer.
# TODO: Add test case for file where footer exists but has incorrect format?


def test_high_cyclomatic_complexity(tmp_path: Path) -> None:
    """Verify detection of high cyclomatic complexity."""
    # Arrange
    # Function complexity: 1 (base) + 1 (if) + 1 (for) + 1 (while) + 1 (and) = 5
    complex_code = (
        "# FILE: complex.py\n"
        '"""Module docstring."""\n'
        "def complex_function(a, b, c):\n"
        "    if a > 10: # +1\n"
        "        print('a')\n"
        "    for i in range(c): # +1\n"
        "        if a > 5 and b < 10: # +1 (for and)\n"
        "           print(i)\n"
        "    while c > 0: # +1\n"
        "        c -= 1\n"
        "    return a + b + c\n"
        # Remove footer section to avoid parsing issues
        # "\n"
        # "## ZEROTH LAW COMPLIANCE:\n"
        # "# ... footer content ...\n"
    )
    py_file = tmp_path / "complex.py"
    py_file.write_text(complex_code, encoding="utf-8")  # Write only the code part

    # Act
    threshold = 4  # Set threshold lower than actual complexity (5)
    violations = analyze_complexity(py_file, threshold)

    # Assert
    expected = [("complex_function", 3, 6)]  # name, line, score (Corrected expected complexity)
    assert violations == expected
    # pytest.fail("Test not implemented yet, analyze_complexity needs to be called.")


# TODO: Add complexity test for function just at the threshold.
# TODO: Add complexity test for async function.
# TODO: Add complexity test for file with multiple functions, some complex, some not.


def test_too_many_parameters(tmp_path: Path) -> None:
    """Verify detection of too many parameters."""
    # Arrange
    code = (
        "# FILE: params.py\n"
        '"""Module docstring."""\n'
        "def func_many_params(p1, p2, p3, p4, p5, p6):\n"
        "    pass\n"
        "\n"
        "def func_ok_params(p1, p2, p3):\n"
        "    pass\n"
        # Remove footer section entirely
        # "\n"
        # "## ZEROTH LAW COMPLIANCE:\n"
        # '"""\n\n' # Minimal valid footer
    )
    py_file = tmp_path / "params.py"
    py_file.write_text(code, encoding="utf-8")

    # Act
    threshold = 5  # Max allowed parameters
    violations = analyze_parameters(py_file, threshold)

    # Assert
    expected = [("func_many_params", 3, 6)]
    assert violations == expected
    # pytest.fail("Test not implemented yet, analyze_parameters needs to be called.")


# TODO: Add parameter test for methods (ignoring self/cls).

# TODO: Add parameter test for functions with pos-only and kw-only args.


def test_too_many_statements(tmp_path: Path) -> None:
    """Verify detection of a function with too many statements."""
    # Arrange
    code = (
        "# FILE: statements.py\n"
        '"""Module docstring."""\n'
        "def func_many_statements():\n"
        "    x = 1 # stmt 1\n"
        "    y = 2 # stmt 2\n"
        "    z = 3 # stmt 3\n"
        "    a = 4 # stmt 4\n"
        "    b = 5 # stmt 5\n"
        "    print(x+y+z+a+b) # stmt 6\n"
        "\n"
        "def func_ok_statements():\n"
        "    x = 1\n"
        "    print(x)\n"
        # No footer to avoid parsing issues
    )
    py_file = tmp_path / "statements.py"
    py_file.write_text(code, encoding="utf-8")

    # Act
    threshold = 5  # Max allowed statements
    violations = analyze_statements(py_file, threshold)

    # Assert
    expected = [("func_many_statements", 3, 6)]  # name, line, count
    assert violations == expected
    # pytest.fail("Test not implemented yet, analyze_statements needs to be called.")


# TODO: Add statement test for nested functions (should only count outer).
# TODO: Add statement test for function with only a docstring (count should be 0).
# TODO: Add statement test for function with pass (count should be 1).


def test_too_many_executable_lines(tmp_path: Path) -> None:
    """Verify detection of a file with too many executable lines."""
    # Arrange
    # Executable lines: import, x=1, y=2, print(x), return y = 5 lines
    code = (
        "# FILE: exec_lines.py\n"
        '"""Module docstring."""\n'
        "# A comment\n"
        "import os             # Executable 1\n"
        "\n"
        "def func():\n"
        "    # Another comment\n"
        "    x = 1             # Executable 2\n"
        "    y = 2             # Executable 3\n"
        "\n"
        "    print(x)          # Executable 4\n"
        "    return y          # Executable 5\n"
        "\n"
        "# Final comment\n"
        # No footer to avoid parsing issues
    )
    py_file = tmp_path / "exec_lines.py"
    py_file.write_text(code, encoding="utf-8")

    # Act
    threshold = 4  # Max allowed executable lines
    violations = analyze_line_counts(py_file, threshold)

    # Assert
    expected = [("max_executable_lines", 1, 6)]  # type, line (file level=1), count (def counts)
    assert violations == expected
    # pytest.fail("Test not implemented yet, analyze_line_counts needs to be called.")


# TODO: Add executable line test for files with different comment/blank line densities.


@pytest.mark.no_cover()
def test_missing_test_file_fails(tmp_path: Path) -> None:
    """Verify detection of a missing test file for an existing source file."""
    # Arrange
    # Create a dummy source file structure
    src_dir = tmp_path / "src" / "zeroth_law" / "module"
    src_dir.mkdir(parents=True)
    src_file = src_dir / "tested_source.py"
    src_file.write_text('# FILE: tested_source.py\n""Docstring."""\ndef func(): pass\n', encoding="utf-8")

    # Ensure the corresponding test directory exists, but NOT the file
    test_dir = tmp_path / "tests" / "module"
    test_dir.mkdir(parents=True)
    # test_file = test_dir / "test_tested_source.py" # DO NOT CREATE

    # Act
    # Assuming a function like check_test_file_existence(src_root, test_root)
    violations = check_test_file_existence(tmp_path / "src", tmp_path / "tests")

    # Assert
    # Placeholder - need to define how violations are reported
    expected_missing = [("missing_test_file", str(src_file))]  # Example format
    assert violations == expected_missing
    # pytest.fail("Test not implemented yet, test file existence check needs to be called.")


# TODO: Add test case where source file exists AND test file exists.
# TODO: Add test case for source files that should be ignored (e.g., __init__.py).
