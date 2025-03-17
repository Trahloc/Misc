"""
# PURPOSE

  Handles HTTP response headers and content information for downloads.

## 1. INTERFACES

  process_response_headers(response, existing_file_size: int = 0) -> tuple[str, int, bool]:
    Process response headers to get filename, total size, and resumption status

## 2. DEPENDENCIES

  re: Regular expression operations
  logging: Logging functionality
  requests: HTTP response handling
  pathlib: Path operations for filenames
  urllib.parse: URL parsing
  typing: Type hints

"""

import re
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Tuple
from requests import Response


def process_response_headers(
    response: Response, existing_file_size: int = 0
) -> Tuple[str, int, bool]:
    """
    Process response headers to extract filename, size, and resumption information.

    PARAMS:
        response (Response): HTTP response object
        existing_file_size (int): Size of existing file if resuming

    RETURNS:
        tuple[str, int, bool]: (filename, total_size, is_resuming)
            - filename: Extracted or default filename
            - total_size: Total size of the file
            - is_resuming: Whether download is being resumed
    """
    filename = Path(urlparse(response.url).path).name
    is_resuming = False
    total_size = 0

    # Try to get filename from Content-Disposition header
    content_disposition = response.headers.get("content-disposition", "")
    if "filename=" in content_disposition:
        extracted_filename = re.findall("filename=(.+)", content_disposition)[0].strip(
            '"'
        )
        if extracted_filename:
            filename = extracted_filename

    # Handle resumable downloads
    if response.status_code == 206:  # Partial Content
        if "Content-Range" in response.headers:
            content_range = response.headers.get("Content-Range", "")
            match = re.match(r"bytes (\d+)-(\d+)/(\d+)", content_range)
            if match:
                start, _, file_size = map(
                    int, match.groups()
                )  # Using _ for unused end value
                if start == existing_file_size:
                    is_resuming = True
                    total_size = file_size
                else:
                    logging.warning(
                        "Range mismatch: expected %s, got %s", existing_file_size, start
                    )
                    total_size = existing_file_size + int(
                        response.headers.get("content-length", 0)
                    )
    else:
        total_size = int(response.headers.get("content-length", 0))
        if existing_file_size > 0:
            logging.warning(
                "Server doesn't support resume. Starting fresh download of %s", filename
            )

    return filename, total_size, is_resuming


"""
## Current Known Errors

None

## Improvements Made

- Initial implementation
- Comprehensive header processing

## Future TODOs

- Add support for more header types
- Add content type validation
"""
