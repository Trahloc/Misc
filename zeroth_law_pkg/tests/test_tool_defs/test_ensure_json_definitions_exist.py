# FILE: tests/test_tool_defs/test_ensure_json_definitions_exist.py
"""
Tests that a high-trust JSON definition file exists for every managed
tool/subcommand defined in managed_tools.yaml.

This test DOES NOT generate missing JSON files. It relies on a separate
process (likely AI-driven) to create the JSON based on the corresponding
ground-truth TXT file.
"""

import pytest
import logging  # Import logging
from pathlib import Path  # Import Path
import os
import sys
from typing import Tuple, List

# Add src directory to sys.path
# ... (sys.path logic) ...

# Setup logger for this test module
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # Configure as needed

# Import necessary fixtures/functions from elsewhere (e.g., conftest)
from .conftest import command_sequence_to_id  # Keep this if needed

# Assuming TOOL_DEFS_DIR_FIXTURE is available from conftest


def test_ensure_json_files_exist_for_sequences(managed_sequences: List[Tuple[str, ...]], TOOL_DEFS_DIR_FIXTURE: Path):
    """Check if a corresponding .json definition exists for each managed sequence."""
    log.info(f"Checking for JSON definition existence for {len(managed_sequences)} sequences...")
    if not managed_sequences:
        pytest.skip("No managed sequences provided by the fixture.")

    missing_json_files = []
    tool_defs_dir = TOOL_DEFS_DIR_FIXTURE

    for sequence_tuple in managed_sequences:
        tool_id = command_sequence_to_id(sequence_tuple)
        tool_name = sequence_tuple[0]
        expected_json_path = tool_defs_dir / tool_name / f"{tool_id}.json"

        if not expected_json_path.is_file():
            missing_json_files.append(
                f"Missing JSON for sequence {' '.join(sequence_tuple)}: expected {expected_json_path}"
            )
        else:
            log.debug(f"Found expected JSON: {expected_json_path}")

    if missing_json_files:
        pytest.fail("Missing JSON definition files:\n" + "\n".join(missing_json_files))
    else:
        log.info("All expected JSON definition files found.")


# You might have other tests in this file that also need the fixture
