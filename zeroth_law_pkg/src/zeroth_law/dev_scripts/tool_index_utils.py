#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/tool_index_utils.py
"""
Utilities for loading and saving the central tool index file (tool_index.json).
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict

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
DEFAULT_ENCODING = "utf-8"


# --- Tool Index Handling ---


def load_tool_index() -> Dict[str, dict]:
    """Loads the full tool index file. Returns empty dict on error or if not found."""
    if not TOOL_INDEX_PATH.is_file():
        log.warning(f"Tool index file not found at {TOOL_INDEX_PATH}. Returning empty index.")
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
                    log.warning(f"Invalid or missing metadata structure for tool '{tool_id}' in index {TOOL_INDEX_PATH}. Skipping.")

            if not validated_data:
                log.warning(f"No valid tool entries found in the index file: {TOOL_INDEX_PATH}")

            return validated_data

    except (json.JSONDecodeError, IOError) as e:
        log.error(f"Error loading or parsing tool index {TOOL_INDEX_PATH}: {e}. Returning empty index.")
        return {}
    except Exception as e:
        log.exception(f"Unexpected error loading tool index {TOOL_INDEX_PATH}: {e}. Returning empty index.")  # Log full traceback
        return {}


def save_tool_index(index_data: Dict[str, dict]) -> None:
    """
    Saves the complete tool index file, sorted by key.

    Args:
        index_data: The dictionary representing the entire desired index content.
                    It's the responsibility of the caller to ensure this dictionary
                    has the correct structure (e.g., {"tool_id": {"crc": "...", "timestamp": ...}}).

    Raises:
        IOError: If saving the file fails.
        TypeError: If index_data is not a dictionary.
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

    except IOError as e:
        log.error(f"Error saving tool index {TOOL_INDEX_PATH}: {e}")
        raise  # Re-raise the exception for the caller to handle
    except Exception as e:
        log.exception(f"Unexpected error saving tool index {TOOL_INDEX_PATH}: {e}")
        # Wrap unexpected errors in IOError for consistency? Or re-raise? Re-raising is cleaner.
        raise


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
        assert reloaded_index[dummy_id]["crc"] == dummy_crc
        assert dummy_id_2 in reloaded_index
        log.info("Reload verification successful.")

        # Clean up dummy entry
        log.info(f"Cleaning up dummy entries: {dummy_id}, {dummy_id_2}")
        reloaded_index.pop(dummy_id, None)
        reloaded_index.pop(dummy_id_2, None)
        save_tool_index(reloaded_index)
        log.info("Cleanup save successful.")

    except Exception as e:
        log.error(f"Test save/cleanup failed: {e}")

    log.info("Testing finished.")
