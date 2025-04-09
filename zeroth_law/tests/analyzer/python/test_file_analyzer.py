"""Tests for the main file compliance analyzer function."""

import os
import sys
from pathlib import Path

import pytest

# Ensure the src directory is in the path for imports
current_dir = Path(__file__).parent
src_path = current_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from zeroth_law.analyzer.python.analyzer import (
    analyze_file_compliance,
    check_footer_compliance,
    check_header_compliance,
)


# Helper to create a file with content
def create_test_file(tmp_path: Path, filename: str, content: str) -> Path:
    """Creates a file in the temporary directory."""
    file_path = tmp_path / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


# Define expected header and footer content for tests
# (Could be loaded from config later)
EXPECTED_HEADER = "# <<< ZEROTH LAW HEADER >>>"
EXPECTED_FOOTER = "# <<< ZEROTH LAW FOOTER >>>"

# Test cases for Header Compliance


def test_header_compliant_file(tmp_path: Path) -> None:
    """Verify a file with the correct header passes."""
    content = f"""{EXPECTED_HEADER}\n\n# Some code here\n"""
    test_file = create_test_file(tmp_path, "header_ok.py", content)
    violations = check_header_compliance(test_file)
    assert not violations, "Should have no header violations"


def test_header_missing(tmp_path: Path) -> None:
    """Verify a file missing the header reports HEADER_MISSING."""
    content = """# No header here\n\nprint('hello')\n"""
    test_file = create_test_file(tmp_path, "header_missing.py", content)
    violations = check_header_compliance(test_file)
    assert "HEADER_MISSING" in violations, "Should report HEADER_MISSING"


def test_header_incorrect(tmp_path: Path) -> None:
    """Verify a file with an incorrect header reports HEADER_INCORRECT."""
    content = """# --- INCORRECT HEADER --- \n\nprint('hello')\n"""
    test_file = create_test_file(tmp_path, "header_wrong.py", content)
    violations = check_header_compliance(test_file)
    assert "HEADER_INCORRECT" in violations, "Should report HEADER_INCORRECT"


# Test cases for Footer Compliance


def test_footer_compliant_file(tmp_path: Path) -> None:
    """Verify a file with the correct footer passes."""
    content = f"""# Some code here\n\n{EXPECTED_FOOTER}\n"""
    test_file = create_test_file(tmp_path, "footer_ok.py", content)
    violations = check_footer_compliance(test_file)
    assert not violations, "Should have no footer violations"


def test_footer_missing(tmp_path: Path) -> None:
    """Verify a file missing the footer reports FOOTER_MISSING."""
    content = """# No footer here\n\nprint('hello')\n"""
    test_file = create_test_file(tmp_path, "footer_missing.py", content)
    violations = check_footer_compliance(test_file)
    assert "FOOTER_MISSING" in violations, "Should report FOOTER_MISSING"


def test_footer_incorrect(tmp_path: Path) -> None:
    """Verify a file with an incorrect footer reports FOOTER_INCORRECT."""
    content = """# Some code\n\n# --- WRONG FOOTER --- \n"""
    test_file = create_test_file(tmp_path, "footer_wrong.py", content)
    violations = check_footer_compliance(test_file)
    assert "FOOTER_INCORRECT" in violations, "Should report FOOTER_INCORRECT"


# Existing test using the main analyzer function
# Modify this test to expect correct header/footer behavior now
def test_fully_compliant_file(tmp_path: Path) -> None:
    """Verify a fully compliant file reports no violations (after impl)."""
    # Arrange
    compliant_content = f"""{EXPECTED_HEADER}\n# FILE: compliant.py
\"\"\"Module docstring.\"\"\"

def main() -> None:
    print("Compliant")

{EXPECTED_FOOTER}
"""
    test_file = create_test_file(tmp_path, "compliant.py", compliant_content)

    # Act
    results = analyze_file_compliance(test_file, max_complexity=10, max_lines=100)

    # Assert
    # Expect empty dict (no violations) once header/footer checks are implemented
    assert results == {}, f"Expected no violations, but got: {results}"


