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
from zeroth_law.common.path_utils import find_project_root, process_json_files_in_tools_dir

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
    from zeroth_law.common.path_utils import process_json_files_in_tools_dir

    process_json_files_in_tools_dir(
        file_callback=fix_json_trailing_whitespace,
        log_prefix="JSON trailing whitespace check",
        exit_on_error=True,
    )


if __name__ == "__main__":
    main()
