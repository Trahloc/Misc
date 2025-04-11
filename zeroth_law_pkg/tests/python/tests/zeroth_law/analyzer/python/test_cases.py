# File: tests/python/tests/zeroth_law/analyzer/python/test_cases.py
"""Test case definitions for the Python analyzer."""

from .case_types import AnalyzerCase

# Header compliance test cases
header_test_cases = [
    AnalyzerCase(
        name="compliant_header",
        input_file="header_example.py",
        expected_violations=[],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    ),
    AnalyzerCase(
        name="missing_file_line",
        input_file="header_missing_file_line.py",
        expected_violations=["HEADER_MISSING_FILE_LINE"],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    ),
    AnalyzerCase(
        name="missing_docstring",
        input_file="header_missing_docstring.py",
        expected_violations=["HEADER_MISSING_DOCSTRING_START"],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    ),
    AnalyzerCase(
        name="completely_missing",
        input_file="header_completely_missing.py",
        expected_violations=["HEADER_LINE_1_MISMATCH"],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    ),
]

# Footer compliance test cases
footer_test_cases = [
    AnalyzerCase(
        name="compliant_footer",
        input_file="footer_example.py",
        expected_violations=[],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    ),
    AnalyzerCase(
        name="missing_footer",
        input_file="footer_missing.py",
        expected_violations=["FOOTER_MISSING"],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    ),
    AnalyzerCase(
        name="incorrect_footer",
        input_file="footer_wrong.py",
        expected_violations=["FOOTER_MISSING"],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    ),
]

# Docstring compliance test cases
docstring_test_cases = [
    AnalyzerCase(
        name="missing_function_docstring",
        input_file="docstrings_example.py",
        expected_violations=[("function_without_docstring", 11)],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    )
]

# Complexity test cases
complexity_test_cases = [
    AnalyzerCase(
        name="high_complexity",
        input_file="complexity_example.py",
        expected_violations=[("complex_function", 6, 12)],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    )
]

# Parameter count test cases
parameter_test_cases = [
    AnalyzerCase(
        name="too_many_parameters",
        input_file="parameters_example.py",
        expected_violations=[("function_with_many_params", 6, 6)],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    )
]

# Statement count test cases
statement_test_cases = [
    AnalyzerCase(
        name="too_many_statements",
        input_file="statements_example.py",
        expected_violations=[("function_with_many_statements", 6, 53)],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    )
]

# Line count test cases
line_test_cases = [
    AnalyzerCase(
        name="too_many_lines",
        input_file="too_many_lines.py",
        expected_violations=[("max_executable_lines", 114)],
        config={
            "max_complexity": 10,
            "max_lines": 100,
            "max_params": 5,
            "max_statements": 50,
        },
    )
]
