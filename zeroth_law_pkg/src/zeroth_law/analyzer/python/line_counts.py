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


def _is_docstring_token(toktype, tokval, prev_tok_type, srow, scol, indent_level):
    """Determine if a token is part of a docstring."""
    # Module docstring (first string at column 0 after ENCODING/NEWLINE)
    if scol == 0 and toktype == tokenize.STRING and prev_tok_type in (tokenize.ENCODING, tokenize.NEWLINE, None):
        return True

    # Class/Function docstring (after DEF/CLASS keywords and INDENT)
    if toktype == tokenize.STRING and prev_tok_type in (tokenize.INDENT, tokenize.NEWLINE) and indent_level > 0:
        return True

    return False


def _count_executable_lines(content: str) -> tuple[int, set[int]]:
    """Counts the number of likely executable lines using the tokenize module.

    Excludes comments, blank lines, and docstrings.
    Counts lines containing actual code tokens.

    Args:
    ----
        content: The string content of the Python code.

    Returns:
    -------
        A tuple containing:
          - The count of executable lines
          - A set of line numbers containing code

    """
    lines_with_code = set()
    prev_tok_type = None
    indent_level = 0
    in_docstring = False
    docstring_start_row = 0

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(content).readline))

        for i, (toktype, tokval, (srow, scol), (erow, ecol), line) in enumerate(tokens):
            # Handle indentation level tracking
            if toktype == tokenize.INDENT:
                indent_level += 1
            elif toktype == tokenize.DEDENT:
                indent_level -= 1

            # Docstring detection
            if not in_docstring and _is_docstring_token(toktype, tokval, prev_tok_type, srow, scol, indent_level):
                in_docstring = True
                docstring_start_row = srow

            # End of docstring detection
            if in_docstring and toktype == tokenize.STRING and srow >= docstring_start_row:
                # The docstring token itself has finished
                in_docstring = False

            # Add executable lines (skip tokens in docstrings, comments, etc.)
            if not in_docstring and toktype not in (
                tokenize.COMMENT,
                tokenize.NL,  # Non-logical newline
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.ERRORTOKEN,
            ):
                lines_with_code.add(srow)

            prev_tok_type = toktype

        return len(lines_with_code), lines_with_code

    except tokenize.TokenError as e:
        log.warning(f"Tokenizing error during line count: {e}")
        # Improved fallback that attempts to exclude comments and blank lines
        code_lines = set()
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                code_lines.add(i)
        return len(code_lines), code_lines
    except Exception as e:
        log.exception("Unexpected error during tokenized line count", exc_info=e)
        # Fallback
        code_lines = set()
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                code_lines.add(i)
        return len(code_lines), code_lines


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
        executable_line_count, _ = _count_executable_lines(content)

        if executable_line_count > max_lines:
            violations.append(("max_executable_lines", executable_line_count))
            log.debug(f"File {path.name} exceeds max line count: {executable_line_count} > {max_lines}")

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
