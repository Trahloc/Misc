# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/tests/test_reporting.py
"""
# PURPOSE: Tests for the Zeroth Law reporting functions.

## INTERFACES:
 - All test functions

## DEPENDENCIES:
 - pytest
 - zeroth_law.reporting
"""
import pytest
from zeroth_law.reporting import generate_report, generate_summary_report


def test_generate_report_error():
    """Tests generating a report for a file with an error."""
    metrics = {"file_path": "test.py", "error": "Test error message"}
    report = generate_report(metrics)
    assert "Error analyzing" in report
    assert "test.py" in report
    assert "Test error message" in report


def test_generate_report_template_file():
    """Tests generating a report for a template file."""
    metrics = {
        "file_path": "template.py",
        "file_name": "template.py",
        "is_template": True,
        "executable_lines": 10,
        "header_footer_status": "complete"
    }
    report = generate_report(metrics)
    assert "Template File - Not Scored" in report
    assert "Executable Lines: 10" in report
    assert "Header/Footer Status: complete" in report


def test_generate_report_regular_file():
    """Tests generating a report for a regular Python file."""
    metrics = {
        "file_path": "test.py",
        "file_name": "test.py",
        "overall_score": 90,
        "compliance_level": "Excellent",
        "total_lines": 100,
        "header_lines": 20,
        "footer_lines": 15,
        "effective_lines": 65,
        "executable_lines": 50,
        "header_footer_status": "complete",
        "import_count": 5,
        "functions": [
            {
                "name": "test_function",
                "lines": 25,
                "cyclomatic_complexity": 5,
                "has_docstring": True,
                "parameter_count": 2,
                "naming_score": 95
            }
        ],
        "penalties": [
            {"reason": "Function test_function exceeds max lines", "deduction": 5}
        ]
    }
    
    report = generate_report(metrics)
    assert "Overall Score: 90/100 - Excellent" in report
    assert "Total Lines: 100" in report
    assert "Function Metrics:" in report
    assert "test_function" in report
    assert "Lines: 25" in report
    assert "Penalties:" in report
    assert "Function test_function exceeds max lines: -5" in report


def test_generate_summary_report_empty():
    """Tests generating a summary report with no files."""
    report = generate_summary_report([])
    assert "No files analyzed." in report


def test_generate_summary_report_errors_only():
    """Tests generating a summary report with only error files."""
    all_metrics = [
        {"file_path": "test1.py", "error": "Error 1"},
        {"file_path": "test2.py", "error": "Error 2"}
    ]
    report = generate_summary_report(all_metrics)
    assert "Error analyzing all files." in report


def test_generate_summary_report_mixed():
    """Tests generating a summary report with mixed file types and scores."""
    all_metrics = [
        # Template file
        {
            "file_path": "template.py",
            "is_template": True,
            "executable_lines": 10
        },
        # Regular files
        {
            "file_path": "excellent.py",
            "overall_score": 95,
            "compliance_level": "Excellent"
        },
        {
            "file_path": "good.py",
            "overall_score": 80,
            "compliance_level": "Good"
        },
        {
            "file_path": "adequate.py",
            "overall_score": 60,
            "compliance_level": "Adequate"
        },
        {
            "file_path": "needs_improvement.py",
            "overall_score": 40,
            "compliance_level": "Needs Improvement"
        }
    ]
    
    report = generate_summary_report(all_metrics)
    
    assert "Total Files Analyzed: 5" in report
    assert "Template Files: 1" in report
    assert "Scored Files: 4" in report
    assert "Average Overall Score: 68.75/100" in report
    assert "Compliance Distribution:" in report
    assert "Excellent: 1" in report
    assert "Good: 1" in report
    assert "Adequate: 1" in report
    assert "Needs Improvement: 1" in report 