# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/metrics/imports.py
"""
# PURPOSE: Analyze import statements for context independence

## INTERFACES:
  - calculate_import_metrics(tree: ast.AST) -> dict: Analyze imports

## DEPENDENCIES:
    ast
    pylint.lint
    io
    tempfile
"""
import ast
import io
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple
from pylint.lint import Run
from pylint.reporters.text import TextReporter
from zeroth_law.utils.config import load_config


def _run_pylint_check(source_code: str) -> str:
    """Run pylint's unused-import check on source code.

    Args:
        source_code (str): The source code to analyze

    Returns:
        str: The pylint output
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        temp_file.write(source_code)
        temp_file_path = temp_file.name

    try:
        pylint_output = io.StringIO()
        reporter = TextReporter(pylint_output)
        Run(
            ["--disable=all", "--enable=unused-import", temp_file_path],
            reporter=reporter,
            exit=False,
        )
        return pylint_output.getvalue()
    finally:
        Path(temp_file_path).unlink()


def _count_unused_imports(pylint_output: str) -> int:
    """Count the number of unused imports from pylint output.

    Args:
        pylint_output (str): The pylint output to analyze

    Returns:
        int: Number of unused imports found
    """
    return sum(1 for line in pylint_output.splitlines() if "unused-import" in line)


def calculate_import_metrics(tree: ast.AST) -> Dict[str, Any]:
    """Analyzes imports using pylint to detect unused imports.

    This function uses pylint's unused-import check to identify imports that
    are not used in the code. The penalty for each unused import is configured
    in the project settings.
    """
    source = ast.unparse(tree)
    pylint_output = _run_pylint_check(source)
    unused_imports = _count_unused_imports(pylint_output)

    config = load_config()
    unused_import_penalty = config.get("unused_import_penalty", 10)
    imports_score = max(0, 100 - unused_imports * unused_import_penalty)

    return {"import_count": unused_imports, "imports_score": imports_score}


# ## KNOWN ERRORS:
# None
#
# ## IMPROVEMENTS:
# None
#
# ## FUTURE TODOs:
# Consider adding more sophisticated import analysis, such as checking for unused imports.
#
# ## ZEROTH LAW COMPLIANCE:
# Overall Score: 100/100 - Excellent
# Penalties:
# Analysis Timestamp: 2025-04-07T13:34:55.173688
