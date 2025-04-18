#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/generate_baseline_cli.py
"""
CLI wrapper for generating/verifying baseline files for a single tool command.
"""

import argparse
import logging
import sys
from pathlib import Path

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
    from src.zeroth_law.dev_scripts.baseline_generator import (
        generate_or_verify_baseline,
        BaselineStatus,  # Import the Enum
    )
except ImportError as e:
    print(f"Error importing baseline_generator module. Check paths and dependencies. Details: {e}", file=sys.stderr)
    sys.exit(2)  # Use a different exit code for import errors

# --- LOGGING ---
# Setup basic logging for the CLI tool
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)  # Get logger for this module


# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(
        description="Generate or verify ground-truth baseline files (TXT, index, skeleton JSON) for a command's --help output.",
        epilog="Compares captured help CRC with index. Updates TXT/index if mismatched or new. Ensures skeleton JSON exists.",
    )
    parser.add_argument(
        "--command",
        required=True,
        nargs="+",
        help=("The full command sequence for the tool (e.g., 'ruff', 'ruff check'). " "'--help | cat' will be added automatically by the generator."),
    )
    # Optional: Add verbosity flag if needed later
    # parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")

    args = parser.parse_args()
    original_command_str = " ".join(args.command)

    log.info(f"Starting baseline check/generation for command: '{original_command_str}'")

    try:
        status = generate_or_verify_baseline(original_command_str)
    except Exception as e:
        # Catch unexpected errors during the core generation process
        log.exception(f"An unexpected error occurred during baseline generation for '{original_command_str}': {e}")
        status = BaselineStatus.UNEXPECTED_ERROR

    # Report final status and set exit code
    if status == BaselineStatus.UP_TO_DATE:
        log.info(f"[SUCCESS] Baseline for '{original_command_str}' is up-to-date.")
        sys.exit(0)
    elif status == BaselineStatus.UPDATED:
        log.info(f"[SUCCESS] Baseline for '{original_command_str}' was successfully updated.")
        sys.exit(0)
    else:
        # Log the specific failure reason
        log.error(f"[FAILURE] Baseline generation failed for '{original_command_str}' with status: {status.name}")
        # Specific messages for common failures
        if status == BaselineStatus.FAILED_WRITE_TXT:
            log.error("  >> Failed to write the ground truth .txt file.")
        elif status == BaselineStatus.FAILED_SAVE_INDEX:
            log.error("  >> Wrote .txt file but failed to update tool_index.json. Index is now INCONSISTENT!")
        elif status == BaselineStatus.FAILED_SKELETON_WRITE:
            log.error("  >> Updated .txt and index, but failed to write the skeleton .json file.")
        elif status == BaselineStatus.FAILED_CAPTURE:
            log.error("  >> Failed to capture command output. Is the command installed and executable?")
        # Add more specific messages if needed

        sys.exit(1)


if __name__ == "__main__":
    main()
