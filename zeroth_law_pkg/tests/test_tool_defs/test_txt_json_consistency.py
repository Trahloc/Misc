# FILE: tests/test_tool_defs/test_txt_json_consistency.py
"""
Tests that the ground_truth_crc stored *within* a JSON definition file
matches the CRC stored in the central tool index (tool_index.json).

It effectively triggers AI action when the ground truth TXT changes (affecting the index)
or when a JSON file lacks the ground_truth_crc (indicating it's a skeleton or corrupted).
"""

import json
import logging
import pytest

# Need these core paths as well
from zeroth_law.dev_scripts.tool_discovery import (
    TOOLS_DIR,
    WORKSPACE_ROOT,
)

# Reuse helpers and fixture from the TXT baseline test
from .test_ensure_txt_baselines_exist import (
    MANAGED_COMMAND_SEQUENCES,
    TOOL_INDEX_PATH,  # Need the path for context in messages
    command_sequence_to_id,  # Explicitly import if needed, though fixture use is implicit
)

# Import the helper from the new utils file
# from .test_json_is_populated import is_likely_skeleton

# --- Constants ---
DEFAULT_ENCODING = "utf-8"
SCHEMA_GUIDELINES_PATH = "tools/zlt_schema_guidelines.md"  # Relative to workspace

# --- Logging ---
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%s - %(levelname)s - %(message)s")


# --- Test Function ---
@pytest.mark.parametrize("command_parts", MANAGED_COMMAND_SEQUENCES, ids=command_sequence_to_id)
def test_json_crc_matches_index(command_parts: tuple[str, ...], tool_index_handler):
    """
    Verifies that the metadata.ground_truth_crc in a JSON file exists and matches the index crc.
    Fails if ground_truth_crc is missing or if the CRCs mismatch.
    """
    if not command_parts:
        pytest.skip("Skipping test for empty command parts.")

    tool_id = command_sequence_to_id(command_parts)
    tool_name = command_parts[0]

    # Paths for context
    tool_dir = TOOLS_DIR / tool_name
    json_file = tool_dir / f"{tool_id}.json"
    relative_json_path = json_file.relative_to(WORKSPACE_ROOT)
    relative_txt_path = (tool_dir / f"{tool_id}.txt").relative_to(WORKSPACE_ROOT)
    relative_index_path = TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)

    # --- Get Expected CRC from Index ---
    index_data = tool_index_handler["data"]
    index_entry = index_data.get(tool_id)
    if not index_entry or "crc" not in index_entry:
        pytest.fail(
            f"CRC entry missing in tool_index.json for '{tool_id}'.\n"
            f"Action Required: Run test_ensure_txt_baselines_exist.py or generate_baseline_cli.py for this tool first."
        )
    expected_index_crc = index_entry["crc"]

    # --- Check if JSON File Exists ---
    if not json_file.is_file():
        pytest.fail(
            f"JSON definition file does not exist: {relative_json_path}\n"
            f"Action Required: Run generate_baseline_cli.py --command {' '.join(command_parts)} to create the skeleton."
        )

    # --- Load JSON and Check Metadata/CRC ---
    json_data = None
    try:
        with open(json_file, "r", encoding=DEFAULT_ENCODING) as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Failed to decode JSON file: {relative_json_path}\n"
            f"Error: {e}\n"
            f"Action Required: Manually inspect and fix the JSON syntax."
        )
    except Exception as e:
        pytest.fail(f"Failed to read JSON file: {relative_json_path}\nError: {e}")

    # Check metadata structure
    metadata = json_data.get("metadata")
    if not isinstance(metadata, dict):
        pytest.fail(
            f"JSON file is missing the top-level 'metadata' dictionary: {relative_json_path}\n"
            f"Action Required: Ensure the JSON structure is correct. It should contain at least `metadata: {{}}`. "
            f"Skeletons have empty metadata, populated files need `metadata: {{ 'ground_truth_crc': '...' }}`."
        )

    # Check for ground_truth_crc
    json_ground_truth_crc = metadata.get("ground_truth_crc")

    if json_ground_truth_crc is None:
        # Fail if the key is missing entirely
        pytest.fail(
            f"Failed: JSON is missing `metadata.ground_truth_crc`: {relative_json_path}\n"
            f"This key must exist and match the tool index.\n"
            f"Action Required: Populate the JSON file or regenerate the baseline/skeleton."
        )

    # Compare CRCs (case-insensitive) - This is the core check.
    if json_ground_truth_crc.lower() != expected_index_crc.lower():
        pytest.fail(
            f"JSON CRC mismatch for '{tool_id}': Stored='{json_ground_truth_crc}', Expected (from index)='{expected_index_crc}'\\n"
            f"File: {relative_json_path}\\n"
            f"Reason: The ground-truth TXT file has likely changed, or the JSON CRC is incorrect.\\n"
            f"AI Action Required: You MUST personally re-read the ground-truth file:\\n"
            f"  {relative_txt_path}\\n"
            f"Then, update the content of the JSON file ({json_file.name}) "
            f"according to the guidelines in:\\n"
            f"  {SCHEMA_GUIDELINES_PATH}\\n"
            f"Ensure `metadata.ground_truth_crc` is updated to `{expected_index_crc}` after updating content."
        )

    # If we reach here, ground_truth_crc exists and matches the index crc
    log.info(f"CRC check passed for JSON: {relative_json_path} (CRC: {expected_index_crc})")
    assert True  # Explicit pass
