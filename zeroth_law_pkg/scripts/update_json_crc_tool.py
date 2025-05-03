#!/usr/bin/env python3
import json
import argparse
import sys
from pathlib import Path
import logging

# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# --- Constants ---
# Assuming the script runs from the workspace root
WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()  # Navigate two levels up
TOOL_INDEX_PATH = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools" / "tool_index.json"
TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"

# --- Helper Functions ---


def get_tool_id_from_path(json_path: Path) -> tuple[str | None, str | None]:
    """Derives tool_id and potentially base_tool_name from the json file path.

    Revised logic to handle nested directories by calculating path relative to TOOLS_DIR
    and stopping ID construction when a directory part matches the filename stem.
    """
    try:
        abs_json_path = json_path.resolve()
        abs_tools_dir = TOOLS_DIR.resolve()

        if not abs_json_path.is_relative_to(abs_tools_dir):
            log.error(f"JSON path {abs_json_path} is not inside TOOLS_DIR {abs_tools_dir}")
            return None, None

        relative_path = abs_json_path.relative_to(abs_tools_dir)
        parts = relative_path.parts

        if not parts:
            log.error(f"Could not extract path parts from {relative_path}")
            return None, None

        tool_name = parts[0]  # Base tool name is always the first directory
        tool_id_stem = abs_json_path.stem

        # Construct ID from path parts, stopping when a part matches the stem
        path_based_id_parts = []
        for part in parts[:-1]:  # Iterate through directories leading up to the file
            path_based_id_parts.append(part)
            if part == tool_id_stem:  # If dir name matches stem, assume this is the end of the ID hierarchy
                break
        else:  # If no directory part matched the stem (e.g., tool1/tool1.json or ruff/ruff_check.json)
            # Check if the first part (tool_name) itself matches the stem
            if len(path_based_id_parts) == 1 and path_based_id_parts[0] == tool_id_stem:
                # This covers the tool1/tool1.json case, ID is just tool1
                pass  # ID is already correct from the loop
            else:
                # This covers ruff/ruff_check.json case where stem is different
                # and also potentially tool/sub/different_stem.json (though less likely)
                # We might need just the stem as the ID, or tool_stem?
                # Let's assume for now, if no dir part matches stem,
                # and the first dir part doesn't match the stem,
                # the intended ID *might* just be the stem itself (like ruff_check).
                # OR it might be tool_stem.
                # For the ruff_check example, find_expected_crc handles looking up tool_id=ruff_check
                # OR tool_id=ruff, subcommand=check.
                # Let's try constructing tool_stem as the ID here.
                # If the stem itself is the ID (like ruff_check), find_expected_crc should handle it.
                # If the ID is truly tool_stem (like foo_bar where foo/bar.json exists), this works.
                if tool_name != tool_id_stem:
                    path_based_id_parts.append(tool_id_stem)

        tool_id = "_".join(path_based_id_parts)

        log.debug(
            f"Derived from path {relative_path}: tool_name='{tool_name}', tool_id='{tool_id}', stem='{tool_id_stem}'"
        )

        # Always return the first part as base_tool_name for hierarchical lookup in find_expected_crc
        return tool_id, tool_name

    except (ValueError, IndexError) as e:
        log.error(f"Error deriving tool_id from path: {json_path}. Error: {e}")
        return None, None


def find_expected_crc(tool_id: str, base_tool_name: str | None, index_data: dict) -> tuple[str | None, str]:
    """Finds the expected CRC in the tool index, checking nested then top-level."""
    index_crc = None
    index_crc_source = "Unknown"

    # --- Determine expected CRC from index ---
    # Prioritize nested subcommand entry if applicable
    if base_tool_name and "_" in tool_id and tool_id.startswith(base_tool_name + "_"):
        subcommand_name = tool_id.split("_", 1)[1]  # Get the part after the first underscore
        base_entry = index_data.get(base_tool_name)
        if isinstance(base_entry, dict) and "subcommands" in base_entry:
            subcommands_dict = base_entry["subcommands"]
            if isinstance(subcommands_dict, dict) and subcommand_name in subcommands_dict:
                subcommand_entry = subcommands_dict[subcommand_name]
                if isinstance(subcommand_entry, dict):
                    index_crc = subcommand_entry.get("crc")
                    index_crc_source = f"Nested ({base_tool_name}.subcommands.{subcommand_name})"
                    log.info(f"Found nested CRC {index_crc} for {tool_id} under {base_tool_name}")

    # Fallback or primary: Check top-level entry
    if index_crc is None:
        top_level_entry = index_data.get(tool_id)
        if isinstance(top_level_entry, dict):
            index_crc = top_level_entry.get("crc")
            index_crc_source = f"Top-Level ({tool_id})"
            log.info(f"Found top-level CRC {index_crc} for {tool_id}")
        elif base_tool_name and base_tool_name == tool_id:  # Check base tool if tool_id matches base_tool_name
            base_entry = index_data.get(base_tool_name)
            if isinstance(base_entry, dict):
                index_crc = base_entry.get("crc")
                # Check if it's just the base tool's CRC without subcommands object
                if index_crc and "subcommands" not in base_entry:
                    index_crc_source = f"Top-Level Base ({base_tool_name})"
                    log.info(f"Found top-level base CRC {index_crc} for {tool_id}")
                else:
                    index_crc = None  # Avoid using base CRC if subcommands exist

    if index_crc is None:
        log.error(f"Could not find CRC entry for '{tool_id}' (base: {base_tool_name}) in tool index.")

    return index_crc, index_crc_source


