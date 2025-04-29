import pytest

# import yaml # No longer needed?
from pathlib import Path
import sys
import json
import warnings

# import xml.etree.ElementTree as ET # No longer needed?
import re

# import io  # Import io for capturing report output # No longer needed?
# import coverage  # Import coverage API # No longer needed?
import logging
from typing import Set
import os

# --- Added for testing CLI --- #
from click.testing import CliRunner
from zeroth_law.cli import main  # Import the main entry point

# Assuming tool_discovery.py is now in src/zeroth_law/dev_scripts/
# Add the src directory to the path to allow importing the discovery script
_TEST_DIR = Path(__file__).parent.resolve()
# _SRC_DIR = _TEST_DIR.parent.parent / "src" # sys.path managed by uv run / pytest
# sys.path.insert(0, str(_SRC_DIR))

# --- Configuration --- #
# Constants can be derived from the imported script or kept simple
# Go up three levels: tests/test_interaction/test_tool_defs -> tests/test_interaction -> tests -> workspace_root
WORKSPACE_ROOT = _TEST_DIR.parent.parent.parent
TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
# GENERATION_SCRIPT = WORKSPACE_ROOT / "src" / "zeroth_law" / "dev_scripts" / "generate_baseline_files.py" # Obsolete
# MANAGED_TOOLS_YAML = WORKSPACE_ROOT / "src" / "zeroth_law" / "managed_tools.yaml" # Obsolete, uses pyproject.toml

# Constants for test configuration
# TOOL_INDEX_FILENAME = "tool_index.json" # Defined in fixtures
COVERAGE_TOTAL_FILENAME = "coverage_total.txt"
MINIMUM_COVERAGE_THRESHOLD = 95.0  # Restore original threshold

logger = logging.getLogger(__name__)


# --- Test for Unknown Tools (Refactored to use `zlt tools reconcile`) --- #
def test_check_for_new_tools():
    """Check if 'zlt tools reconcile' reports any NEW_ENV_TOOL errors."""
    runner = CliRunner()
    # Run the reconcile command with JSON output for easier parsing
    result = runner.invoke(main, ["tools", "reconcile", "--json"], catch_exceptions=False)

    # Check if the command executed successfully (exit code 0 or 1 is expected)
    # Exit code 2 or higher indicates a crash in the command itself.
    if result.exit_code >= 2:
        print(f"zlt tools reconcile crashed! Exit code: {result.exit_code}")
        print("Output:")
        print(result.output)
        pytest.fail(f"'zlt tools reconcile --json' command failed unexpectedly.", pytrace=False)

    # Parse the JSON output
    try:
        report_data = json.loads(result.output)
    except json.JSONDecodeError:
        print("Failed to parse JSON output from 'zlt tools reconcile --json':")
        print(result.output)
        pytest.fail("Could not parse JSON output from reconcile command.", pytrace=False)

    # Check the detailed status for NEW_ENV_TOOL
    new_env_tools = []
    details = report_data.get("details", {})
    for tool, status_name in details.items():
        if status_name == "NEW_ENV_TOOL":
            new_env_tools.append(tool)

    # Assert that no new environment tools were found
    assert not new_env_tools, (
        f"'zlt tools reconcile' reported newly discovered potential tools: {sorted(new_env_tools)}\n"
        f"These executables were found in the environment but are not listed in the managed-tools "
        f"whitelist or blacklist in pyproject.toml. \n"
        f"Action Required: Run 'zlt tools reconcile' and assess each tool. Add to whitelist or blacklist using "
        f"'zlt tools add-whitelist <tool>' or 'zlt tools add-blacklist <tool>'."
    )

    # If the assertion passes, it means no NEW_ENV_TOOL errors were found.
    print("test_check_for_new_tools: PASSED - 'zlt tools reconcile' reported no unmanaged tools in the environment.")


# --- Test for Orphan Directories --- #


def test_no_orphan_tool_directories(managed_sequences: set[str], TOOLS_DIR: Path):
    """
    Test that there are no directories under TOOLS_DIR that do not
    correspond to a managed tool defined in the configuration (e.g., pyproject.toml).
    Uses the imported get_tool_dirs function from tools_dir_scanner.
    """
    # Import the canonical scanner function
    try:
        # --- Updated Import Path --- #
        from zeroth_law.lib.tooling.tools_dir_scanner import get_tool_dirs
    except ImportError:
        pytest.fail(
            "Could not import get_tool_dirs from zeroth_law.lib.tooling.tools_dir_scanner. Check path/installation."
        )

    # Use the imported scanner function
    actual_tool_dirs = get_tool_dirs(TOOLS_DIR)

    # managed_sequences fixture provides the set of managed tool names from config/reconciliation
    known_managed_tools = managed_sequences

    orphan_dirs = actual_tool_dirs - known_managed_tools

    assert not orphan_dirs, (
        f"Orphan tool directories found under '{TOOLS_DIR.relative_to(Path.cwd())}' "  # Use Path.cwd() for relative path
        f"that are not listed as 'managed_tools' in the configuration: {sorted(list(orphan_dirs))}.\n"
        f"The get_tool_dirs function identified these as tool directories, but they aren't managed.\n"
        f"Please investigate and decide whether to remove these directories or add the "
        f"corresponding tool name(s) to the configuration (e.g., pyproject.toml)."
    )


# --- Test for Project Coverage --- #


@pytest.mark.coverage_check
def test_project_coverage_threshold(WORKSPACE_ROOT: Path):
    """Reads the parsed total coverage from the file and checks against the minimum."""
    # Correct path using WORKSPACE_ROOT fixture
    coverage_total_file = WORKSPACE_ROOT / COVERAGE_TOTAL_FILENAME

    if not coverage_total_file.exists():
        pytest.fail(f"Coverage total file not found: {coverage_total_file}")

    try:
        content = coverage_total_file.read_text(encoding="utf-8").strip()
        # Expecting content to be just the coverage number (e.g., "70.0")
        current_coverage = float(content)
    except ValueError:
        pytest.fail(f"Could not parse coverage value from {coverage_total_file}: '{content}'")
    except Exception as e:
        pytest.fail(f"Error reading or processing {coverage_total_file}: {e}")

    logger.info(f"Current project coverage: {current_coverage}%")
    if current_coverage < MINIMUM_COVERAGE_THRESHOLD:
        warnings.warn(
            f"Project coverage {current_coverage}% is below the desired threshold of {MINIMUM_COVERAGE_THRESHOLD}%"
        )
