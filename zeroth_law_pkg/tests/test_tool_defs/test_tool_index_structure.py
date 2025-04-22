# FILE: tests/test_tool_defs/test_tool_index_structure.py
"""
Tests the structure of tool_index.json for consistency.

Specifically checks for redundant top-level entries that correspond to
commands already defined as nested subcommands within a parent tool entry.
"""

import pytest
import json
import logging
from pathlib import Path

# Setup logger for this test module
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import fixtures from top-level conftest
from tests.conftest import TOOLS_DIR, ZLT_ROOT

# Import helper from sibling test module
from .test_ensure_txt_baselines_exist import command_sequence_to_id


def test_no_redundant_top_level_subcommand_entries(tool_index_handler, WORKSPACE_ROOT, TOOL_INDEX_PATH):
    """
    Checks if any top-level key in tool_index.json corresponds to a command
    that is already defined as a nested subcommand within another entry.
    E.g., Fails if 'ruff_analyze' exists at the top level AND 'analyze'
    is defined within the 'subcommands' dictionary of the 'ruff' entry.
    """
    # Get the index data using the handler's method
    index_data = tool_index_handler.get_raw_index_data()
    redundant_entries = []

    # Find all defined nested subcommands: set of (parent_name, sub_name)
    nested_subcommands = set()
    for tool_name, entry in index_data.items():
        if isinstance(entry, dict) and "subcommands" in entry:
            sub_dict = entry.get("subcommands")
            if isinstance(sub_dict, dict):
                for sub_name in sub_dict.keys():
                    nested_subcommands.add((tool_name, sub_name))

    # Check if any top-level key matches a known nested subcommand definition
    for parent_name, sub_name in nested_subcommands:
        # Construct the ID that a top-level entry for this subcommand *would* have
        # based on the standard naming convention used elsewhere (e.g., ruff_analyze)
        potential_redundant_id = command_sequence_to_id((parent_name, sub_name))

        # Check if this potentially redundant ID exists as a top-level key
        if potential_redundant_id in index_data:
            redundant_entries.append(f"'{potential_redundant_id}' (subcommand '{sub_name}' of '{parent_name}')")

    # Assert that no redundant entries were found
    if redundant_entries:
        fail_message = (
            f"Redundant top-level entries found in tool_index.json "
            f"({TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}). "
            f"These entries correspond to commands already defined as nested subcommands:\\n"
            f"  - {', '.join(redundant_entries)}\\n"
            f"Action Required: Remove these redundant top-level entries from the tool index. "
            f"The nested definition under the parent tool should be the source of truth."
        )
        pytest.fail(fail_message)
    else:
        log.info("Tool index structure check passed: No redundant top-level subcommand entries found.")
