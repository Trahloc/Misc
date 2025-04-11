# FILE: src/zeroth_law/actions/lint/python.py
"""Executes Python linting checks using configured consultant tools."""

import logging
import subprocess
import sys  # Import the sys module
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
# TODO: Replace basic logging with structlog configured instance


def run_python_lint(config: dict[str, Any], project_root: Path) -> bool:
    """Runs Python linters (ruff check, mypy) via subprocess.

    Args:
    ----
        config: The loaded ZLF configuration (currently unused).
        project_root: The root path of the project being analyzed.

    Returns:
    -------
        True if linting passed, False otherwise.

    """
    passed = True
    # --- Ruff Check ---
    log.info("Executing consultant tool: ruff check")
    ruff_command = ["poetry", "run", "ruff", "check", "."]
    try:
        # Run from the project root
        # TODO: Use config to customize ruff args (e.g., specific files, config path)
        # Using fixed command array with no user input mitigates S603 security risk
        result = subprocess.run(
            ruff_command,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on failure, check returncode
        )
        log.debug("'ruff check' command finished.")
        log.debug(f"Return Code: {result.returncode}")
        if result.stdout:
            # Output stdout directly for user visibility
            print(result.stdout)
            log.debug(f"stdout:\n{result.stdout}")
        if result.stderr:
            # Output stderr directly for user visibility
            print(result.stderr, file=sys.stderr)  # Use sys.stderr
            log.debug(f"stderr:\n{result.stderr}")

        if result.returncode != 0:
            log.warning("Consultant 'ruff check' reported issues (non-zero exit code).")
            passed = False
        else:
            log.info("Consultant 'ruff check' completed with no issues reported.")

    except FileNotFoundError:
        log.error(f"Error: Command not found. Is 'poetry' installed and in PATH? Command: {' '.join(ruff_command)}")
        passed = False
    except Exception as e:
        # Using .exception() instead of .error() with exc_info=True as per G201
        log.exception(f"Error running consultant 'ruff check': {e}")
        passed = False

    # --- MyPy Check (Example - Add later) ---
    # log.info("Executing consultant tool: mypy")
    # mypy_command = ["poetry", "run", "mypy", ".", "--strict"]
    # try:
    #     result = subprocess.run(...)
    #     if result.returncode != 0: passed = False
    # except ...:
    #     passed = False

    # TODO: Add execution for other configured linters (e.g., targeted pylint)

    return passed