# Test Case 2: Missing Header - FILE Line
def test_missing_header_file_line(tmp_path: Path) -> None:
    """Verify a file missing the '# FILE:' line reports the correct error."""
    # Arrange
    # This content starts directly with the docstring, missing the # FILE line.
    content_missing_file_line = """\"\"\"Module docstring.\"\"\"

def simple_function(a: int) -> int:
    \"\"\"Function docstring.\"\"\"
    return a + 1

# <<< ZEROTH LAW FOOTER >>>
"""

    test_file = create_test_file(tmp_path, "missing_file_line.py", content_missing_file_line)

    # Act
    results = analyze_file_compliance(test_file, max_complexity=10, max_params=5, max_statements=50, max_lines=100)

    # Assert
    expected_violations = {
        "header": ["HEADER_MISSING_FILE_LINE", "HEADER_MISSING_DOCSTRING_START"],
    }
    assert results == expected_violations


# Test Case 3: Missing Header - Docstring Start
def test_missing_header_docstring_start(tmp_path: Path) -> None:
    '''Verify a file missing the '"""' docstring start reports the correct error.'''
    # Arrange
    # This content has the FILE line but is missing the docstring start on line 2.
    content_missing_docstring = """# FILE: missing_docstring.py
# Some other comment instead of docstring start

def simple_function(a: int) -> int:
    return a + 1

# <<< ZEROTH LAW FOOTER >>>
"""
    test_file = create_test_file(tmp_path, "missing_docstring.py", content_missing_docstring)

    # Act
    results = analyze_file_compliance(test_file, max_complexity=10, max_params=5, max_statements=50, max_lines=100)

    # Assert
    expected_violations = {
        "header": ["HEADER_MISSING_DOCSTRING_START"],
        "docstrings": [("module", 1), ("simple_function", 4)],
    }
    assert results == expected_violations


# Test Case 4: Missing Footer
def test_missing_footer(tmp_path: Path) -> None:
    """Verify a file missing the footer marker reports the correct error."""
    # Arrange
    # This content is compliant except for the missing footer marker.
    content_missing_footer = """# FILE: missing_footer.py
\"\"\"Module docstring.\"\"\"

def simple_function(a: int) -> int:
    \"\"\"Function docstring.\"\"\"
    return a + 1

# Some other comment at the end
"""
    test_file = create_test_file(tmp_path, "missing_footer.py", content_missing_footer)

    # Act
    results = analyze_file_compliance(test_file, max_complexity=10, max_params=5, max_statements=50, max_lines=100)

    # Assert
    # Only expect the footer violation
    expected_violations = {"footer": ["FOOTER_MISSING"]}
    assert results == expected_violations


# Test Case 5: Missing Function Docstring
def test_missing_function_docstring(tmp_path: Path) -> None:
    """Verify a function missing a docstring is detected when header/footer are ok."""
    # Arrange
    content_missing_docstring = """# FILE: missing_func_docstring.py
\"\"\"Module docstring.\"\"\"

def function_without_docstring(x: int) -> int:
    # No docstring here
    return x * 2

def function_with_docstring(y: int) -> int:
    \"\"\"This one is fine.\"\"\"
    return y + 1

# <<< ZEROTH LAW FOOTER >>>
"""
    test_file = create_test_file(tmp_path, "missing_func_docstring.py", content_missing_docstring)

    # Act
    results = analyze_file_compliance(test_file, max_complexity=10, max_params=5, max_statements=50, max_lines=100)

    # Assert
    # Expect only the missing docstring violation for the specific function
    expected_violations = {"docstrings": [("function_without_docstring", 4)]}
    assert results == expected_violations


# Test Case 6: High Complexity
def test_high_complexity(tmp_path: Path) -> None:
    """Verify a function exceeding the complexity threshold is detected."""
    # Arrange
    # Default threshold is 10. This function has complexity > 10.
    content_high_complexity = """# FILE: high_complexity.py
\"\"\"Module docstring.\"\"\"

def complex_function(a, b, c, d, e, f):
    \"\"\"A complex function to test threshold.\"\"\"
    if a:
        if b:
            if c:
                print(1)
            elif d:
                print(2)
            else:
                print(3)
        elif e:
            for i in range(10):
                if i % 2 == 0:
                    print(i)
    elif f:
        while True:
            try:
                assert a is not None
                break
            except AssertionError:
                pass
    return 0

# <<< ZEROTH LAW FOOTER >>>
"""
    test_file = create_test_file(tmp_path, "high_complexity.py", content_high_complexity)

    # Act
    results = analyze_file_compliance(test_file, max_complexity=10, max_params=5, max_statements=50, max_lines=100)

    # Assert
    # Check the actual complexity calculated (was 12 in last run) and parameters.
    # Note: This might need adjustment if the visitor logic changes.
    expected_violations = {
        "complexity": [("complex_function", 4, 12)],
        "parameters": [("complex_function", 4, 6)],  # Function also exceeds param limit
    }
    assert results == expected_violations


