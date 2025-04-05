"""
# PURPOSE: Process HTTP response headers for downloads.

## INTERFACES:
    process_response_headers(response: Response, existing_file_size: int = 0) -> Tuple[str, int, bool]

## DEPENDENCIES:
    re: Regular expressions
    logging: Logging functionality
    requests: HTTP response handling
    pathlib: Path operations
    urllib.parse: URL parsing
    os: Operating system path operations
"""

import re
import logging
from pathlib import Path
from typing import Tuple, Dict, Any
from logging import LoggerAdapter
from datetime import datetime
from requests import Response
from urllib.parse import urlparse
import os

logger = LoggerAdapter(logging.getLogger(__name__), {"component": "response_handler"})


def process_response_headers(
    response: Response, existing_file_size: int = 0
) -> Tuple[str, int, bool]:
    """
    Process response headers for filename and size information.

    PRE-CONDITIONS:
        - response must be a valid Response object
        - existing_file_size must be non-negative

    POST-CONDITIONS:
        - returned filename is not empty
        - returned total_size is non-negative
        - is_resuming implies response status is 206

    PARAMS:
        response: HTTP response object
        existing_file_size: Size of existing file if resuming

    RETURNS:
        tuple[str, int, bool]: (filename, total_size, is_resuming)
            - filename: Extracted or default filename
            - total_size: Total size of the file
            - is_resuming: Whether download is being resumed

    USAGE:
        >>> response = requests.get("https://example.com/file.zip", stream=True)
        >>> filename, size, resuming = process_response_headers(response)
        >>> print(f"Downloading {filename} ({size} bytes)")
    """
    assert isinstance(response, Response), "response must be a Response object"
    assert existing_file_size >= 0, "existing_file_size must be non-negative"

    log_context = {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "existing_size": existing_file_size,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Extract filename
    filename = _extract_filename(response)
    log_context["filename"] = filename

    # Handle resumable downloads
    is_resuming = False
    total_size = 0

    if response.status_code == 206:  # Partial Content
        content_range = response.headers.get("Content-Range", "")
        match = re.match(r"bytes (\d+)-(\d+)/(\d+)", content_range)

        if match:
            start, _, file_size = map(int, match.groups())
            if start == existing_file_size:
                is_resuming = True
                total_size = file_size
                logger.info("Resuming download", extra=log_context)
            else:
                logger.warning(
                    "Range mismatch",
                    extra={**log_context, "expected": existing_file_size, "got": start},
                )
                total_size = existing_file_size + int(
                    response.headers.get("content-length", 0)
                )
    else:
        total_size = int(response.headers.get("content-length", 0))
        if existing_file_size > 0:
            logger.warning("Server doesn't support resume", extra=log_context)

    # Validate post-conditions
    assert filename, "Filename cannot be empty"
    assert total_size >= 0, "Total size must be non-negative"
    if is_resuming:
        assert response.status_code == 206, "Resuming requires partial content response"

    logger.debug(
        "Processed response headers",
        extra={**log_context, "total_size": total_size, "is_resuming": is_resuming},
    )

    return filename, total_size, is_resuming


def _extract_filename(response: Response) -> str:
    """Extract filename from Content-Disposition header or URL."""
    content_disposition = response.headers.get("Content-Disposition", "")
    if content_disposition:
        # More robust regex for filename extraction (handles quotes optionally)
        matches = re.findall('filename="?([^"\n]+)"?', content_disposition)
        if matches:
            # Take the first match and remove potential path characters
            filename = os.path.basename(matches[0])
            if filename:
                logger.debug(f"Extracted filename from Content-Disposition: {filename}")
                return filename

    # Fallback to URL if Content-Disposition doesn't provide a filename
    try:
        parsed_url = urlparse(response.url)
        filename_from_url = os.path.basename(parsed_url.path)
        if filename_from_url:
            logger.debug(f"Extracted filename from URL: {filename_from_url}")
            return filename_from_url
    except Exception as e:
        logger.warning(f"Could not parse filename from URL {response.url}: {e}")

    # Final fallback
    logger.warning("Could not determine filename, using default.")
    content_type = response.headers.get("Content-Type", "").lower()
    if "image/jpeg" in content_type or "image/jpg" in content_type:
        return "downloaded_file.jpg"
    elif "image/png" in content_type:
        return "downloaded_file.png"
    elif "image/gif" in content_type:
        return "downloaded_file.gif"
    elif "image/webp" in content_type:
        return "downloaded_file.webp"
    elif "image/svg+xml" in content_type:
        return "downloaded_file.svg"
    else:
        return "downloaded_file.bin"  # Generic fallback for unknown types


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added type hints and assertions
- Added structured logging with context
- Added usage examples
- Added private helper function
- Improved error context

## FUTURE TODOs:
- Add content type validation
- Add checksum validation
"""
