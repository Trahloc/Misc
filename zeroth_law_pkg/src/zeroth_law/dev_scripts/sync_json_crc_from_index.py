#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/sync_json_crc_from_index.py
"""
Synchronizes the 'metadata.ground_truth_crc' field within one or more JSON definition
files with the corresponding CRC value stored in the central tool_index.json.
"""

import argparse
import json
import logging
from pathlib import Path
import sys
import re

# --- Add project root to path for sibling imports ---
try:
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root))
except NameError:
    project_root = Path.cwd()
    if not (project_root / "src").exists():
        project_root = project_root.parent
    sys.path.insert(0, str(project_root))

# --- Import project modules ---
try:
    from src.zeroth_law.dev_scripts.tool_index_utils import load_tool_index, TOOL_INDEX_PATH, DEFAULT_ENCODING
except ImportError as e:
    print(f"Error importing tool_index_utils. Check paths/dependencies. Details: {e}", file=sys.stderr)
    sys.exit(2)


# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# --- CONSTANTS ---
CRC_FIELD_NAME = "ground_truth_crc"
METADATA_KEY = "metadata"
COMMAND_KEY = "command"
SUBCOMMAND_KEY = "subcommand"
CRC_HEX_REGEX = re.compile(r"^0x[0-9a-fA-F]{8}$")


def get_command_sequence_from_json(data: dict) -> tuple[str, ...] | None:
    """Extracts the command sequence (tuple) from the JSON data."""
    command = data.get(COMMAND_KEY)
    subcommand = data.get(SUBCOMMAND_KEY)  # Can be None

    if not command or not isinstance(command, str):
        log.warning(f"Missing or invalid '{COMMAND_KEY}' key in JSON data.")
        # Fallback: try getting from metadata? (Not standard)
        # Fallback: try parsing filename? (Brittle)
        return None

    if subcommand is not None and not isinstance(subcommand, str):
        log.warning(f"Invalid '{SUBCOMMAND_KEY}' key type in JSON data (should be str or null).")
        return None  # Treat invalid type as missing subcommand

    if subcommand:
        return (command, subcommand)
    else:
        return (command,)


def get_crc_from_index(index_data: dict, command_sequence: tuple[str, ...]) -> str | None:
    """Finds the CRC for a command sequence in the loaded tool_index data."""
    if not command_sequence:
        return None

    tool_id = "_".join(command_sequence)
    base_tool_name = command_sequence[0]
    index_crc = None

    # --- Logic Refined --- #
    base_entry = index_data.get(base_tool_name)
    is_base_command_request = len(command_sequence) == 1

    # 1. If requesting the base command, check its top-level CRC first
    if is_base_command_request and isinstance(base_entry, dict):
        index_crc = base_entry.get("crc")  # Get CRC directly from base entry

    # 2. If it's a subcommand request OR base CRC wasn't found above
    if not is_base_command_request or index_crc is None:
        if len(command_sequence) > 1:
            subcommand_name = command_sequence[1]
            if isinstance(base_entry, dict) and "subcommands" in base_entry:
                subcommands_dict = base_entry.get("subcommands")  # Use .get for safety
                if isinstance(subcommands_dict, dict):
                    subcommand_entry = subcommands_dict.get(subcommand_name)
                    if isinstance(subcommand_entry, dict):
                        # Prioritize the CRC within the specific subcommand entry
                        index_crc = subcommand_entry.get("crc")

    # 3. Fallback: Check for a top-level entry using the full tool_id (less common)
    if index_crc is None:
        top_level_entry_by_id = index_data.get(tool_id)
        if isinstance(top_level_entry_by_id, dict):
            maybe_crc = top_level_entry_by_id.get("crc")
            if maybe_crc:
                log.debug(f"Using top-level CRC for {tool_id} as final fallback.")
                index_crc = maybe_crc
    # --- End Refined Logic ---

    if index_crc and isinstance(index_crc, str) and CRC_HEX_REGEX.match(index_crc):
        return index_crc
    elif index_crc:
        log.warning(f"Found CRC '{index_crc}' for {command_sequence} in index, but format is invalid. Ignoring.")
        return None
    else:
        # Make the warning slightly more specific based on the logic path
        if not base_entry:
            log.warning(f"Base tool '{base_tool_name}' not found in tool_index.json for sequence {command_sequence}")
        elif not is_base_command_request and (
            not isinstance(base_entry.get("subcommands"), dict) or command_sequence[1] not in base_entry["subcommands"]
        ):
            log.warning(
                f"Subcommand '{command_sequence[1]}' entry not found under '{base_tool_name}' in tool_index.json for sequence {command_sequence}"
            )
        else:
            log.warning(
                f"Could not find a valid CRC entry for command sequence {command_sequence} in tool_index.json (checked base, subcommand, and top-level fallback)"
            )
        return None