# Test Case 7: Too Many Parameters
def test_too_many_parameters(tmp_path: Path) -> None:
    """Verify a function exceeding the parameter threshold is detected."""
    # Arrange
    # Default threshold is 5. This function has 6 parameters.
    content_many_params = """# FILE: many_params.py
\"\"\"Module docstring.\"\"\"

def function_with_many_params(p1, p2, p3, p4, p5, p6):
    \"\"\"This function has too many parameters.\"\"\"
    return p1 + p2 + p3 + p4 + p5 + p6

# <<< ZEROTH LAW FOOTER >>>
"""
    test_file = create_test_file(tmp_path, "many_params.py", content_many_params)

    # Act
    results = analyze_file_compliance(test_file, max_complexity=10, max_params=5, max_statements=50, max_lines=100)

    # Assert
    expected_violations = {"parameters": [("function_with_many_params", 4, 6)]}
    assert results == expected_violations


# Test Case 8: Too Many Statements
def test_too_many_statements(tmp_path: Path) -> None:
    """Verify a function exceeding the statement threshold is detected."""
    # Arrange
    # Default threshold is 50. Generate a function with 51 simple statements.
    statements = "\n".join([f"    x{i} = {i}" for i in range(51)])
    content_many_statements = f"""# FILE: many_statements.py
\"\"\"Module docstring.\"\"\"

def function_with_many_statements():
    \"\"\"This function has too many statements.\"\"\"
{statements}
    return 0

# <<< ZEROTH LAW FOOTER >>>
"""
    test_file = create_test_file(tmp_path, "many_statements.py", content_many_statements)

    # Act
    results = analyze_file_compliance(test_file, max_complexity=10, max_params=5, max_statements=50, max_lines=100)

    # Assert
    # Statement count excludes the docstring line.
    expected_violations = {
        "statements": [("function_with_many_statements", 4, 52)]  # 51 assignments + 1 return
    }
    assert results == expected_violations


# Test Case 9: Too Many Lines
def test_too_many_lines(tmp_path: Path) -> None:
    """Verify a file exceeding the total executable line threshold is detected."""
    # Arrange
    # Default threshold is 100. Generate content with > 100 executable lines.
    # Include comments, blank lines, and a docstring to ensure they aren't counted.
    lines = [
        "# FILE: too_many_lines.py",
        '"""Module docstring."""',
        "",
        "# A comment",
        "",
    ]
    # Add 101 simple assignment lines (executable)
    lines.extend([f"x{i} = {i}" for i in range(101)])
    lines.append("")  # Blank line
    lines.append("# <<< ZEROTH LAW FOOTER >>>")
    content_too_many_lines = "\n".join(lines)

    test_file = create_test_file(tmp_path, "too_many_lines.py", content_too_many_lines)

    # Act
    results = analyze_file_compliance(test_file, max_complexity=10, max_params=5, max_statements=50, max_lines=100)

    # Assert
    expected_violations = {"line_counts": [("max_executable_lines", 1, 102)]}
    assert results == expected_violations


# Test Case 10: Ignore Specific Rule
def test_ignore_rule(tmp_path: Path) -> None:
    """Verify that a specific rule code can be ignored."""
    # Arrange
    # Use the content from test_missing_header_file_line which triggers two header errors
    content_missing_file_line = """\"\"\"Module docstring.\"\"\"

def simple_function(a: int) -> int:
    \"\"\"Function docstring.\"\"\"
    return a + 1

# <<< ZEROTH LAW FOOTER >>>
"""
    test_file = create_test_file(tmp_path, "ignore_rule_test.py", content_missing_file_line)

    # Act
    # Analyze, but ignore one of the expected header violations
    results = analyze_file_compliance(
        test_file,
        max_complexity=10,  # Use defaults for non-relevant thresholds
        max_params=5,
        max_statements=50,
        max_lines=100,
        ignore_rules=["HEADER_MISSING_FILE_LINE"],  # Ignore the file line error
    )

    # Assert
    # Expect only the *other* header violation to be present
    expected_violations = {"header": ["HEADER_MISSING_DOCSTRING_START"]}
    assert results == expected_violations
