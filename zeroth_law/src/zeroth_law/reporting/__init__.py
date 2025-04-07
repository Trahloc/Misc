"""
# PURPOSE: Reporting module for Zeroth Law.

## INTERFACES:
 - formatter: Format compliance reports and metrics
 - updater: Update file headers and footers

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
"""

from zeroth_law.reporting.formatter import (
    format_compliance_report,
    format_file_metrics,
    format_function_metrics,
    format_summary_report,
)
from zeroth_law.reporting.updater import update_file_footer, generate_footer

__all__ = [
    "format_compliance_report",
    "format_file_metrics",
    "format_function_metrics",
    "format_summary_report",
    "update_file_footer",
    "generate_footer",
]
