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
        input_file: Path to the test data file relative to test_data/zeroth_law/analyzer/python/
        expected_violations: List of expected violation codes or tuples of (function_name, line_number, count)
        config: Optional configuration overrides for this test case

    """

    name: str
    input_file: str
    expected_violations: list[str | tuple[str, int] | tuple[str, int, int]]
    config: dict[str, Any] | None = None

    def get_content(self) -> str:
        """Get the content of the test data file."""
        test_data_dir = Path(__file__).parent.parent.parent.parent.parent / "test_data" / "zeroth_law" / "analyzer" / "python"
        file_path = test_data_dir / self.input_file
        return file_path.read_text(encoding="utf-8")


# <<< ZEROTH LAW FOOTER >>>
