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
WORKSPACE_ROOT = Path(__file__).parent.resolve()
TOOL_INDEX_PATH = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools" / "tool_index.json"
TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"

# --- Helper Functions ---


def get_tool_id_from_path(json_path: Path) -> tuple[str | None, str | None]:
    """Derives tool_id and potentially base_tool_name from the json file path."""
    try:
        # Expected format: .../tools/<tool_name>/<tool_id>.json or .../tools/<tool_name>/<subcommand_id>.json
        tool_id = json_path.stem  # e.g., 'ruff_check' or 'safety'
        tool_name = json_path.parent.name  # e.g., 'ruff' or 'safety'

        # Handle cases where tool_id might contain the tool_name (like ruff_check)
        # or be the same as tool_name (like safety)
        if tool_id == tool_name:
            # Simple case: safety/safety.json -> tool_id='safety', base_tool_name='safety'
            return tool_id, tool_name
        elif tool_id.startswith(tool_name + "_"):
            # Subcommand case: ruff/ruff_check.json -> tool_id='ruff_check', base_tool_name='ruff'
            # It's also possible the base_tool_name is needed to find nested CRCs
            return tool_id, tool_name
        else:
            # If naming convention is different, might need adjustment
            log.warning(
                f"Could not confidently determine base tool name for {tool_id} from path {json_path}. Assuming top-level lookup."
            )
            return tool_id, None  # Fallback to just using tool_id

    except IndexError:
        log.error(f"Could not derive tool_id from path: {json_path}")
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

    target_json_path = args.file.resolve()  # Ensure absolute path

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
