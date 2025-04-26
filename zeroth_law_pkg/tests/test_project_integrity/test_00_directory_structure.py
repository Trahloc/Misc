# FILE: tests/test_project_integrity/test_00_directory_structure.py
# PURPOSE: Ensure that no tool directory contains 'json' or 'txt' subdirectories.
#          Files should reside directly within the tool's main directory.

import pytest
from pathlib import Path
import sys

# --- Calculate paths relative to the new file location --- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = PROJECT_ROOT / "src" / "zeroth_law" / "tools"
WORKSPACE_ROOT = PROJECT_ROOT  # In this context, PROJECT_ROOT is the workspace root

# Remove the problematic import attempt for now
# try:
#     # Assuming tool_discovery.py is importable via src layout or installation
#     from src.zeroth_law.dev_scripts.tool_discovery import TOOLS_DIR, WORKSPACE_ROOT
# except ImportError as e:
#     print(f"Error importing modules. Check PYTHONPATH and file locations. Details: {e}", file=sys.stderr)
#     # If we can't import TOOLS_DIR, we can't run the test effectively.
#     # Define it manually relative to this file for resilience, though this is not ideal.
#     TOOLS_DIR = Path(__file__).resolve().parents[1] / "src" / "zeroth_law" / "tools"
#     WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
#     print(f"Falling back to manually defined TOOLS_DIR: {TOOLS_DIR}", file=sys.stderr)


def test_no_json_or_txt_subdirectories():
    """
    Verify that no direct subdirectory under TOOLS_DIR contains
    a subdirectory named 'json' or 'txt'.
    """
    if not TOOLS_DIR.is_dir():
        pytest.fail(f"Base tools directory not found: {TOOLS_DIR}")

    found_invalid_structure = False
    error_messages = []

    for item in TOOLS_DIR.iterdir():
        if item.is_dir():  # It's a tool directory (e.g., tools/ruff/)
            tool_name = item.name
            relative_tool_dir = item.relative_to(WORKSPACE_ROOT)

            # Check for 'json' subdirectory
            json_subdir = item / "json"
            if json_subdir.is_dir():
                found_invalid_structure = True
                error_messages.append(
                    f"Invalid subdirectory found: '{relative_tool_dir / 'json'}'. "
                    f".json files should be directly in '{relative_tool_dir}'."
                )

            # Check for 'txt' subdirectory
            txt_subdir = item / "txt"
            if txt_subdir.is_dir():
                found_invalid_structure = True
                error_messages.append(
                    f"Invalid subdirectory found: '{relative_tool_dir / 'txt'}'. "
                    f".txt files should be directly in '{relative_tool_dir}'."
                )

    if found_invalid_structure:
        pytest.fail("\n".join(error_messages))
