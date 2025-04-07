"""
# PURPOSE: Tests for the Zeroth Law updater functions.

## INTERFACES:
 - test_update_file_footer_initial: Test initial footer update
 - test_update_file_footer_second: Test second footer update

## DEPENDENCIES:
 - pytest
 - zeroth_law.reporting.updater
"""

import pytest
import os
import tempfile
from zeroth_law.reporting.updater import update_file_footer, generate_footer


def test_update_file_footer_initial():
    """Test that initial footer update works correctly and doesn't include missing footer penalty."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(
            '''"""
# PURPOSE: Test file

## INTERFACES: None
"""

def test():
    pass
'''
        )
        temp_path = f.name

    try:
        metrics = {"overall_score": 100, "compliance_level": "Excellent", "penalties": []}

        update_file_footer(temp_path, metrics)

        with open(temp_path, "r") as f:
            content = f.read()

        assert "Missing footer" not in content
        assert "Overall Score: 100/100 - Excellent" in content
        assert "Penalties:" in content
        assert "None" in content

    finally:
        os.unlink(temp_path)


def test_update_file_footer_second():
    """Test that second footer update preserves file content and doesn't nuke the file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(
            '''"""
# PURPOSE: Test file

## INTERFACES: None
"""

def test():
    pass

"""
## KNOWN ERRORS: None.

## IMPROVEMENTS: None.

## FUTURE TODOs: None.

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 100/100 - Excellent
    - Penalties: None
    - Analysis Timestamp: 2024-03-21T12:00:00Z
"""
'''
        )
        temp_path = f.name

    try:
        metrics = {"overall_score": 90, "compliance_level": "Good", "penalties": [{"reason": "Test penalty", "deduction": 10}]}

        update_file_footer(temp_path, metrics)

        with open(temp_path, "r") as f:
            content = f.read()

        assert "PURPOSE: Test file" in content
        assert "def test():" in content
        assert "Overall Score: 90/100 - Good" in content
        assert "Test penalty: -10" in content

    finally:
        os.unlink(temp_path)
