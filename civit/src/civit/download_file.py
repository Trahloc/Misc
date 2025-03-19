# FILE: src/civit/download_file.py
"""
# PURPOSE: Download a file from a URL with support for custom filename patterns.

## INTERFACES: download_file(url: str, destination: str, api_key: Optional[str] = None) -> str: Downloads a file with custom filename patterns.

## DEPENDENCIES: requests, os
"""

import logging
from pathlib import Path
from tqdm import tqdm
from requests import Response
import os
import requests
import re
from typing import Optional, Dict


def make_request_with_auth(url: str, headers: Dict[str, str], stream: bool = False) -> Response:
    """Make an authenticated request with detailed logging"""
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


def download_file(url: str, destination: str, api_key: Optional[str] = None) -> str:
    """
    Download a file from a URL with support for custom filename patterns.

    CONTEXT: Uses requests for HTTP operations.

    PARAMS:
        url (str): The URL to download the file from
        destination (str): The directory to save the downloaded file
        api_key (Optional[str]): API key for authentication

    RETURNS:
        str: The path to the downloaded file
    """
    logging.debug(f"Starting download from URL: {url}")

    # Set up headers with API key if provided
    headers = {
        'Accept': '*/*',  # Accept any content type
        'User-Agent': 'civit-cli/1.0'  # Identify our client
    }
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
        visible_part = api_key[:4] if len(api_key) > 4 else ""
        logging.debug(f"Using API key for auth (starts with: {visible_part}...)")

    # For direct API URLs, make a direct request
    if "/api/download/models/" in url:
        logging.debug("Direct API URL detected - making authenticated request")
        response = make_request_with_auth(url, headers, stream=True)

        # Extract filename from the URL or Content-Disposition header
        if "Content-Disposition" in response.headers:
            filename = re.findall("filename=(.+)", response.headers["Content-Disposition"])[0].strip('"')
        else:
            filename = url.split("/")[-1].split("?")[0]

        total_size = int(response.headers.get('content-length', 0))
        logging.debug(f"Filename: {filename}, Size: {total_size}")
    else:
        # Handle model page URLs through the API
        # Get the direct download URL from the Civitai API
        response = make_request_with_auth(url, headers)
        direct_url = response.json().get('downloadUrl')

        if not direct_url:
            logging.error("No download URL found in API response")
            logging.debug(f"API Response: {response.text}")
            raise ValueError("No download URL found in API response")

        # Download the file from the direct URL
        response = make_request_with_auth(direct_url, headers, stream=True)
        filename = direct_url.split('/')[-1]

    # Create destination directory if it doesn't exist
    Path(destination).mkdir(parents=True, exist_ok=True)

    # Save the file to the destination
    filepath = os.path.join(destination, filename)
    total_size = int(response.headers.get('content-length', 0))

    with open(filepath, 'wb') as f, tqdm(
        desc=filename,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for data in response.iter_content(chunk_size=8192):
            size = f.write(data)
            pbar.update(size)

    logging.info(f'Download completed: {filepath}')
    return filepath


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added detailed request debugging
- Improved error handling and logging
- Added proper User-Agent and Accept headers
- Added helper function for authenticated requests

## FUTURE TODOs: Consider adding more request options
"""
