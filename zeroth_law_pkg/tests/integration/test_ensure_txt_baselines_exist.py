import logging
import os
import pytest
import sys
from pathlib import Path
from typing import Dict, Set, Tuple

# Add src directory to sys.path to allow importing modules from src
# TODO: This might be better handled by packaging or pytest config
src_dir = Path(__file__).resolve().parents[2] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# pylint: disable=import-error,wrong-import-position
from zeroth_law.dev_scripts.reconciliation_logic import (
    ReconciliationError,
    perform_tool_reconciliation,
)
from zeroth_law.dev_scripts.tool_reconciler import ToolStatus

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Determine project root and tool definitions directory relative to this test file
# tests/integration/test_this_file.py -> project_root
# This assumes the tests are run from the project root or the structure is consistent
# tests -> parent -> parent = project_root
PROJECT_ROOT_DIR = Path(__file__).resolve().parents[2]
TOOL_DEFS_DIR = PROJECT_ROOT_DIR / "tool_defs"
BASELINE_DIR = PROJECT_ROOT_DIR / "generated_command_outputs"


def test_ensure_txt_baselines_exist():
    """
    Checks that a .txt baseline file exists in generated_command_outputs
    for every command sequence defined for managed tools.
    """
    logger.info("Starting baseline existence check...")
    if not BASELINE_DIR.is_dir():
        pytest.fail(f"Baseline directory not found: {BASELINE_DIR}")

    # --- Refactored Reconciliation Section ---
    try:
        # Call the helper function to get results and managed tools
        reconciliation_results, managed_tools_for_processing = perform_tool_reconciliation(
            project_root_dir=PROJECT_ROOT_DIR, tool_defs_dir=TOOL_DEFS_DIR
        )
        logger.info(f"Managed tools identified for baseline check: {managed_tools_for_processing}")

    except ReconciliationError as e:
        # Fail the test if reconciliation itself had errors
        pytest.fail(f"Tool reconciliation failed: {e}")
    except FileNotFoundError as e:
        # Fail if necessary inputs (pyproject.toml, tool_defs) were missing
        pytest.fail(f"Required directory or file not found during reconciliation: {e}")
    except Exception as e:
        # Catch any other unexpected errors during reconciliation
        pytest.fail(f"An unexpected error occurred during reconciliation: {e}", pytrace=True)
    # --- End Refactored Section ---

    # --- Logic Using Refactored Results (Mostly Unchanged) ---
    missing_baselines = []
    tools_with_issues = []  # Tools that are managed but might have definition issues

    # Iterate through the managed tools identified by the helper function
    for tool_name in managed_tools_for_processing:
        tool_status = reconciliation_results.get(tool_name)  # Get status from the returned results

        # If the tool is managed but missing from the env, we still expect a baseline
        # generated from the definition. If it's whitelisted but missing defs, skip.
        if tool_status == ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR:
            logger.warning(
                f"Skipping baseline check for whitelisted tool '{tool_name}' - no definition found in {TOOL_DEFS_DIR}"
            )
            continue  # Cannot generate sequences without definition

        tool_def_dir = TOOL_DEFS_DIR / tool_name
        if not tool_def_dir.is_dir():
            # This case should ideally be covered by WHITELISTED_NOT_IN_TOOLS_DIR status check,
            # but kept as a safeguard.
            logger.error(f"Tool '{tool_name}' is managed but definition directory missing: {tool_def_dir}")
            tools_with_issues.append(tool_name)
            continue

        # Assume existence of a function to get command sequences from tool defs
        # (This would likely live in another module, e.g., sequence_generator.py)
        # For now, simulate based on expected baseline filenames
        # A real implementation would parse JSONs etc.
        expected_sequences = find_expected_baseline_sequences(tool_name, tool_def_dir)

        for sequence_tuple, baseline_filename in expected_sequences:
            baseline_path = BASELINE_DIR / baseline_filename
            if not baseline_path.is_file():
                missing_baselines.append(
                    f"Missing baseline for {tool_name} sequence {sequence_tuple}: expected {baseline_path}"
                )
            else:
                logger.debug(f"Found baseline for {tool_name} sequence {sequence_tuple}: {baseline_path}")

    if tools_with_issues:
        pytest.fail(f"Found issues with tool definitions for managed tools: {tools_with_issues}")

    if missing_baselines:
        pytest.fail("Missing baseline files:\\n" + "\\n".join(missing_baselines))
    else:
        logger.info("All expected baseline files found.")


def find_expected_baseline_sequences(tool_name: str, tool_def_dir: Path) -> list[tuple[tuple[str, ...], str]]:
    """
    Placeholder/Simplified function to determine expected baseline filenames
    based on the tool name and its definition directory.
    A real version would parse JSONs/config within tool_def_dir.
    Returns a list of tuples: ((command_part1, ...), baseline_filename.txt)
    """
    # Example: just look for a baseline named after the tool itself
    # In reality, would check for subcommands defined in json files etc.
    sequences = []
    # Assume a base command (tool_name,) always exists
    base_sequence = (tool_name,)
    sequences.append((base_sequence, f"{tool_name}.txt"))

    # Example: check for a hypothetical 'version' subcommand definition
    version_def_file = tool_def_dir / "version.json"  # Hypothetical
    if version_def_file.is_file():  # Simulate finding a definition
        version_sequence = (tool_name, "--version")  # Example sequence
        # Replace special chars for filename
        filename_safe_cmd = "_".join(part.replace("-", "_").strip("_") for part in version_sequence)
        sequences.append((version_sequence, f"{filename_safe_cmd}.txt"))

    # Add more complex logic here based on actual tool definition structure
    # e.g., iterating over *.json files in tool_def_dir

    return sequences


# Helper function placeholder to parse tool definitions (e.g., JSON files)
# This would contain the logic to extract command sequences
# def get_command_sequences_for_tool(tool_name: str, tool_def_dir: Path) -> list[tuple[str, ...]]:
#     # Actual implementation would go here
#     # For now, return dummy data or use find_expected_baseline_sequences
#     pass

# Example of how the test might look if fully implemented:
# def test_ensure_txt_baselines_exist_fully_implemented():
# ... (setup and reconciliation as above) ...
# managed_tools = ... result from reconciliation ...
# all_sequences = []
# for tool_name in managed_tools:
#     tool_def_dir = TOOL_DEFS_DIR / tool_name
#     if tool_def_dir.is_dir(): # Or rely on reconciliation status
#          sequences = get_command_sequences_for_tool(tool_name, tool_def_dir) # Real function
#          all_sequences.extend([(tool_name, seq) for seq in sequences])
#     else:
#         # Handle missing def dir if needed (e.g., log warning)
#         pass
# Check baselines for all_sequences...
