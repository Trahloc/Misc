# FILE: src/civit/download_file.py
"""
# PURPOSE: Download a file from a URL with support for custom filename patterns.

## INTERFACES: download_file(url: str, destination: str, api_key: Optional[str] = None) -> str: Downloads a file with custom filename patterns.

## DEPENDENCIES: requests, os
"""

import logging
import re
from pathlib import Path
from tqdm import tqdm
from typing import Optional, Dict
import requests
from requests import Response


def make_request_with_auth(
    url: str, headers: Dict[str, str], stream: bool = False
) -> Response:
    """Make an authenticated request with detailed logging"""
    if not url:
        raise ValueError("URL cannot be empty")

    logging.debug("Making request:")
    logging.debug(f"  URL: {url}")
    logging.debug(f"  Headers: {headers}")
    logging.debug(f"  Stream: {stream}")

    response = requests.get(url, stream=stream, headers=headers)

    logging.debug("Response details:")
    logging.debug(f"  Status code: {response.status_code}")
    logging.debug(f"  Headers: {dict(response.headers)}")
    if response.status_code == 401:
        logging.debug(f"  Response body: {response.text}")
        raise requests.exceptions.HTTPError(
            f"Authentication failed (401) - Response: {response.text}"
        )
    response.raise_for_status()
    return response


def extract_filename(url: str, headers: Dict[str, str]) -> str:
    """Extract filename from Content-Disposition header or URL"""
    if "Content-Disposition" in headers:
        matches = re.findall('filename="(.+?)"', headers["Content-Disposition"])
        if matches:
            return matches[0]
        matches = re.findall("filename=(.+)", headers["Content-Disposition"])
        if matches:
            return matches[0].strip('"')
    return url.split("/")[-1].split("?")[0]


def download_file(
    url: str, destination: str, api_key: Optional[str] = None
) -> Optional[str]:
    """
    Download a file from a URL with support for custom filename patterns.

    CONTEXT: Uses requests for HTTP operations.

    PARAMS:
        url (str): The URL to download the file from
        destination (str): The directory to save the downloaded file
        api_key (Optional[str]): API key for authentication

    RETURNS:
        Optional[str]: The path to the downloaded file if successful, None otherwise

    RAISES:
        ValueError: If the URL is empty or invalid
        OSError: If there are file system related errors
    """
    if not url:
        raise ValueError("URL cannot be empty")

    logging.debug(f"Starting download from URL: {url}")

    # Set up headers with API key if provided
    headers = {
        "Accept": "*/*",  # Accept any content type
        "User-Agent": "civit-cli/1.0",  # Identify our client
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        visible_part = api_key[:4] if len(api_key) > 4 else ""
        logging.debug(f"Using API key for auth (starts with: {visible_part}...)")

    try:
        # For direct API URLs, make a direct request
        if "/api/download/models/" in url:
            logging.debug("Direct API URL detected - making authenticated request")
            response = make_request_with_auth(url, headers, stream=True)
            filename = extract_filename(url, response.headers)
        else:
            # Handle model page URLs through the API
            # Get the direct download URL from the Civitai API
            response = make_request_with_auth(url, headers)
            data = response.json()
            direct_url = data.get("downloadUrl")

            if not direct_url:
                logging.error("No download URL found in API response")
                logging.debug(f"API Response: {response.text}")
                return None

            # Download the file from the direct URL
            response = make_request_with_auth(direct_url, headers, stream=True)
            filename = extract_filename(direct_url, response.headers)

        # Create destination directory if it doesn't exist
        dest_path = Path(destination)
        try:
            dest_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logging.error(f"Failed to create destination directory: {e}")
            return None

        filepath = dest_path / filename
        total_size = int(response.headers.get("content-length", 0))

        with open(filepath, "wb") as f, tqdm(
            desc=filename,
            total=total_size,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for data in response.iter_content(chunk_size=8192):
                size = f.write(data)
                pbar.update(size)

        logging.info(f"Download completed: {filepath}")
        return str(filepath)

    except (requests.RequestException, ValueError, OSError) as e:
        logging.error(f"Download failed: {str(e)}")
        return None


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added detailed request debugging
- Improved error handling and logging
- Added proper User-Agent and Accept headers
- Added helper function for authenticated requests

## FUTURE TODOs: Consider adding more request options
"""
