"""
# PURPOSE: Handle download resumption logic.

## INTERFACES:
    prepare_resumption(filepath: Path, headers: Dict[str, str]) -> tuple[bool, int, str]

## DEPENDENCIES:
    pathlib: Path handling
    logging: Logging functionality
    typing: Type hints
"""

import logging
from pathlib import Path
from typing import Dict, Tuple, Union
from logging import LoggerAdapter
from datetime import datetime
from dataclasses import dataclass

# Create structured logger
logger = LoggerAdapter(
    logging.getLogger(__name__), {"component": "download_resumption"}
)


@dataclass
class ResumptionInfo:
    """Data class for download resumption information."""

    is_resuming: bool
    existing_size: int
    file_mode: str
    headers: Dict[str, str]


def prepare_resumption(filepath: Path, headers: Dict[str, str]) -> ResumptionInfo:
    """
    Prepare download resumption by checking existing file and setting up headers.

    PRE-CONDITIONS:
        - filepath must be a valid Path object
        - headers must be a non-None dictionary
        - if resuming, file must exist and be readable

    POST-CONDITIONS:
        - returned file_mode is either 'ab' or 'wb'
        - if resuming, Range header is set correctly
        - existing_size matches file size if resuming

    PARAMS:
        filepath: Path to the file being downloaded
        headers: Request headers to be modified for resumption

    RETURNS:
        ResumptionInfo containing:
            - is_resuming: Whether download can be resumed
            - existing_size: Size of existing file (0 if not resuming)
            - file_mode: File mode to use ('ab' for append, 'wb' for write)
            - headers: Updated headers dict

    USAGE:
        >>> info = prepare_resumption(Path('file.zip'), {})
        >>> if info.is_resuming:
        ...     print(f"Resuming from byte {info.existing_size}")
    """
    # Validate pre-conditions
    assert isinstance(filepath, Path), "filepath must be a Path object"
    assert isinstance(headers, dict), "headers must be a dictionary"

    log_context = {
        "filepath": str(filepath),
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        if filepath.exists():
            existing_size = filepath.stat().st_size
            headers["Range"] = f"bytes={existing_size}-"

            logger.info(
                "Resuming download",
                extra={**log_context, "existing_size": existing_size},
            )

            # Validate post-conditions for resume
            assert existing_size >= 0, "File size must be non-negative"
            return ResumptionInfo(True, existing_size, "ab", headers)

        logger.debug("Starting new download", extra=log_context)
        return ResumptionInfo(False, 0, "wb", headers)

    except (OSError, PermissionError) as e:
        logger.error(
            "Failed to prepare download resumption",
            extra={**log_context, "error": str(e)},
        )
        # Fall back to new download on error
        return ResumptionInfo(False, 0, "wb", headers)


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added structured logging with context
- Added pre/post condition assertions
- Added ResumptionInfo dataclass for better type safety
- Added error handling with fallbacks
- Added usage examples

## FUTURE TODOs:
- Add file integrity validation
- Add support for checksum verification
"""
