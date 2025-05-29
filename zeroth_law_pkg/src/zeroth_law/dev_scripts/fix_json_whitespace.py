#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/fix_json_whitespace.py
"""Scans for JSON files in the tools directory and removes trailing whitespace after the final brace."""

import sys
import structlog
from pathlib import Path
import re
import json
import jsonschema

# from zeroth_law.path_utils import find_project_root
from zeroth_law.common.path_utils import find_project_root

# Add project root to sys.path to ensure correct module resolution
# Assuming this script is run from somewhere within the project structure
project_root = find_project_root()

log = structlog.get_logger()

# Regex to find a closing brace followed by whitespace at the very end of the string
TRAILING_WHITESPACE_RE = re.compile(r"(\}\s+)$")


def fix_json_trailing_whitespace(file_path: Path) -> bool:
    """Reads a file, removes trailing whitespace after final }, writes back if changed."""
    try:
        original_content = file_path.read_text(encoding="utf-8")
        # Efficiently check if the problematic pattern exists at the end
        match = TRAILING_WHITESPACE_RE.search(original_content)
        if match:
            # If found, strip all trailing whitespace (more robust than just removing the matched group)
            corrected_content = original_content.rstrip()
            # Double-check it still ends with '}' after stripping
            if corrected_content.endswith("}"):
                if corrected_content != original_content:
                    log.info(f"Fixing trailing whitespace in: {file_path.relative_to(project_root)}")
                    file_path.write_text(corrected_content, encoding="utf-8")
                    return True  # File was changed
                else:
                    # This case should be rare if TRAILING_WHITESPACE_RE matched
                    log.debug(f"Whitespace found but stripping caused no change? {file_path.relative_to(project_root)}")
                    return False
            else:
                log.warning(
                    f"Stripping whitespace removed closing brace in {file_path.relative_to(project_root)}. Skipping fix."
                )
                return False
        else:
            # log.debug(f"No trailing whitespace found in: {file_path.relative_to(project_root)}")
            return False  # No change needed

    except Exception as e:
        log.error(f"Error processing file {file_path.relative_to(project_root)}: {e}")
        return False


def main():
    """Main function to find and fix JSON files."""
    log.info("Starting JSON trailing whitespace check...")
    project_root = find_project_root()
    if not project_root:
        log.error("Could not find project root. Exiting.")
        sys.exit(1)

    tools_dir = project_root / "src" / "zeroth_law" / "tools"
    if not tools_dir.is_dir():
        log.error(f"Tools directory not found at {tools_dir}. Exiting.")
        sys.exit(1)

    json_files = list(tools_dir.rglob("*.json"))
    log.info(f"Found {len(json_files)} JSON files to check in {tools_dir.relative_to(project_root)}.")

    files_fixed = 0
    files_error = 0

    for json_file in json_files:
        try:
            if fix_json_trailing_whitespace(json_file):
                files_fixed += 1
        except Exception as e:
            # Log error from the main loop just in case
            log.exception(f"Unexpected error during processing of {json_file}: {e}")
            files_error += 1

    log.info(f"JSON trailing whitespace check complete. Fixed: {files_fixed} file(s). Errors: {files_error}.")
    if files_error > 0:
        sys.exit(1)  # Exit with error if any file processing failed


if __name__ == "__main__":
    main()
