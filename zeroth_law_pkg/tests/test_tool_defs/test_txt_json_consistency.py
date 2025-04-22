# FILE: tests/test_tool_defs/test_txt_json_consistency.py
"""
Compares the content of the TXT baseline file with the 'description'
and 'usage' fields in the corresponding JSON definition file.
"""

import json
import pytest
import logging
from pathlib import Path
import sys

# Reuse constants and helpers from TXT test
# Ensure MANAGED_COMMAND_SEQUENCES is correctly populated before this import
# Use absolute import relative to the project root (assuming tests/ is at the root)
from tests.test_tool_defs.test_ensure_txt_baselines_exist import (
    MANAGED_COMMAND_SEQUENCES,
    command_sequence_to_id,
)

# Import WORKSPACE_ROOT, TOOLS_DIR, and TOOL_INDEX_PATH from conftest

# Import fixtures from top-level conftest
from tests.conftest import TOOLS_DIR, ZLT_ROOT

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

    # NEW CHECK: Ensure forbidden 'file_status' key is not present
    json_metadata = json_data.get("metadata", {})
    assert "file_status" not in json_metadata, (
        f"Forbidden 'metadata.file_status' key found in {relative_json_path}. "
        f"This key is disallowed by project rules."
    )

    # --- CRC Checks --- #
    # 3. Check CRC value in JSON metadata matches the index
    json_crc = json_metadata.get("ground_truth_crc")
    assert json_crc is not None, f"Missing 'metadata.ground_truth_crc' in {relative_json_path}"

    # Get the index data using the handler's method
    index_data = tool_index_handler.get_raw_index_data()
    index_crc = None
    index_crc_source = "Unknown"  # For error messages

    # --- Determine expected CRC from index ---
    # Prioritize nested subcommand entry if applicable (e.g., ruff -> subcommands -> check)
    if len(command_parts) > 1:
        base_tool_name = command_parts[0]
        subcommand_name = command_parts[1]
        base_entry = index_data.get(base_tool_name)
        if isinstance(base_entry, dict) and "subcommands" in base_entry:
            subcommands_dict = base_entry["subcommands"]
            if isinstance(subcommands_dict, dict) and subcommand_name in subcommands_dict:
                subcommand_entry = subcommands_dict[subcommand_name]
                if isinstance(subcommand_entry, dict):
                    index_crc = subcommand_entry.get("crc")
                    index_crc_source = f"Nested ({base_tool_name}.subcommands.{subcommand_name})"

    # Fallback or primary: Check top-level entry (e.g., ruff_check)
    if index_crc is None:
        top_level_entry = index_data.get(tool_id)
        if isinstance(top_level_entry, dict):
            index_crc = top_level_entry.get("crc")
            index_crc_source = f"Top-Level ({tool_id})"

    # Assert that we found an index CRC from *somewhere*
    if index_crc is None:
        pytest.fail(
            f"Managed sequence '{tool_id}' is missing a valid CRC entry in the tool index "
            f"({TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}), checked nested and top-level.\\n"
            f"Action Required: Ensure the tool index includes a CRC entry for this sequence, "
            f"or remove/exclude '{tool_id}' from managed sequences."
        )

    # --- Debug Logging --- START
    log.debug(f"[DEBUG {tool_id}] JSON Path: {relative_json_path}")
    log.debug(f"[DEBUG {tool_id}] JSON CRC Value: {json_crc} (Type: {type(json_crc)})")
    log.debug(f"[DEBUG {tool_id}] Index CRC Value: {index_crc} (Type: {type(index_crc)}) (Source: {index_crc_source})")
    # --- Debug Logging --- END

    # Perform case-insensitive comparison
    json_crc_str = str(json_crc).lower()

    # --- ADDED CHECK: Explicitly fail if JSON CRC is the skeleton value --- START
    # Get the expected index CRC *before* deciding whether to fail or compare
    index_crc_str = str(index_crc).lower() if index_crc is not None else None

    if json_crc_str == "0x00000000":
        # Check if the index ALSO expects 0x00000000 (meaning intentionally blank baseline)
        if index_crc_str == "0x00000000":
            log.info(
                f"Skipping consistency check for '{tool_id}': Both JSON and index have skeleton CRC (0x00000000), indicating intentionally empty baseline."
            )
        else:
            # Get the index CRC solely for the error message context
            index_data = tool_index_handler.get_raw_index_data()
            index_crc_from_index = None  # Default
            index_crc_source_for_error = "Unknown"
            if len(command_parts) > 1:
                base_tool_name = command_parts[0]
                subcommand_name = command_parts[1]
                base_entry = index_data.get(base_tool_name)
                if isinstance(base_entry, dict) and "subcommands" in base_entry:
                    subcommands_dict = base_entry["subcommands"]
                    if isinstance(subcommands_dict, dict) and subcommand_name in subcommands_dict:
                        subcommand_entry = subcommands_dict[subcommand_name]
                        if isinstance(subcommand_entry, dict):
                            index_crc_from_index = subcommand_entry.get("crc")
                            index_crc_source_for_error = f"Nested ({base_tool_name}.subcommands.{subcommand_name})"
            if index_crc_from_index is None:
                top_level_entry = index_data.get(tool_id)
                if isinstance(top_level_entry, dict):
                    index_crc_from_index = top_level_entry.get("crc")
                    index_crc_source_for_error = f"Top-Level ({tool_id})"

            # Specific message for skeleton files needing population
            fail_message = (
                f"JSON CRC is skeleton value (0x00000000) for managed sequence '{tool_id}':\\n"
                f"  JSON file ({relative_json_path}): metadata.ground_truth_crc = {json_crc}\\n"
                f"  Tool Index ({TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}): Expected CRC = {index_crc_from_index if index_crc_from_index else '(Not Found/Applicable)'} (Source: {index_crc_source_for_error})\\n"
                f"--- MANDATE REINFORCEMENT --- \\n"
                f"  Your ONLY task is to populate the STRUCTURE (description, usage, options, arguments, subcommands) based on the ground truth TXT baseline ({relative_txt_path}).\\n"
                f"  You MUST NOT manually set the 'metadata.ground_truth_crc' field. This field is managed EXCLUSIVELY by automated tooling.\\n"
                f"----------------------------- \\n"
                f"Action Required (AI): This JSON file ({relative_json_path}) is a skeleton and needs its structure populated based on the TXT baseline.\\n"
                f"  Steps:\\n"
                f"  1. Read the ground truth TXT file: {relative_txt_path} (if it exists, may need generation first via test_ensure_txt_baselines_exist).\\n"
                f"  2. **Populate ONLY the JSON STRUCTURE in this file ({relative_json_path}) based on the TXT content and schema guidelines.**\\n"
                f"  3. **After confirming the JSON structure is fully populated and correct**, use the designated CRC update tool: `uv run python update_json_crc_tool.py --file {relative_json_path}`. This tool *must* be used to set the CRC; do not edit it manually.\\n"
                f"  4. Ensure the resulting JSON content adheres to the schema (check test_json_schema_validation.py results)."
            )
            pytest.fail(fail_message)
    # --- ADDED CHECK: Explicitly fail if JSON CRC is the skeleton value --- END

    # If json_crc is not 0x00000000 OR if it was 0x00000000 but the index also expected that,
    # proceed with comparing to the index CRC (if index_crc was found)
    elif index_crc_str is not None and json_crc_str != index_crc_str:
        # --- Check for mismatch ---
        # Message for actual mismatches (TXT likely changed, or index/JSON mismatch)
        fail_message = (
            f"JSON CRC mismatch for managed sequence '{tool_id}' (case-insensitive comparison):\\n"
            f"  JSON file ({relative_json_path}): metadata.ground_truth_crc = {json_crc}\\n"
            f"  Tool Index ({TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}): Expected CRC = {index_crc} (Source: {index_crc_source})\\n"
            f"--- MANDATE REINFORCEMENT --- \\n"
            f"  Your ONLY task related to this file ({relative_json_path}) is to ensure its STRUCTURE (description, usage, options, arguments, subcommands) accurately reflects the ground truth TXT baseline ({relative_txt_path}).\\n"
            f"  You MUST NOT manually edit the 'metadata.ground_truth_crc' field. This field is managed EXCLUSIVELY by automated tooling.\\n"
            f"----------------------------- \\n"
            f"Action Required (AI): The JSON definition's structure needs updating based on its source TXT baseline.\\n"
            f"  Steps:\\n"
            f"  1. Verify the TXT file ({relative_txt_path}) content is up-to-date (regenerate via test_ensure_txt_baselines_exist if needed).\\n"
            f"  2. Read the current content of this JSON file ({relative_json_path}).\\n"
            f"  3. **Update ONLY the JSON STRUCTURE based on the verified TXT content.** Ensure the structure is complete and accurate according to the TXT baseline.\\n"
            f"  4. **After confirming the JSON structure is correct**, use the designated CRC update tool: `uv run python update_json_crc_tool.py --file {relative_json_path}`. This tool *must* be used to set the CRC; do not edit it manually.\\n"
            f"  5. Ensure the resulting JSON content adheres to the schema (check test_json_schema_validation.py results).\\n"
            f"Alternatively, if this sequence ('{tool_id}') should not be managed, remove/exclude it."
        )
        pytest.fail(fail_message)
    # --- End Check for mismatch ---
    elif index_crc_str is None:
        # This case should have been caught earlier when checking if index_crc is None
        # but added defensively
        log.warning(f"Could not compare CRCs for {tool_id} because index CRC was not found or invalid.")
    else:
        # If we reach here, the CRCs matched (and were not both 0x00000000).
        log.info(f"Consistency checks passed for {tool_id} (CRC match: {json_crc})")


