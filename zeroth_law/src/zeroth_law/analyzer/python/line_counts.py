# FILE: src/zeroth_law/analyzer/python/line_counts.py
"""Analyzes Python files for line count thresholds."""

import io
import logging
import tokenize
from pathlib import Path

log = logging.getLogger(__name__)

# Type alias for violation result
LineCountViolation = tuple[str, int]  # (violation_type, count)

# ----------------------------------------------------------------------------
# IMPLEMENTATION
# ----------------------------------------------------------------------------

# TODO(low): Investigate potential tokenize issue. The test 'test_too_many_lines_full_analysis'
#            using 'too_many_lines.py' resulted in 102 lines counted instead of the expected 101.
#            This suggests the tokenizer might be failing and the fallback logic (sum(1 for ...))
#            is being used, which incorrectly counts the module docstring line. Verify why
#            tokenize might fail on simple assignment code and if the fallback is appropriate.


def _count_executable_lines(content: str) -> int:
    """Counts the number of likely executable lines using the tokenize module.

    Excludes comments, blank lines, and docstrings.
    Counts lines containing actual code tokens.

    Args:
    ----
        content: The string content of the Python code.

    Returns:
    -------
        The count of executable lines.

    """
    count = 0
    lines_with_code = set()
    prev_tok_type = None
    indent_level = 0
    is_docstring = False

    try:
        g = tokenize.generate_tokens(io.StringIO(content).readline)
        for toktype, tokval, (srow, scol), (erow, ecol), line in g:
            # Detect Module/Class/Function docstrings
            if scol == 0 and indent_level == 0 and toktype == tokenize.STRING and prev_tok_type == tokenize.NEWLINE:  # Module docstring
                is_docstring = True
            elif (
                scol > 0 and toktype == tokenize.STRING and prev_tok_type in (tokenize.INDENT, tokenize.NEWLINE)
            ):  # Class/Func docstring starts
                # Crude check: Assume string after indent/newline in def/class is docstring
                # This might misclassify multiline strings assigned to variables at indent 0
                # A more robust check involves AST, but tokenize is faster for just line count.
                is_docstring = True

            if not is_docstring and toktype not in (
                tokenize.COMMENT,
                tokenize.NL,  # Non-logical newline
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.ENDMARKER,
                tokenize.ERRORTOKEN,
            ):
                # If it's a meaningful token on a line we haven't counted yet
                lines_with_code.add(srow)

            # Reset docstring flag after the string token
            if toktype == tokenize.STRING and is_docstring:
                is_docstring = False  # Assume docstring ends after the token

            # Track indentation to help with docstring detection
            if toktype == tokenize.INDENT:
                indent_level += 1
            elif toktype == tokenize.DEDENT:
                indent_level -= 1

            prev_tok_type = toktype

        count = len(lines_with_code)

    except tokenize.TokenError as e:
        log.warning(f"Tokenizing error during line count: {e}")
        # Fallback to basic count if tokenizing fails?
        return sum(1 for line in content.splitlines() if line.strip() and not line.strip().startswith("#"))
    except Exception as e:
        log.exception("Unexpected error during tokenized line count", exc_info=e)
        # Fallback
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
            # Changed violation format to (type, count)
            violations.append(("max_executable_lines", executable_line_count))

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
