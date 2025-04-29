#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/sync_json_crc_from_index.py
"""
DEPRECATED: This script is no longer the correct way to synchronize CRC values.

Use 'scripts/update_json_crc_tool.py --file <path>' on individual files AFTER
ensuring their structure is correct via AI interpretation based on the corresponding
.txt baseline and schema guidelines. Batch synchronization is discouraged as it
bypasses the necessary AI interpretation step.
"""

import argparse
import json
import structlog
import sys
from pathlib import Path

# --- LOGGING ---
log = structlog.get_logger()


def main():
    parser = argparse.ArgumentParser(
        description="DEPRECATED: Use 'scripts/update_json_crc_tool.py --file <path>' instead.",
        epilog="This script is disabled to enforce the correct workflow.",
    )
    parser.add_argument(
        "json_files",
        nargs="*",
        help="Path(s) to the JSON definition file(s) (ignored).",
    )

    args = parser.parse_args()

    log.error("DEPRECATED SCRIPT CALLED: src/zeroth_law/dev_scripts/sync_json_crc_from_index.py")
    log.error("This script should not be used for synchronizing CRCs.")
    log.error("Please use 'scripts/update_json_crc_tool.py --file <path>' instead.")
    log.error(
        "Run the update script only AFTER verifying/updating the JSON file's structure "
        "based on its .txt baseline and schema guidelines."
    )
    sys.exit(2)  # Exit with error code to signal improper usage


if __name__ == "__main__":
    main()