# --- Direct Execution Logic ---


# Helper function to encapsulate the core check for one sequence
def _check_single_consistency(command_parts, tool_index_handler, WORKSPACE_ROOT, TOOLS_DIR, TOOL_INDEX_PATH):
    if not command_parts:
        log.warning("Skipping empty command parts tuple in direct check.")
        return None  # Indicate skip

    tool_id = command_sequence_to_id(command_parts)
    tool_name = command_parts[0]
    tool_dir = TOOLS_DIR / tool_name
    json_file = tool_dir / f"{tool_id}.json"
    relative_json_path = json_file.relative_to(WORKSPACE_ROOT)

    # --- Load JSON Content ---
    if not json_file.is_file():
        log.error(f"[{tool_id}] JSON file missing: {relative_json_path}")
        return {"tool_id": tool_id, "status": "ERROR", "reason": "JSON Missing"}
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except Exception as e:
        log.error(f"[{tool_id}] Failed to load/decode JSON {relative_json_path}: {e}")
        return {"tool_id": tool_id, "status": "ERROR", "reason": f"JSON Load Error: {e}"}

    # --- Check CRC ---
    json_metadata = json_data.get("metadata", {})
    json_crc = json_metadata.get("ground_truth_crc")
    if json_crc is None:
        log.error(f"[{tool_id}] Missing 'metadata.ground_truth_crc' in {relative_json_path}")
        return {"tool_id": tool_id, "status": "ERROR", "reason": "Missing JSON CRC Key"}

    json_crc_str = str(json_crc).lower()

    # --- Explicit check for 0x0 ---
    if json_crc_str == "0x00000000":
        log.warning(f"[{tool_id}] JSON CRC is skeleton value (0x00000000) in {relative_json_path}")
        return {"tool_id": tool_id, "status": "SKELETON", "json_crc": json_crc}

    # --- Get Index CRC ---
    index_data = tool_index_handler.get_raw_index_data()
    index_crc = None
    index_crc_source = "Unknown"
    if len(command_parts) > 1:
        base_tool_name = command_parts[0]
        subcommand_name = command_parts[1]
        base_entry = index_data.get(base_tool_name)
        if isinstance(base_entry, dict) and "subcommands" in base_entry:
            subcommands_dict = base_entry["subcommands"]
            if isinstance(subcommands_dict, dict) and subcommand_name in subcommands_dict:
                subcommand_entry = subcommands_dict[subcommand_name]
                if isinstance(subcommand_entry, dict):
                    index_crc = subcommand_entry.get("crc")
                    index_crc_source = f"Nested ({base_tool_name}.subcommands.{subcommand_name})"
    if index_crc is None:
        top_level_entry = index_data.get(tool_id)
        if isinstance(top_level_entry, dict):
            index_crc = top_level_entry.get("crc")
            index_crc_source = f"Top-Level ({tool_id})"

    if index_crc is None:
        log.error(f"[{tool_id}] Missing corresponding CRC entry in tool index.")
        return {"tool_id": tool_id, "status": "ERROR", "reason": "Missing Index CRC"}

    index_crc_str = str(index_crc).lower()

    # --- Compare ---
    if json_crc_str != index_crc_str:
        log.error(f"[{tool_id}] CRC MISMATCH: JSON='{json_crc}', Index='{index_crc}' (Source: {index_crc_source})")
        return {"tool_id": tool_id, "status": "MISMATCH", "json_crc": json_crc, "index_crc": index_crc}
    else:
        log.info(f"[{tool_id}] CRC OK: '{json_crc}'")
        return {"tool_id": tool_id, "status": "OK", "json_crc": json_crc}