def sync_single_file(file_path: Path, full_index_data: dict) -> bool:
    """
    Reads a JSON file, finds the expected CRC in the index, updates the file,
    and writes it back using canonical formatting.

    Args:
        file_path: Path object for the JSON file.
        full_index_data: The loaded dictionary from tool_index.json.

    Returns:
        True if the file was processed successfully (or no update needed),
        False if an error occurred or the CRC couldn't be synced.
    """
    log.info(f"Processing file: {file_path}")

    if not file_path.is_file():
        log.error(f"File not found: {file_path}")
        return False

    try:
        with open(file_path, "r", encoding=DEFAULT_ENCODING) as f:
            content = f.read()
            if not content.strip():
                log.error(f"File is empty: {file_path}")
                return False
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                log.error(f"Invalid JSON in file {file_path}: {e}")
                return False

        if not isinstance(data, dict):
            log.error(f"Root element in {file_path} is not a JSON object (dictionary). Skipping.")
            return False

        # --- Get command sequence and expected CRC ---
        command_sequence = get_command_sequence_from_json(data)
        if not command_sequence:
            log.error(f"Could not determine command sequence from {file_path}. Skipping.")
            return False

        expected_crc = get_crc_from_index(full_index_data, command_sequence)
        if not expected_crc:
            log.error(
                f"Could not find expected CRC for {command_sequence} (from {file_path}) in {TOOL_INDEX_PATH}. Skipping update."
            )
            # Fail the sync for this file if CRC is missing in index
            return False
        # --- End get command sequence ---

        # Ensure metadata key exists
        if METADATA_KEY not in data or not isinstance(data[METADATA_KEY], dict):
            log.info(f"'{METADATA_KEY}' object missing or invalid in {file_path}. Creating/resetting it to add CRC.")
            data[METADATA_KEY] = {}

        original_crc = data[METADATA_KEY].get(CRC_FIELD_NAME)

        # Compare case-insensitively
        needs_update = True  # Assume update needed unless CRCs match
        if original_crc is not None and str(original_crc).lower() == expected_crc.lower():
            log.info(f"CRC ({expected_crc}) already matches value in tool_index.json for {file_path}")
            needs_update = False
        # else: # Implicitly, CRCs don't match or original is missing
        # No specific log here, proceed to update

        if needs_update:
            # Update the data dictionary with the expected CRC from the index
            log.info(f"Updating CRC in {file_path} from '{original_crc}' to '{expected_crc}' (from tool_index.json)")
            data[METADATA_KEY][CRC_FIELD_NAME] = expected_crc

            # Write the updated data back to the file in canonical format
            try:
                with open(file_path, "w", encoding=DEFAULT_ENCODING) as f:
                    json.dump(data, f, sort_keys=True, indent=2, separators=(",", ": "))
                    f.write("\n")  # Ensure trailing newline
                log.info(f"Successfully wrote updated CRC to {file_path}")
            except IOError as e:
                log.error(f"Failed to write updated CRC to {file_path}: {e}")
                return False  # Write failed
        # else: # No update needed
        # Already logged above
        # pass

        return True  # Return True if update succeeded or wasn't needed

    except KeyError as e:
        log.error(f"Data structure error processing {file_path}: {e}")
        return False
    except TypeError as e:
        log.error(f"Data type error processing {file_path}: {e}")
        return False
    except IOError as e:
        log.error(f"File I/O error for {file_path}: {e}")
        return False
    except Exception as e:
        log.exception(f"Unexpected error processing {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description=f"Synchronize '{METADATA_KEY}.{CRC_FIELD_NAME}' in JSON files with tool_index.json.",
        epilog=f"Looks up the command in {TOOL_INDEX_PATH} and updates the JSON file's CRC field.",
    )
    parser.add_argument(
        "json_files", nargs="+", type=Path, help="Path(s) to the JSON definition file(s) to synchronize."
    )

    args = parser.parse_args()

    # Load the index once
    log.info(f"Loading tool index from {TOOL_INDEX_PATH}...")
    full_index_data = load_tool_index()
    if not full_index_data:
        log.error("Tool index is empty or failed to load. Cannot proceed.")
        sys.exit(2)
    log.info(f"Loaded {len(full_index_data)} top-level entries from tool index.")

    exit_code = 0
    for file_path in args.json_files:
        if not sync_single_file(file_path, full_index_data):
            exit_code = 1  # Indicate failure if any file fails

    if exit_code == 0:
        log.info("Finished processing all files successfully.")
    else:
        log.warning("Finished processing files, but errors occurred for one or more files.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
