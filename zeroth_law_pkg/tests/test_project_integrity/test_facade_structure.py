# FILE: tests/test_project_integrity/test_facade_structure.py
"""
Tests to ensure the Command Facade structure (Sec 4.19) is followed within subcommands.
"""

import pytest
from pathlib import Path

# TODO: Broaden scope beyond subcommands eventually. Start focused.
# Define the base directory to scan
SUBCOMMANDS_DIR = Path("src/zeroth_law/subcommands")

# Skip all tests in this file if the base directory doesn't exist
if not SUBCOMMANDS_DIR.is_dir():
    pytest.skip(f"Subcommands directory not found: {SUBCOMMANDS_DIR}", allow_module_level=True)


def test_command_facade_structure():
    """
    Verifies that subcommands adhere to the Facade structure:
    - No '*_cmd.py' files exist.
    - Facade files (e.g., 'sync.py') have a corresponding helper directory ('_sync/').
    - Helper directories (e.g., '_sync/') have a corresponding facade file ('sync.py').
    - Python files (potential helpers) are not siblings of facade files unless they are
      the facade itself, __init__.py, or a group definition file (e.g., tools.py).
    """
    violations = []
    processed_facades = set()  # Keep track of facades verified against helper dirs

    # 1. Check for invalid '*_cmd.py' files
    for cmd_file in SUBCOMMANDS_DIR.rglob("*_cmd.py"):
        violations.append(f"Invalid '*_cmd.py' file found (should be renamed): {cmd_file.relative_to(SUBCOMMANDS_DIR)}")

    # 2. Check Python files for proper placement (facade vs. helper)
    for py_file in SUBCOMMANDS_DIR.rglob("*.py"):
        parent = py_file.parent
        relative_path = py_file.relative_to(SUBCOMMANDS_DIR)

        # Ignore files directly inside the base subcommands directory
        if parent == SUBCOMMANDS_DIR:
            continue

        # Ignore files inside correctly named helper directories (e.g., _sync/)
        if parent.name.startswith("_"):
            continue

        # Ignore __init__.py files
        if py_file.name == "__init__.py":
            continue

        # Ignore group definition files (e.g., tools.py inside tools/)
        if py_file.stem == parent.name:
            continue

        # --- At this point, it's potentially a facade file or a misplaced helper ---
        facade_name = py_file.stem
        expected_helper_dir = parent / f"_{facade_name}"
        processed_facades.add(py_file)  # Mark as potentially processed facade

        if not expected_helper_dir.is_dir():
            violations.append(
                f"Potential facade/misplaced helper: '{relative_path}' exists but corresponding helper directory '_{facade_name}/' is missing in '{parent.relative_to(SUBCOMMANDS_DIR)}'."
            )

    # 3. Check helper directories for corresponding facade files
    for helper_dir in SUBCOMMANDS_DIR.rglob("_*"):
        # Ensure it's a directory and directly inside a command group dir
        if not helper_dir.is_dir() or not helper_dir.name.startswith("_") or helper_dir.parent == SUBCOMMANDS_DIR:
            continue

        facade_name = helper_dir.name[1:]  # e.g., 'sync' from '_sync'
        expected_facade_file = helper_dir.parent / f"{facade_name}.py"
        relative_dir_path = helper_dir.relative_to(SUBCOMMANDS_DIR)

        if not expected_facade_file.is_file():
            violations.append(
                f"Helper directory '{relative_dir_path}' exists but corresponding facade file '{facade_name}.py' is missing in '{helper_dir.parent.relative_to(SUBCOMMANDS_DIR)}'."
            )
        # Ensure the corresponding facade file was actually found in the previous loop
        elif expected_facade_file not in processed_facades:
            # This case should be rare if the file loop ran correctly
            violations.append(
                f"Helper directory '{relative_dir_path}' has facade '{expected_facade_file.relative_to(SUBCOMMANDS_DIR)}' but it wasn't identified correctly in the file scan."
            )

    # Final Assertion
    assert not violations, f"Command Facade structure violations found in '{SUBCOMMANDS_DIR}':\n - " + "\n - ".join(
        sorted(violations)
    )
