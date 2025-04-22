#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/tool_index_utils.py
"""
Utilities for loading and saving the central tool index file (tool_index.json).
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Tuple, Any, Optional
from filelock import FileLock, Timeout

# --- Add project root to path for sibling imports ---
# This assumes the script is run from a context where this path logic works
# or that the calling script handles the path appropriately.
try:
    project_root = Path(__file__).resolve().parents[3]
except NameError:
    # Fallback if __file__ is not defined (e.g., interactive session)
    # This might need adjustment depending on execution context.
    project_root = Path.cwd()


# --- LOGGING ---
# Use a logger specific to this module
log = logging.getLogger(__name__)
# Basic config assuming the calling script sets up root logging
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# --- CONSTANTS ---
# It's often better if constants like these are defined centrally, but for now:
TOOLS_DIR_ROOT: Path = project_root / "src" / "zeroth_law" / "tools"
TOOL_INDEX_PATH: Path = TOOLS_DIR_ROOT / "tool_index.json"
TOOL_INDEX_LOCK_PATH = TOOL_INDEX_PATH.with_suffix(".lock")
LOCK_TIMEOUT = 10
DEFAULT_ENCODING = "utf-8"


# --- Tool Index Handling ---


def load_tool_index() -> Dict[str, dict]:
    """Loads the full tool index file. Returns empty dict on error or if not found."""
    if not TOOL_INDEX_PATH.is_file():
        log.info(f"Tool index file not found at {TOOL_INDEX_PATH}. Returning empty index for bootstrap.")
        return {}
    try:
        with open(TOOL_INDEX_PATH, "r", encoding=DEFAULT_ENCODING) as f:
            full_index_data = json.load(f)

            # Validate the overall structure
            if not isinstance(full_index_data, dict):
                log.error(f"Tool index format is invalid (must be a Dict). Returning empty index: {TOOL_INDEX_PATH}")
                return {}

            # Basic validation of entries (ensure they are dicts with at least 'crc')
            validated_data = {}
            for tool_id, metadata in full_index_data.items():
                if isinstance(metadata, dict) and "crc" in metadata:
                    validated_data[tool_id] = metadata
                else:
                    # Keep track of subcommands even if the parent is slightly malformed? Or skip?
                    # For now, skip malformed entries entirely.
                    log.warning(
                        f"Invalid or missing metadata structure for tool '{tool_id}' in index {TOOL_INDEX_PATH}. Skipping."
                    )

            if not validated_data:
                log.warning(f"No valid tool entries found in the index file: {TOOL_INDEX_PATH}")

            return validated_data

    except (json.JSONDecodeError, IOError) as e:
        log.error(f"Error loading or parsing tool index {TOOL_INDEX_PATH}: {e}. Returning empty index.")
        return {}
    except Exception as e:
        log.exception(
            f"Unexpected error loading tool index {TOOL_INDEX_PATH}: {e}. Returning empty index."
        )  # Log full traceback
        return {}


def save_tool_index(index_data: Dict[str, dict]) -> bool:
    """
    Saves the complete tool index file, sorted by key.

    Args:
        index_data: The dictionary representing the entire desired index content.
                    It's the responsibility of the caller to ensure this dictionary
                    has the correct structure (e.g., {"tool_id": {"crc": "...", "timestamp": ...}}).

    Returns:
        True if the save was successful, False otherwise.
    """
    if not isinstance(index_data, dict):
        raise TypeError("index_data must be a dictionary")

    try:
        # Ensure parent directory exists
        TOOL_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Sort the index by key before saving for consistent ordering
        sorted_index = dict(sorted(index_data.items()))

        with open(TOOL_INDEX_PATH, "w", encoding=DEFAULT_ENCODING) as f:
            json.dump(sorted_index, f, indent=2)
            f.write("\n")  # Add trailing newline
        log.info(f"Successfully saved updated tool index to {TOOL_INDEX_PATH}")
        return True

    except IOError as e:
        log.error(f"Error saving tool index {TOOL_INDEX_PATH}: {e}")
        return False
    except Exception as e:
        log.exception(f"Unexpected error saving tool index {TOOL_INDEX_PATH}: {e}")
        # Wrap unexpected errors in IOError for consistency? Or re-raise? Re-raising is cleaner.
        return False


def get_index_entry(index_data: Dict[str, Any], command_sequence: Tuple[str, ...]) -> Dict[str, Any]:
    """Gets the specific metadata dictionary for a command sequence from the index.

    Handles nested subcommand lookups.

    Args:
        index_data: The full tool index dictionary.
        command_sequence: Tuple representing the command (e.g., ('ruff',), ('ruff', 'check')).

    Returns:
        The metadata dictionary for the sequence, or an empty dictionary if not found.
    """
    if not command_sequence:
        log.warning("Attempted to get index entry for empty command sequence.")
        return {}

    entry_id = "_".join(command_sequence)
    base_tool_name = command_sequence[0]

    if len(command_sequence) == 1:
        # Base command lookup
        entry = index_data.get(base_tool_name, {})
        log.debug(f"get_index_entry for base '{entry_id}': Found {entry}")
        return entry if isinstance(entry, dict) else {}
    else:
        # Subcommand lookup
        subcommand_name = command_sequence[1]
        base_entry = index_data.get(base_tool_name)
        if isinstance(base_entry, dict):
            subcommands_dict = base_entry.get("subcommands")
            if isinstance(subcommands_dict, dict):
                entry = subcommands_dict.get(subcommand_name, {})
                log.debug(f"get_index_entry for sub '{entry_id}': Found {entry}")
                return entry if isinstance(entry, dict) else {}
            else:
                log.debug(f"get_index_entry for sub '{entry_id}': 'subcommands' not found or not a dict in base entry.")
                return {}
        else:
            log.debug(f"get_index_entry for sub '{entry_id}': Base entry '{base_tool_name}' not found or not a dict.")
            return {}


def update_index_entry(
    index_data: Dict[str, Any], command_sequence: Tuple[str, ...], update_data: Dict[str, Any]
) -> bool:
    """Updates or creates the metadata entry for a command sequence in the index.

    Handles nested subcommand updates.

    Args:
        index_data: The full tool index dictionary (will be modified in place).
        command_sequence: Tuple representing the command.
        update_data: Dictionary containing the keys/values to update/add.

    Returns:
        True if the update was successful, False otherwise.
    """
    if not command_sequence:
        log.error("Attempted to update index entry for empty command sequence.")
        return False

    entry_id = "_".join(command_sequence)
    base_tool_name = command_sequence[0]

    try:
        if len(command_sequence) == 1:
            # Update base command
            if base_tool_name not in index_data or not isinstance(index_data[base_tool_name], dict):
                # Create new entry or overwrite invalid one, preserve existing subcommands if possible
                existing_subs = None
                if base_tool_name in index_data and isinstance(index_data[base_tool_name], dict):
                    existing_subs = index_data[base_tool_name].get("subcommands")
                index_data[base_tool_name] = {}
                if isinstance(existing_subs, dict):
                    index_data[base_tool_name]["subcommands"] = existing_subs
                log.info(f"Creating/resetting base entry for '{entry_id}'")

            # Perform the update
            index_data[base_tool_name].update(update_data)
            log.info(f"Updated base entry for '{entry_id}' with {update_data.keys()}")
            return True
        else:
            # Update subcommand
            subcommand_name = command_sequence[1]

            # Ensure base entry exists and is a dict
            if base_tool_name not in index_data or not isinstance(index_data[base_tool_name], dict):
                index_data[base_tool_name] = {}  # Create minimal parent
                log.warning(f"Created minimal base entry for '{base_tool_name}' while updating subcommand '{entry_id}'")

            base_entry = index_data[base_tool_name]

            # Ensure 'subcommands' dict exists
            if "subcommands" not in base_entry or not isinstance(base_entry.get("subcommands"), dict):
                base_entry["subcommands"] = {}
                log.info(f"Created 'subcommands' dict for base '{base_tool_name}' while updating '{entry_id}'")

            subcommands_dict = base_entry["subcommands"]

            # Ensure subcommand entry exists
            if subcommand_name not in subcommands_dict or not isinstance(subcommands_dict[subcommand_name], dict):
                subcommands_dict[subcommand_name] = {}
                log.info(f"Creating subcommand entry for '{entry_id}'")

            # Perform the update
            subcommands_dict[subcommand_name].update(update_data)
            log.info(f"Updated subcommand entry for '{entry_id}' with {update_data.keys()}")
            return True

    except Exception as e:
        log.exception(f"Unexpected error updating index for '{entry_id}': {e}")
        return False


def load_update_and_save_entry(command_sequence: Tuple[str, ...], update_data: Dict[str, Any]) -> bool:
    """Acquires a lock, loads the index, updates an entry, saves, and releases.

    This provides a thread-safe way to update a single entry in the index file.

    Args:
        command_sequence: Tuple representing the command.
        update_data: Dictionary containing the keys/values to update/add.

    Returns:
        True if the update and save were successful, False otherwise.
    """
    lock = FileLock(TOOL_INDEX_LOCK_PATH, timeout=LOCK_TIMEOUT)
    entry_id = "_".join(command_sequence)
    try:
        with lock:
            log.debug(f"Lock acquired for updating index entry: {entry_id}")
            # Load the *current* index data inside the lock
            current_index_data = load_tool_index()

            # Update the loaded data in memory
            if not update_index_entry(current_index_data, command_sequence, update_data):
                log.error(f"In-memory update failed for index entry: {entry_id}")
                return False  # Error during the in-memory update logic

            # Save the modified index back to disk
            if not save_tool_index(current_index_data):
                log.error(f"Failed to save updated index file after modifying entry: {entry_id}")
                return False  # Error during saving

            log.debug(f"Successfully updated and saved index entry: {entry_id}")
            return True

    except Timeout:
        log.error(f"Timeout acquiring lock for index update ({entry_id}) after {LOCK_TIMEOUT} seconds.")
        return False
    except Exception as e:
        log.exception(f"Unexpected error during locked index update for '{entry_id}': {e}")
        return False
    finally:
        if lock.is_locked:
            lock.release()
            log.debug(f"Lock released for index entry: {entry_id}")


# Example usage (for testing this module directly)
if __name__ == "__main__":
    # Setup basic logging for direct execution test
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    log.info("Testing tool_index_utils...")

    # Test loading
    log.info(f"Loading index from: {TOOL_INDEX_PATH}")
    current_index = load_tool_index()
    log.info(f"Loaded {len(current_index)} entries.")
    # print("Current Index:", json.dumps(current_index, indent=2)) # Can be noisy

    # Test saving (add/update a dummy entry)
    dummy_id = "_test_dummy_tool"
    dummy_crc = "0x12345678"
    log.info(f"Adding/Updating dummy entry: {dummy_id}")
    current_index[dummy_id] = {"crc": dummy_crc, "timestamp": time.time()}

    # Add another entry to test sorting
    dummy_id_2 = "_aaa_test_dummy"
    current_index[dummy_id_2] = {"crc": "0xabcdef", "timestamp": time.time()}

    try:
        log.info("Attempting to save index...")
        save_tool_index(current_index)
        log.info("Save successful (check file content manually).")

        # Verify load after save
        log.info("Reloading index after save...")
        reloaded_index = load_tool_index()
        assert dummy_id in reloaded_index
        # Use get_index_entry to verify nested structure if needed
        dummy_entry = get_index_entry(reloaded_index, (dummy_id,))
        assert dummy_entry.get("crc") == dummy_crc
        dummy_entry_2 = get_index_entry(reloaded_index, (dummy_id_2,))
        assert dummy_entry_2.get("crc") == "0xabcdef"

        log.info("Reload verification successful.")

        # Test updating existing entry
        log.info(f"Updating existing entry: {dummy_id}")
        update_success = update_index_entry(
            reloaded_index, (dummy_id,), {"checked_timestamp": time.time(), "new_field": True}
        )
        assert update_success
        dummy_entry_updated = get_index_entry(reloaded_index, (dummy_id,))
        assert dummy_entry_updated.get("new_field") is True
        assert "checked_timestamp" in dummy_entry_updated
        log.info("Update verification successful.")

        # Test updating/creating nested entry
        nested_id_tuple = ("_test_dummy_tool", "sub")
        log.info(f"Updating/creating nested entry: {"_" .join(nested_id_tuple)}")
        nested_update_success = update_index_entry(
            reloaded_index, nested_id_tuple, {"crc": "0xnested", "checked_timestamp": time.time()}
        )
        assert nested_update_success
        nested_entry = get_index_entry(reloaded_index, nested_id_tuple)
        assert nested_entry.get("crc") == "0xnested"
        assert "checked_timestamp" in nested_entry
        # Ensure parent structure exists
        assert "subcommands" in reloaded_index[dummy_id]
        assert "sub" in reloaded_index[dummy_id]["subcommands"]
        log.info("Nested update verification successful.")

        # Clean up dummy entry
        log.info(f"Cleaning up dummy entries: {dummy_id}, {dummy_id_2}")
        reloaded_index.pop(dummy_id, None)  # Remove base key which includes nested
        reloaded_index.pop(dummy_id_2, None)
        save_tool_index(reloaded_index)
        log.info("Cleanup save successful.")

    except Exception as e:
        log.error(f"Test save/cleanup failed: {e}")

    # Test the new locked update function
    log.info("Testing locked update...")
    test_seq = ("_test_dummy_tool",)
    update_success = load_update_and_save_entry(
        test_seq, {"checked_timestamp": time.time(), "new_field": "locked_update"}
    )
    if update_success:
        log.info(f"Locked update successful for {test_seq}")
        # Verify by reloading
        reloaded_index = load_tool_index()
        updated_entry = get_index_entry(reloaded_index, test_seq)
        log.info(f"Verified entry after locked update: {updated_entry}")
        if not updated_entry or updated_entry.get("new_field") != "locked_update":
            log.error("Verification failed after locked update!")
    else:
        log.error(f"Locked update failed for {test_seq}")

    log.info("Testing finished.")
