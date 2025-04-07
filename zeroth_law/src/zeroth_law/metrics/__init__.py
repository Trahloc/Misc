# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/metrics/__init__.py
"""
# PURPOSE: Exports functions from the metrics module.

## INTERFACES:
   All functions

## DEPENDENCIES:
  - None
"""

from zeroth_law.metrics.cyclomatic_complexity import calculate_cyclomatic_complexity
from zeroth_law.metrics.docstring_coverage import calculate_docstring_coverage
from zeroth_law.metrics.file_size import calculate_file_size_metrics
from zeroth_law.metrics.function_size import calculate_function_size_metrics
from zeroth_law.metrics.naming import calculate_naming_score
from zeroth_law.metrics.imports import calculate_import_metrics

__all__ = [
    "calculate_cyclomatic_complexity",
    "calculate_docstring_coverage",
    "calculate_file_size_metrics",
    "calculate_function_size_metrics",
    "calculate_naming_score",
    "calculate_import_metrics",
]

"""
## KNOWN ERRORS: None.

## IMPROVEMENTS: None.

## FUTURE TODOs: None.

## ZEROTH LAW COMPLIANCE:
    - Overall Score: 100/100 - Excellent
    - Penalties:
    - Analysis Timestamp: 2025-04-06T15:52:46.588790
"""
