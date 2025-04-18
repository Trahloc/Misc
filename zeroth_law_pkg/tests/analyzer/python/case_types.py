# File: tests/python/tests/zeroth_law/analyzer/python/case_types.py
"""Test case type definitions for the Python analyzer."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AnalyzerCase:
    """A test case for the Python analyzer.

    Attributes:
        name: A descriptive name for the test case
        input_file: Path to the test data file relative to test_data/analyzer/python/
        expected_violations: List of expected violation codes or tuples of (function_name, line_number, count)
        config: Optional configuration overrides for this test case

    """

    name: str
    input_file: str
    expected_violations: list[str | tuple[str, int] | tuple[str, int, int]]
    config: dict[str, Any] | None = None

    def get_content(self) -> str:
        """Get the content of the test data file."""
        # Calculate path relative to this file's location to find tests/test_data/
        # tests/analyzer/python/ -> tests/analyzer/ -> tests/
        tests_dir = Path(__file__).parent.parent.parent
        test_data_dir = tests_dir / "test_data" / "analyzer" / "python"
        file_path = test_data_dir / self.input_file
        # Add error handling for missing test data file
        if not file_path.is_file():
            raise FileNotFoundError(f"Test data file not found: {file_path}. " f"Ensure test data is correctly placed in '{test_data_dir}'.")
        return file_path.read_text(encoding="utf-8")


# <<< ZEROTH LAW FOOTER >>>
