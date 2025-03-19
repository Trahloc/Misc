"""
# PURPOSE

  Validates URLs for the civitai.com download script.
  This module handles URL validation and normalization specifically for civitai.com URLs.

## 1. INTERFACES

  validate_url(url: str) -> bool: Validates if a given URL is a valid civitai.com URL
  normalize_url(url: str) -> str: Normalizes a civitai.com URL to its canonical form

## 2. DEPENDENCIES

  re: Regular expression operations for URL pattern matching
  urllib.parse: URL parsing and manipulation
  logging: Logging functionality for validation errors

"""

import re
import logging
from urllib.parse import urlparse, urljoin
from typing import Optional


def validate_url(url: str) -> bool:
    """
    Validate if a given URL is a valid civitai.com URL.
    PARAMS:
        url (str): The URL to validate
    RETURNS:
        bool: True if valid, False otherwise
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        logging.error(f"Invalid URL scheme or netloc: {url}")
        return False

    # Check if the URL is from civitai.com
    if not re.match(r"^(www\.)?civitai\.com$", parsed_url.netloc):
        logging.error(
            f"Invalid domain: {parsed_url.netloc}. Expected domain: civitai.com"
        )
        return False

    # Check if the URL path matches the expected patterns
    if re.match(r"^/models/\d+", parsed_url.path) or \
       re.match(r"^/images/\d+", parsed_url.path) or \
       re.match(r"^/api/download/models/\d+", parsed_url.path):
        return True

    logging.error(
        f"Invalid URL path: {parsed_url.path}. Expected path to start with /models/, /images/, or /api/download/models/"
    )
    return False


def normalize_url(url: str) -> Optional[str]:
    """
    Normalize a given URL to ensure it is in the correct format.
    PARAMS:
        url (str): The URL to normalize
    RETURNS:
        Optional[str]: The normalized URL if valid, None otherwise
    """
    if validate_url(url):
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc.replace("www.", "")
        normalized_path = parsed_url.path.rstrip("/")  # Remove trailing slash

        # Keep query parameters for API download URLs
        if "/api/download/models/" in parsed_url.path:
            normalized_url = f"{parsed_url.scheme}://{netloc}{normalized_path}"
            if parsed_url.query:
                normalized_url += f"?{parsed_url.query}"
            return normalized_url

        return urljoin(f"{parsed_url.scheme}://{netloc}", normalized_path)
    return None


"""
## Current Known Errors

None

## Improvements Made

- Added support for direct API download URLs in validation
- Added query parameter preservation for API URLs
- Improved error messages

## Future TODOs

- Add specific path pattern validation for different civitai.com URL types
- Implement rate limiting check
- Add support for more API endpoints
"""
