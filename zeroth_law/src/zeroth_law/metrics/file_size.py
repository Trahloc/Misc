# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/metrics/file_size.py
"""
# PURPOSE: Calculate metrics related to file size.

## INTERFACES:
  - calculate_file_size_metrics(source_code: str, header: str | None, footer: str | None) -> dict: Calculate file size metrics

## DEPENDENCIES:
   - typing
   - zeroth_law.utils.config
"""
from typing import Dict, Any, Optional
from zeroth_law.utils import config


def calculate_file_size_metrics(source_code: str, header: Optional[str], footer: Optional[str]) -> Dict[str, Any]:
    """Calculate various metrics related to file size.

    This function calculates metrics such as total lines, header lines,
    footer lines, effective lines (excluding header and footer), and checks
    for lines exceeding the configured maximum length.

    Args:
        source_code (str): The complete source code of the file.
        header (Optional[str]): The header content if present.
        footer (Optional[str]): The footer content if present.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - total_lines (int): Total number of lines in the file
            - header_lines (int): Number of lines in the header
            - footer_lines (int): Number of lines in the footer
            - effective_lines (int): Number of lines excluding header and footer
            - long_lines (list): List of line numbers exceeding max length
            - max_line_length (int): Maximum allowed line length
    """
    lines = source_code.splitlines()
    total_lines = len(lines)

    header_lines = len(header.splitlines()) if header else 0
    footer_lines = len(footer.splitlines()) if footer else 0

    effective_lines = total_lines - header_lines - footer_lines

    # Check for lines exceeding max length
    max_line_length = config.get("max_line_length", 100)
    long_lines = [i + 1 for i, line in enumerate(lines) if len(line) > max_line_length]  # Convert to 1-based line numbers

    return {
        "total_lines": total_lines,
        "header_lines": header_lines,
        "footer_lines": footer_lines,
        "effective_lines": effective_lines,
        "long_lines": long_lines,
        "max_line_length": max_line_length,
    }


"""
## KNOWN ERRORS: None.

## IMPROVEMENTS: None.

## FUTURE TODOs: Consider adding more sophisticated file size analysis, such as checking for file size thresholds.

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 95/100 - Good
    - Penalties:
      - Function calculate_file_size_metrics exceeds max lines: -5
    - Analysis Timestamp: 2025-04-06T15:52:46.325129
"""
