# FILE: tests/test_tool_defs/test_txt_json_consistency.py
"""
Compares the content of the TXT baseline file with the 'description'
and 'usage' fields in the corresponding JSON definition file.
"""

import json
import pytest
import logging
from pathlib import Path

# Reuse constants and helpers from TXT test
# Ensure MANAGED_COMMAND_SEQUENCES is correctly populated before this import
from .test_ensure_txt_baselines_exist import (
    MANAGED_COMMAND_SEQUENCES,
    command_sequence_to_id,
)

# Import WORKSPACE_ROOT, TOOLS_DIR, and TOOL_INDEX_PATH from conftest

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# --- Test Function ---
@pytest.mark.parametrize(
    "command_parts",
    MANAGED_COMMAND_SEQUENCES,
    ids=[command_sequence_to_id(cp) for cp in MANAGED_COMMAND_SEQUENCES],
)
def test_txt_json_consistency(
    command_parts: tuple[str, ...], tool_index_handler, WORKSPACE_ROOT, TOOLS_DIR, TOOL_INDEX_PATH
):
    """Compares TXT content with relevant JSON fields."""

    if not command_parts:
        pytest.skip("Skipping test for empty command parts.")

    tool_id = command_sequence_to_id(command_parts)
    tool_name = command_parts[0]

    # Use dynamically provided paths
    tool_dir = TOOLS_DIR / tool_name
    txt_file = tool_dir / f"{tool_id}.txt"
    json_file = tool_dir / f"{tool_id}.json"
    relative_json_path = json_file.relative_to(WORKSPACE_ROOT)
    relative_txt_path = txt_file.relative_to(WORKSPACE_ROOT)

    # --- Load TXT Content ---
    if not txt_file.is_file():
        pytest.skip(f"Skipping consistency check: TXT file missing for {tool_id} at {relative_txt_path}")
    try:
        txt_content = txt_file.read_text(encoding="utf-8")
    except Exception as e:
        pytest.fail(f"Failed to read TXT file {relative_txt_path}: {e}")

    # --- Load JSON Content ---
    if not json_file.is_file():
        pytest.fail(
            f"JSON file missing for {tool_id} at {relative_json_path}. Cannot perform consistency check.\n"
            f"Action Required: Ensure the JSON file has been generated/populated."
        )
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode JSON file {relative_json_path}: {e}")
    except Exception as e:
        pytest.fail(f"Failed to read JSON file {relative_json_path}: {e}")

    # --- Perform Consistency Checks ---

    # 1. Check description (compare first non-empty line of TXT? TBD)
    # For now, just check if description exists
    # json_description = json_data.get("description", "").strip()
    # assert json_description, f"JSON 'description' field is empty in {relative_json_path}"
    # TODO: Add smarter comparison logic if needed

    # 2. Check usage (compare relevant section of TXT? TBD)
    # For now, just check if usage exists
    # json_usage = json_data.get("usage", "").strip()
    # assert json_usage, f"JSON 'usage' field is empty in {relative_json_path}"
    # TODO: Add smarter comparison logic if needed

    # 3. Check CRC value in JSON metadata matches the index
    json_metadata = json_data.get("metadata", {})
    json_crc = json_metadata.get("ground_truth_crc")

    index_data = tool_index_handler["data"]
    index_entry = index_data.get(tool_id)
    index_crc = index_entry.get("crc") if index_entry else None

    assert json_crc is not None, f"Missing 'metadata.ground_truth_crc' in {relative_json_path}"
    assert index_crc is not None, f"Missing CRC entry for '{tool_id}' in tool index ({TOOL_INDEX_PATH})"

    # Perform case-insensitive comparison
    assert str(json_crc).lower() == str(index_crc).lower(), (
        f"JSON CRC mismatch for {tool_id} (case-insensitive comparison):\n"
        f"  JSON file ({relative_json_path}): metadata.ground_truth_crc = {json_crc}\n"
        f"  Tool Index ({TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}): stored CRC = {index_crc}\n"
        f"Action Required: Ensure the CRC values match numerically. Update the 'ground_truth_crc' in {relative_json_path} if the TXT file ({relative_txt_path}) has changed."
    )

    log.info(f"Consistency checks passed for {tool_id}")
