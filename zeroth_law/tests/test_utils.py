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