# --- Main Logic ---


def main():
    parser = argparse.ArgumentParser(
        description="Updates the 'metadata.ground_truth_crc' in a tool's JSON definition file based on the value in tool_index.json."
    )
    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to the JSON definition file to update (e.g., src/zeroth_law/tools/safety/safety.json)",
    )
    args = parser.parse_args()

    # --- DEBUG --- #
    log.debug(f"args.file type: {type(args.file)}, value: {args.file}")
    # --- END DEBUG --- #

    target_json_path = args.file.resolve()  # Ensure absolute path

    # --- DEBUG --- #
    log.debug(f"target_json_path type: {type(target_json_path)}, value: {target_json_path}")
    try:
        is_file_result = target_json_path.is_file()
        log.debug(f"target_json_path.is_file() result: {is_file_result}")
    except Exception as e:
        log.debug(f"Error calling is_file(): {e}")
    # --- END DEBUG --- #

    if not target_json_path.is_file():
        log.error(f"Target JSON file not found: {target_json_path}")
        sys.exit(1)

    # Derive tool_id from path
    tool_id, base_tool_name = get_tool_id_from_path(target_json_path)
    if not tool_id:
        log.error(f"Could not determine tool_id for {target_json_path}. Aborting.")
        sys.exit(1)
    log.info(f"Processing file: {target_json_path} (tool_id: {tool_id}, base_tool_name: {base_tool_name})")

    # Load Tool Index
    if not TOOL_INDEX_PATH.is_file():
        log.error(f"Tool index file not found: {TOOL_INDEX_PATH}")
        sys.exit(1)
    try:
        with open(TOOL_INDEX_PATH, "r", encoding="utf-8") as f:
            tool_index_data = json.load(f)
    except json.JSONDecodeError as e:
        log.error(f"Failed to decode tool index JSON {TOOL_INDEX_PATH}: {e}")
        sys.exit(1)
    except Exception as e:
        log.error(f"Failed to read tool index file {TOOL_INDEX_PATH}: {e}")
        sys.exit(1)

    # Find Expected CRC
    expected_crc, crc_source = find_expected_crc(tool_id, base_tool_name, tool_index_data)

    if expected_crc is None:
        log.error(f"No CRC found for '{tool_id}' in the tool index. Cannot update {target_json_path}.")
        sys.exit(1)

    log.info(f"Found expected CRC for '{tool_id}': {expected_crc} (Source: {crc_source})")

    # Load Target JSON
    try:
        with open(target_json_path, "r", encoding="utf-8") as f:
            target_json_data = json.load(f)
    except json.JSONDecodeError as e:
        log.error(f"Failed to decode target JSON file {target_json_path}: {e}")
        sys.exit(1)
    except Exception as e:
        log.error(f"Failed to read target JSON file {target_json_path}: {e}")
        sys.exit(1)

    # Update CRC if needed
    metadata = target_json_data.setdefault("metadata", {})  # Ensure metadata key exists
    current_crc = metadata.get("ground_truth_crc")

    # Perform case-insensitive comparison before updating
    if current_crc is None or str(current_crc).lower() != str(expected_crc).lower():
        log.info(f"Updating CRC in {target_json_path}: {current_crc} -> {expected_crc}")
        metadata["ground_truth_crc"] = expected_crc  # Update the value

        # Write Updated JSON Back
        try:
            with open(target_json_path, "w", encoding="utf-8") as f:
                json.dump(target_json_data, f, indent=4, ensure_ascii=False)
                f.write("\n")  # Add trailing newline for POSIX compatibility
            log.info(f"Successfully updated CRC in {target_json_path}")
        except Exception as e:
            log.error(f"Failed to write updated JSON file {target_json_path}: {e}")
            sys.exit(1)
    else:
        log.info(
            f"CRC in {target_json_path} ({current_crc}) already matches expected value ({expected_crc}). No update needed."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
