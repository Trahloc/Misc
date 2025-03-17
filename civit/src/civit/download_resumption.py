"""
# PURPOSE

  Handles download resumption logic for partially downloaded files.

## 1. INTERFACES

  prepare_resumption(filepath: Path, headers: dict) -> tuple[bool, int, str]:
    Prepares headers and determines if download can be resumed

## 2. DEPENDENCIES

  pathlib: Path handling
  logging: Logging functionality
  typing: Type hints

"""

import logging
from pathlib import Path
from typing import Dict, Tuple


def prepare_resumption(
    filepath: Path, headers: Dict[str, str]
) -> Tuple[bool, int, str]:
    """
    Prepares download resumption by checking existing file and setting up headers.

    PARAMS:
        filepath (Path): Path to the file being downloaded
        headers (dict): Request headers to be modified for resumption

    RETURNS:
        tuple[bool, int, str]: (is_resuming, existing_size, file_mode)
            - is_resuming: Whether download can be resumed
            - existing_size: Size of existing file (0 if not resuming)
            - file_mode: File mode to use ('ab' for append, 'wb' for write)
    """
    existing_file_size = 0
    if filepath.exists():
        existing_file_size = filepath.stat().st_size
        headers["Range"] = f"bytes={existing_file_size}-"
        logging.info(
            "Resuming download for %s from byte %d", filepath.name, existing_file_size
        )
        return True, existing_file_size, "ab"

    return False, 0, "wb"


"""
## Current Known Errors

None

## Improvements Made

- Initial implementation

## Future TODOs

- Add validation for file integrity
- Add support for checksums
"""
