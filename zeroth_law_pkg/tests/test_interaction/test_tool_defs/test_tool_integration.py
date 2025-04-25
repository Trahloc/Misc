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

# Assuming tool_discovery.py is now in src/zeroth_law/dev_scripts/
# Add the src directory to the path to allow importing the discovery script
_TEST_DIR = Path(__file__).parent.resolve()
_SRC_DIR = _TEST_DIR.parent.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

# --- Configuration ---
# Constants can be derived from the imported script or kept simple
WORKSPACE_ROOT = _TEST_DIR.parent  # Assuming tests/ is one level down from workspace root
TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
GENERATION_SCRIPT = WORKSPACE_ROOT / "src" / "zeroth_law" / "dev_scripts" / "generate_baseline_files.py"
MANAGED_TOOLS_YAML = WORKSPACE_ROOT / "src" / "zeroth_law" / "managed_tools.yaml"


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
def test_no_orphan_tool_directories():
    """
    Verify that all directories in the tools directory correspond to
    tools listed as managed in managed_tools.yaml.
    """
    if not TOOLS_DIR.is_dir():
        pytest.skip(f"Base tools directory not found: {TOOLS_DIR}")
        return

    existing_tool_dirs = get_existing_tool_dirs()
    config = load_tools_config()
    known_managed_tools = set(config.get("managed_tools", []))

    # Find dirs that exist but aren't listed as managed
    orphan_dirs = existing_tool_dirs - known_managed_tools

    if orphan_dirs:
        orphan_list = ", ".join(sorted(list(orphan_dirs)))
        error_message = (
            f"Orphan tool directories found in '{TOOLS_DIR.relative_to(WORKSPACE_ROOT)}' that are not listed in 'managed_tools' in {MANAGED_TOOLS_YAML.relative_to(WORKSPACE_ROOT)}: [{orphan_list}]. "
            f"Please investigate and decide whether to remove these directories or add the corresponding tool name(s) to the 'managed_tools' list in the YAML config."
        )
        pytest.fail(error_message, pytrace=False)
    else:
        print("No orphan tool directories found.")
        assert True  # Explicit pass


# --- Test for Project Coverage (Moved to end) ---

# Define constants for the test
MIN_PROJECT_COVERAGE = 95.0  # ZLF Requirement
MIN_FILE_COVERAGE = 95.0
COVERAGE_HIGHLIGHT_FILE = WORKSPACE_ROOT / "coverage_lowlights.json"
COVERAGE_TOTAL_FILENAME = "coverage_total.txt"


@pytest.mark.coverage_check
def test_project_coverage_threshold():
    """Reads the parsed total coverage from the file and checks against the minimum."""
    coverage_total_file = WORKSPACE_ROOT / COVERAGE_TOTAL_FILENAME

    if not coverage_total_file.exists():
        pytest.fail(f"Coverage total file not found: {coverage_total_file}")

    try:
        with open(coverage_total_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            parsed_total_coverage = float(content)
    except (IOError, ValueError) as e:
        pytest.fail(f"Could not read or parse coverage total from {coverage_total_file}: {e}")

    print(f"Minimum required project coverage: {MIN_PROJECT_COVERAGE}%")
    print(f"Actual project coverage (from {COVERAGE_TOTAL_FILENAME}): {parsed_total_coverage}%")

    if parsed_total_coverage < MIN_PROJECT_COVERAGE:
        # Use pytest.fail to make it a hard failure, but provide guidance
        fail_message = (
            f"Threshold Check Failed: Project coverage is {parsed_total_coverage:.1f}%, "
            f"below minimum requirement of {MIN_PROJECT_COVERAGE:.1f}%.\n"
            "To investigate:\n"
            "  1. Ensure coverage data is generated: run 'uv run python -m zeroth_law.dev_scripts.run_coverage'\n"
            "  2. Generate the detailed report: run 'uv run coverage report -m'\n"
            "  3. Identify files/lines marked as 'Missing' in the report.\n"
            "  4. Add tests to cover these specific lines/branches.\n"
            "  5. Rerun 'uv run python -m zeroth_law.dev_scripts.run_coverage' to confirm improvement."
        )
        pytest.fail(fail_message, pytrace=False)  # Keep pytrace=False for cleaner output
    else:
        # If coverage is sufficient, maybe just print a success message?
        print(f"Project coverage {parsed_total_coverage}% meets or exceeds minimum {MIN_PROJECT_COVERAGE}%.")


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
