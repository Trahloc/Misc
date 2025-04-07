# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/tests/test_utils.py
"""
# PURPOSE: Tests for the Zeroth Law utility functions.

## INTERFACES:
 - All test functions

## DEPENDENCIES:
 - pytest
 - zeroth_law.utils
"""
import pytest
from zeroth_law.utils import find_header_footer, count_executable_lines, replace_footer
from zeroth_law.utils.file_utils import edit_file_with_black
from zeroth_law.utils.config import load_config


def test_find_header_footer_complete():
    """Tests finding both header and footer in a complete file."""
    source_code = '''"""
# PURPOSE: Test file with header and footer.

## INTERFACES:
 - function_name(): Description
"""

def function_name():
    """This is a docstring"""
    pass

"""
## KNOWN ERRORS: None

## IMPROVEMENTS: None

## FUTURE TODOs: None

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 90/100 - Excellent
    - Penalties:
      - None
    - Analysis Timestamp: 2025-03-23T10:00:00
"""'''

    header, footer = find_header_footer(source_code)
    assert header is not None, "Header should be found"
    assert footer is not None, "Footer should be found"
    assert "PURPOSE" in header
    assert "ZEROTH LAW COMPLIANCE" in footer


def test_find_header_footer_missing():
    """Tests finding header/footer when they're missing."""
    source_code = 'def function_name():\n    """Docstring"""\n    pass'

    header, footer = find_header_footer(source_code)
    assert header is None, "Header should be None when missing"
    assert footer is None, "Footer should be None when missing"


def test_count_executable_lines():
    """Tests counting executable lines in code."""
    code = '''"""
Docstring
"""
# Comment
import sys  # Inline comment

def function():
    """Function docstring"""
    a = 1
    b = 2  # Inline comment
    # Comment
    return a + b

class TestClass:
    pass
'''
    count = count_executable_lines(code)
    # Expected lines: import, def line, a=1, b=2, return, class, pass
    assert count == 7


def test_replace_footer_existing():
    """Tests replacing an existing footer."""
    original = '''"""
# PURPOSE: Test file

## INTERFACES: None
"""

def test():
    pass

"""
## KNOWN ERRORS: None

## IMPROVEMENTS: None

## FUTURE TODOs: None

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 80/100 - Good
    - Analysis Timestamp: 2025-03-23T09:00:00
"""'''

    new_footer = '''"""
## KNOWN ERRORS: None

## IMPROVEMENTS: Fixed issues

## FUTURE TODOs: None

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 90/100 - Excellent
    - Analysis Timestamp: 2025-03-23T10:00:00
"""'''

    updated = replace_footer(original, new_footer)
    assert "Score: 90/100" in updated
    assert "Score: 80/100" not in updated


def test_replace_footer_none_existing():
    """Tests adding a footer when none exists."""
    original = '''"""
# PURPOSE: Test file

## INTERFACES: None
"""

def test():
    pass
'''

    new_footer = '''"""
## KNOWN ERRORS: None

## IMPROVEMENTS: None

## FUTURE TODOs: None

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 90/100 - Excellent
    - Analysis Timestamp: 2025-03-23T10:00:00
"""'''

    updated = replace_footer(original, new_footer)
    assert "Score: 90/100" in updated
    assert original in updated
    assert updated.endswith(new_footer)


def test_edit_file_with_black_formatting():
    """Test that edit_file_with_black only runs Black formatting without pytest."""
    test_content = """def example():
  return    True"""  # Intentionally poorly formatted

    expected_content = """def example():
    return True
"""  # Black-formatted version

    # Test formatting a Python file
    result = edit_file_with_black("test.py", test_content)
    assert result == expected_content

    # Test skipping non-Python file
    non_py_content = "def test(): return True"
    result = edit_file_with_black("test.txt", non_py_content)
    assert result == non_py_content


def test_config_respects_zeroth_law_toml():
    """Test that the configuration from .zeroth_law.toml is respected."""
    # Load the actual config
    config = load_config(".zeroth_law.toml")

    # Verify config values
    assert config["max_function_lines"] == 30, "max_function_lines should be 30"
    assert config["max_line_length"] == 140, "max_line_length should be 140"
    assert config["max_cyclomatic_complexity"] == 8, "max_cyclomatic_complexity should be 8"
    assert config["max_parameters"] == 4, "max_parameters should be 4"
    assert config["max_locals"] == 15, "max_locals should be 15"
    assert config["missing_header_penalty"] == 20, "missing_header_penalty should be 20"
    assert config["missing_footer_penalty"] == 10, "missing_footer_penalty should be 10"
    assert config["missing_docstring_penalty"] == 2, "missing_docstring_penalty should be 2"

    # Test a function that exceeds max_function_lines
    long_function = "def test():\n" + "    x = 1\n" * 51  # 52 lines total
    result = edit_file_with_black("test.py", long_function)

    # Black should still format it, but we should get a warning in the logs
    assert "x = 1" in result
    assert len(result.splitlines()) > 50
