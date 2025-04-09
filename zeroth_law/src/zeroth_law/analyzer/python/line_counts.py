# FILE: src/zeroth_law/analyzer/python/line_counts.py
"""Analyzes Python files for line count thresholds."""

import io
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Type alias for violation result
LineCountViolation = tuple[str, int, int]  # (violation_type, line_number, count)

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------


def _count_executable_lines(content: str) -> int:
    """Counts the number of likely executable lines in Python code content.

    Excludes comments and blank lines.
    Does NOT attempt to exclude docstrings - relies on callers to handle
    potential minor inaccuracies if docstrings are counted.

    Args:
    ----
        content: The string content of the Python code.

    Returns:
    -------
        The count of non-blank, non-comment lines.

    """
    count = 0
    try:
        # Simpler approach: Iterate lines, skip blanks and full-line comments.
        for line in io.StringIO(content):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                count += 1
    except Exception as e:
        # Basic fallback in case of unexpected errors during iteration
        log.exception("Unexpected error during simplified line count", exc_info=e)
        return sum(1 for line in content.splitlines() if line.strip() and not line.strip().startswith("#"))

    return count


def analyze_line_counts(file_path: str | Path, max_lines: int) -> list[LineCountViolation]:
    """Analyzes a Python file for exceeding maximum executable line count.

    Args:
    ----
        file_path: Path to the Python file to analyze.
        max_lines: The maximum allowed executable lines.

    Returns:
    -------
        A list containing a violation tuple if the limit is exceeded,
        otherwise an empty list.

    Raises:
    ------
        FileNotFoundError: If file_path does not exist.
        OSError: For other file I/O errors.

    """
    violations: list[LineCountViolation] = []
    try:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        executable_line_count = _count_executable_lines(content)

        if executable_line_count > max_lines:
            # Report violation type, line number (conventionally 1 for file-level), and count
            violations.append(("max_executable_lines", 1, executable_line_count))

    except FileNotFoundError:
        log.error(f"File not found during line count analysis: {file_path}")
        raise  # Re-raise
    except OSError as e:
        log.error(f"OS error reading file for line count analysis {file_path}: {e}")
        raise  # Re-raise
    except Exception as e:
        log.exception(f"Unexpected error analyzing line counts for {file_path}", exc_info=e)
        raise RuntimeError(f"Unexpected error during line count analysis for {file_path}") from e

    return violations


# <<< ZEROTH LAW FOOTER >>>
