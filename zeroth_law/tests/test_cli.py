"""
# PURPOSE: Tests for command-line interface functionality.

## INTERFACES:
 - TestCommandLine: Test class for CLI functionality

## DEPENDENCIES:
 - pytest
 - click.testing
 - zeroth_law.cli
"""
import pytest
from click.testing import CliRunner
from zeroth_law.cli import main
import os
import tempfile
import logging

@pytest.fixture
def temp_python_file():
    """Creates a temporary Python file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('"""Test file."""\ndef test():\n    pass')
    yield f.name
    os.unlink(f.name)

def test_summary_with_verbose(temp_python_file, caplog):
    """Test that summary reports are shown when verbose mode is enabled."""
    runner = CliRunner()
    with caplog.at_level(logging.INFO):
        result = runner.invoke(main, ['-vv', '-r', '-s', os.path.dirname(temp_python_file)])

    # Check that we got both logging output and summary report
    assert "Analyzing directory:" in caplog.text  # Changed to match actual log format
    assert "Analyzing file:" in caplog.text  # Added to verify file analysis logging
    assert "ZEROTH LAW SUMMARY REPORT" in result.output
    assert result.exit_code == 0

def test_summary_without_verbose(temp_python_file, caplog):
    """Test that summary reports are shown when verbose mode is disabled."""
    runner = CliRunner()
    result = runner.invoke(main, ['-r', '-s', os.path.dirname(temp_python_file)])

    # Check that we got the summary report but no logging
    assert "Analyzing" not in caplog.text
    assert "ZEROTH LAW SUMMARY REPORT" in result.output
    assert result.exit_code == 0