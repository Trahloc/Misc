#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/baseline_writers.py
"""
Utilities for writing baseline files (ground-truth .txt, skeleton .json).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List
import os

# --- Add project root to path for sibling imports ---
try:
    project_root = Path(__file__).resolve().parents[3]
except NameError:  # pragma: no cover # Exclude this fallback
    project_root = Path.cwd()


# --- LOGGING ---
log = logging.getLogger(__name__)


# --- CONSTANTS ---
# Define the root directory for tool definition files
# Allow overriding via environment variable for testing the main block
_test_tools_dir = os.environ.get("ZEROTH_LAW_TEST_TOOLS_DIR")
if _test_tools_dir:
    TOOLS_DIR_ROOT = Path(_test_tools_dir)
    log.info(f"Using test tools directory from env var: {TOOLS_DIR_ROOT}")
else:  # pragma: no cover # Exclude the non-env-var path determination
    try:
        # Assuming the script is in src/zeroth_law/dev_scripts/
        project_root = Path(__file__).resolve().parents[3]
    except NameError:  # pragma: no cover # Already excluded
        # Fallback if __file__ is not defined (e.g., interactive, some test runners)
        project_root = Path(".").resolve()
        log.warning("Could not determine project root from __file__, using cwd.")
    TOOLS_DIR_ROOT = project_root / "src" / "zeroth_law" / "tools"


# Ensure TOOLS_DIR_ROOT exists (added safety check)
# TOOLS_DIR_ROOT.mkdir(parents=True, exist_ok=True) # Better to let functions handle creation

DEFAULT_ENCODING = "utf-8"


# --- Internal Skeleton Helper ---


def _generate_basic_skeleton(
    command_sequence: List[str],
) -> Dict[str, Any]:  # pragma: no cover
    """
    Creates a generic skeleton JSON structure with enhanced guidance.
    Neither file_status nor ground_truth_crc are included in skeleton metadata.
    Presence of ground_truth_crc implies populated status.
    """
    skeleton = {
        "command_sequence": command_sequence,
        "description": "",  # Initialize as empty string
        "usage": "",  # Initialize as empty string
        "options": [
            # Example Switch/Flag (takes_argument: false):
            # {
            #   "short_form": "-v",
            #   "long_form": "--verbose",
            #   "takes_argument": false,
            #   "argument_name": null,
            #   "argument_details": null,
            #   "description": "Enable verbose logging",
            #   "default": false, // Implicit default
            #   "hidden": false
            # },
            # Example Option with Argument (takes_argument: true):
            # {
            #   "short_form": "-l",
            #   "long_form": "--line-length",
            #   "takes_argument": true,
            #   "argument_name": "INTEGER", // Placeholder name
            #   "argument_details": null,
            #   "description": "How many characters per line to allow.",
            #   "default": 88, // Extracted default
            #   "hidden": false
            # },
            # Example Option with Argument + Details:
            # {
            #   "short_form": "-t",
            #   "long_form": "--target-version",
            #   "takes_argument": true,
            #   "argument_name": "VERSION",
            #   "argument_details": "[py33|py34|...]", // Extracted details
            #   "description": "Python versions that should be supported...",
            #   "default": null,
            #   "hidden": false
            # }
        ],
        "arguments": [
            # Example Argument:
            # {
            #   "name": "SRC",
            #   "description": "Source files or directories",
            #   "required": true, // or false
            #   "variadic": true // Optional: if it can take multiple values (...)
            # }
        ],
        "subcommands": [
            # Example Subcommand:
            # {
            #   "name": "check",
            #   "description": "Run checks...",
            #   "summary": "Run checks."
            # }
        ],
        "metadata": {
            "ground_truth_crc": "0x00000000"  # Explicitly set to zero for skeletons. No other keys.
        },
    }
    # Note: We no longer add ground_truth_crc here, even if provided.
    # It should only be added to metadata when the file is actually populated.
    return skeleton


# --- File Writing Functions ---


def write_ground_truth_txt(tool_dir: Path, tool_id: str, content: str) -> bool:
    """
    Writes or overwrites the ground-truth .txt file.

    Args:
        tool_dir: The specific tool directory (e.g., .../tools/ruff).
        tool_id: The identifier for the file (e.g., "ruff", "ruff_check").
        content: The string content to write.

    Returns:
        True if writing was successful, False otherwise.
    """
    output_txt_path = tool_dir / f"{tool_id}.txt"
    log.info(f"Writing ground truth text to: {output_txt_path}")
    try:
        tool_dir.mkdir(parents=True, exist_ok=True)
        with open(output_txt_path, "w", encoding=DEFAULT_ENCODING) as f:
            f.write(content)
        log.info(f"Successfully saved ground truth text to {output_txt_path}")
        return True
    except IOError as e:  # pragma: no cover
        log.error(f"Error writing ground truth file {output_txt_path}: {e}")
        return False
    except Exception as e:  # pragma: no cover
        log.exception(f"Unexpected error writing ground truth file {output_txt_path}: {e}")
        return False


def ensure_skeleton_json_exists(tool_dir: Path, tool_id: str, command_sequence: List[str]) -> bool:
    """
    Ensures a skeleton JSON file exists. If it doesn't, creates it.
    The skeleton will contain `metadata: {"ground_truth_crc": "0x00000000"}` and no `file_status`.

    Args:
        tool_dir: The specific tool directory.
        tool_id: The identifier for the file.
        command_sequence: The command sequence for the skeleton.

    Returns:
        True if the file exists or was created successfully, False on write error.
    """
    output_json_path = tool_dir / f"{tool_id}.json"

    if output_json_path.is_file():
        log.debug(f"Skeleton JSON file already exists: {output_json_path}")
        return True

    log.info(f"Skeleton JSON file does not exist. Writing skeleton to: {output_json_path}")
    try:
        # Generate skeleton without passing CRC
        skeleton_data = _generate_basic_skeleton(command_sequence)
        tool_dir.mkdir(parents=True, exist_ok=True)  # Ensure dir exists

        with open(output_json_path, "w", encoding=DEFAULT_ENCODING) as f:
            json.dump(skeleton_data, f, indent=2)
            f.write("\n")  # Add trailing newline
        log.info(f"Successfully saved skeleton JSON to {output_json_path}")
        return True
    except IOError as e:  # pragma: no cover
        log.error(f"Error writing skeleton JSON file {output_json_path}: {e}")
        return False
    except Exception as e:  # pragma: no cover
        log.exception(f"Unexpected error writing skeleton JSON file {output_json_path}: {e}")
        return False


# --- Main execution function ---


def main():  # pragma: no cover # Exclude the entire main function
    """Runs the test/example logic for the baseline writers."""
    # Re-enable test log message for test_main_execution
    log.info("Testing baseline_writers...")

    # Setup basic logging for direct execution test
    # logging.basicConfig(
    #     level=logging.DEBUG,
    #     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # )
    log.info("Running baseline_writers main function for testing/example.")

    # Define test data


# Example usage (for testing this module directly)
if __name__ == "__main__":  # pragma: no cover # Exclude the main execution block
    main()  # Call the main function
