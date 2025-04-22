#!/usr/bin/env python3
"""
Removes the 'file_status' key from the metadata object in all tool JSON files.
"""

import json
import logging
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")  # Changed back to INFO for less noise
log = logging.getLogger(__name__)

# Determine the project root and tools directory
try:
    SCRIPT_DIR = Path(__file__).resolve().parent
    WORKSPACE_ROOT = SCRIPT_DIR.parent
    TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
except Exception as e:
    log.error(f"Error determining script/workspace directories: {e}")
    sys.exit(1)

if not TOOLS_DIR.is_dir():
    log.error(f"Tools directory not found: {TOOLS_DIR}")
    sys.exit(1)

log.info(f"Scanning for JSON files in: {TOOLS_DIR}")

# --- Main Processing Logic ---
files_processed = 0
files_modified = 0
errors_encountered = 0

for json_file in TOOLS_DIR.rglob("*.json"):
    files_processed += 1
    relative_path = json_file.relative_to(WORKSPACE_ROOT)
    log.debug(f"Processing: {relative_path}")

    try:
        # Read the current content
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check for the key and modify if present
        modified = False
        metadata = data.get("metadata")
        if isinstance(metadata, dict) and "file_status" in metadata:
            log.info(f"Removing 'file_status' from: {relative_path}")
            del metadata["file_status"]
            # If metadata becomes empty after deletion, remove the metadata key itself
            if not metadata:
                if "metadata" in data:
                    del data["metadata"]
            else:
                # Ensure the potentially modified metadata object is back in data
                data["metadata"] = metadata
            modified = True

        # Write back ONLY if modified
        if modified:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")  # Add trailing newline for consistency
            files_modified += 1
            log.debug(f"Successfully modified and saved: {relative_path}")
        else:
            log.debug(f"No 'file_status' key found in: {relative_path}")

    except json.JSONDecodeError:
        log.warning(f"Skipping invalid JSON file: {relative_path}")
        errors_encountered += 1
    except Exception as e:
        log.error(f"Error processing file {relative_path}: {e}")
        errors_encountered += 1

# --- Summary ---
log.info("-" * 30)
log.info("Scan Complete.")
log.info(f"Total JSON files scanned: {files_processed}")
log.info(f"Files modified (removed 'file_status'): {files_modified}")
log.info(f"Errors/Skipped files: {errors_encountered}")

if errors_encountered > 0:
    sys.exit(1)
else:
    sys.exit(0)
