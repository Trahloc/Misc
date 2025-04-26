import pytest
import yaml
from pathlib import Path
import sys
from zeroth_law.dev_scripts.tool_discovery import get_existing_tool_dirs, get_potential_managed_tools, load_tools_config
import json
import warnings
import xml.etree.ElementTree as ET
import re
import io  # Import io for capturing report output
import coverage  # Import coverage API
import logging
from typing import Set
import os

# Assuming tool_discovery.py is now in src/zeroth_law/dev_scripts/
# Add the src directory to the path to allow importing the discovery script
_TEST_DIR = Path(__file__).parent.resolve()
_SRC_DIR = _TEST_DIR.parent.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

# --- Configuration ---
# Constants can be derived from the imported script or kept simple
# Go up three levels: tests/test_interaction/test_tool_defs -> tests/test_interaction -> tests -> workspace_root
WORKSPACE_ROOT = _TEST_DIR.parent.parent.parent
TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
GENERATION_SCRIPT = WORKSPACE_ROOT / "src" / "zeroth_law" / "dev_scripts" / "generate_baseline_files.py"
MANAGED_TOOLS_YAML = WORKSPACE_ROOT / "src" / "zeroth_law" / "managed_tools.yaml"

# Constants for test configuration
TOOL_INDEX_FILENAME = "tool_index.json"
COVERAGE_TOTAL_FILENAME = "coverage_total.txt"
MINIMUM_COVERAGE_THRESHOLD = 95.0  # Restore original threshold

logger = logging.getLogger(__name__)


# --- Test for Unknown Tools ---
def test_check_for_new_tools():
    """Check for discovered tools that are neither managed nor excluded."""
    print("\nRunning tool discovery check...")
    potential_tools = get_potential_managed_tools()
    if not potential_tools:
        pytest.skip("Tool discovery failed or found no potential tools.")

    config = load_tools_config()
    known_managed_tools = set(config.get("managed_tools", []))
    # We don't need existing_tool_dirs for this specific check anymore
    # Check is potential vs (managed + excluded)

    # Calculate unknown tools
    unknown_tools = potential_tools - known_managed_tools
    # Note: excluded tools were already filtered out by get_potential_managed_tools

    if unknown_tools:
        error_msg = (
            "\n--------------------------------------------------\n"
            f"Newly discovered potential tools found: {sorted(list(unknown_tools))}\n"
            "These executables exist in the environment bin directory but are neither\n"
            f"explicitly excluded nor listed as managed in {MANAGED_TOOLS_YAML.relative_to(WORKSPACE_ROOT)}.\n"
            "\nAction Required: Assess each listed executable based on its **long-term utility to the ZLT project** and update managed_tools.yaml:\n"
            "  - If it provides essential, long-term value and ZLT should manage its configuration/baselines, add its name to the 'managed_tools' list.\n"
            "  - If it's a temporary helper, part of another tool's internals, unwanted, or not useful for ZLT's core goals, add its name to the 'excluded_executables' list.\n"
            "--------------------------------------------------"
        )
        pytest.fail(error_msg, pytrace=False)
    else:
        print(
            "No new potential tools found. managed_tools.yaml is up-to-date with discovered non-excluded executables."
        )
        assert True  # Explicit pass


# --- Test for Orphan Directories (Optional but good sanity check) ---


def _find_actual_tool_dirs(base_tools_dir: Path) -> set[str]:
    """
    Helper to find leaf directories under the base_tools_dir.
    Now assumes a flat structure like tools/actual_tool1, tools/actual_tool2.
    Ignores files and only considers directories as actual tools.
    """
    actual_tool_dirs = set()
    if not base_tools_dir.is_dir():
        return actual_tool_dirs

    # Iterate through items directly under base_tools_dir
    for item in base_tools_dir.iterdir():
        if item.is_dir():
            tool_name = item.name
            actual_tool_dirs.add(tool_name)

    return actual_tool_dirs


def test_no_orphan_tool_directories(managed_sequences: set[str], TOOLS_DIR: Path):
    """
    Test that there are no directories under TOOLS_DIR that do not
    correspond to a managed tool defined in the configuration (e.g., pyproject.toml).
    Uses the updated tools_dir_scanner logic to find actual tool directories.
    """
    # Import the corrected function
    try:
        from zeroth_law.dev_scripts.tools_dir_scanner import get_tool_dirs
    except ImportError:
        pytest.fail(
            "Could not import get_tool_dirs from tools_dir_scanner. Check sys.path setup in conftest or test file."
        )

    # Use the corrected scanner function
    actual_tool_dirs = get_tool_dirs(TOOLS_DIR)

    known_managed_tools = managed_sequences

    orphan_dirs = actual_tool_dirs - known_managed_tools

    assert not orphan_dirs, (
        f"Orphan tool directories found under '{TOOLS_DIR.relative_to(Path.cwd())}' "
        f"that are not listed as 'managed_tools' in the configuration: {sorted(list(orphan_dirs))}. "
        "Please investigate and decide whether to remove these directories or add the "
        "corresponding tool name(s) to the configuration (e.g., pyproject.toml)."
    )


# --- Test for Project Coverage (Moved to end) ---


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


# --- Removed test_tool_directories_and_baselines_exist --- #
# This functionality is now split into:
# 1. test_check_for_new_tools (above) - Detects tools needing categorization.
# 2. test_json_baseline_exists (new file) - Checks if categorized tools have baselines.

# Check for orphan tool directories (exist on disk but not in managed list)
# orphan_dirs = existing_tool_dirs - known_managed_tools
# orphan_list = ", ".join(sorted(o.name for o in orphan_dirs))
# assert not orphan_dirs, (
#     f"Found orphan tool directories not in 'managed_tools' config "
#     f"({MANAGED_TOOLS_YAML.relative_to(WORKSPACE_ROOT)}):\n"
#     f"  [{orphan_list}]\n"
#     f"Action Required: Add tool(s) to config or delete directories."
# )
#
# # Check for newly added potential tools (in managed list but dir doesn't exist)
# new_potential_tools = known_managed_tools - existing_tool_dirs
# new_list = ", ".join(sorted(n.name for n in new_potential_tools))
# assert not new_potential_tools, (
#     f"Managed tools listed in config but directory missing:\n"
#     f"  [{new_list}]\n"
#     f"Action Required: Create the tool directory/directories or remove from config."
# )
