#/zeroth_law/metrics/file_size.py
"""
# PURPOSE: Calculate metrics related to file size.

## INTERFACES:
- calculate_file_size_metrics(source_code: str, header: str | None, footer: str | None) -> dict: Calculate file size metrics

## DEPENDENCIES:
  - None
"""
from typing import Dict, Any

def calculate_file_size_metrics(source_code: str, header: str | None, footer: str | None) -> Dict[str, Any]:
    """Calculates file size metrics, excluding header and footer."""
    total_lines = source_code.count("\n") + 1
    header_lines = header.count("\n") + 1 if header else 0
    footer_lines = footer.count("\n") + 1 if footer else 0
    effective_lines = total_lines - header_lines - footer_lines


    return {
        "total_lines": total_lines,
        "header_lines": header_lines,
        "footer_lines": footer_lines,
        "effective_lines": effective_lines,
    }
