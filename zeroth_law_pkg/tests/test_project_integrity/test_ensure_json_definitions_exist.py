# FILE: tests/test_zeroth_law/test_tool_defs/test_ensure_json_definitions_exist.py
"""
Tests to ensure that for every managed tool sequence, a corresponding .json
definition file exists in the expected location within the tools directory.
Relies on fixtures from the root conftest.py for managed sequences and directories.
"""

import pytest
import logging
from pathlib import Path

# Removed outdated relative import:
# from .conftest import command_sequence_to_id  # Keep this if needed
# The command_sequence_to_id function is now in the root conftest and used by fixtures.
# The necessary fixtures (managed_sequences, TOOLS_DIR) are session-scoped and automatically provided.

log = logging.getLogger(__name__)


# Remove parametrization - iterate inside the test function
# @pytest.mark.parametrize("command_sequence", "managed_sequences")
def test_json_definition_exists_for_managed_tool(managed_sequences: set[str], TOOLS_DIR: Path):
    """Verify that a .json definition file exists for each managed tool name."""

    if not managed_sequences:
        pytest.skip("No managed tool names provided by the fixture.")

    missing_files = []
    for tool_name in managed_sequences:
        # Assume sequence is just the tool name for now
        command_sequence = (tool_name,)

        # Helper to get ID
        def _command_sequence_to_id(parts: tuple[str, ...]) -> str:
            return "_".join(parts) if parts else "_EMPTY_"

        tool_id = _command_sequence_to_id(command_sequence)
        # tool_name is already available
        expected_dir = TOOLS_DIR / tool_name
        expected_json_path = expected_dir / f"{tool_id}.json"

        log.debug(f"Checking for JSON definition: {expected_json_path}")

        if not expected_dir.is_dir():
            missing_files.append(f"Tool directory missing for '{tool_name}': Expected {expected_dir}")
            continue  # Skip file check if dir is missing

        if not expected_json_path.is_file():
            missing_files.append(f"JSON definition missing for '{tool_name}': Expected {expected_json_path}")

    assert not missing_files, "\n".join(["Missing expected JSON definition files or directories:"] + missing_files)


# <<< ZEROTH LAW FOOTER >>>
