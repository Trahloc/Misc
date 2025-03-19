"""
# PURPOSE: Manages file download and progress.

## INTERFACES: download_file(url: str, destination: str, filename_pattern: str = None, metadata: dict = None, api_key: str = None) -> str: Downloads a file with custom filename patterns.

## DEPENDENCIES:
- logging: For logging functionality
- pathlib: For path operations
- tqdm: For progress bars
- requests: For HTTP requests
- filename_pattern: For custom filename generation
- re: For regular expression operations

## TODO: None
"""

import logging
import re
from pathlib import Path
from tqdm import tqdm
from requests import Response
import os
import requests
from typing import Dict, Any, Optional

from .filename_pattern import process_filename_pattern


def download_with_progress(
    response: Response,
    filepath: Path,
    total_size: int,
    existing_size: int = 0,
    mode: str = "wb",
) -> bool:
    """
    Downloads file content with progress tracking.

    PARAMS:
        response (Response): HTTP response object with content
        filepath (Path): Path where file will be saved
        total_size (int): Total expected file size
        existing_size (int): Size of existing file if resuming
        mode (str): File open mode ('wb' or 'ab')

    RETURNS:
        bool: True if download successful, False otherwise
    """
    try:
        logging.info(f"Starting download to {filepath}")
        logging.info(f"Total size: {total_size} bytes")
        if existing_size:
            logging.info(f"Resuming from: {existing_size} bytes")

        chunk_size = 8192  # 8KB chunks
        last_received = 0
        stall_timeout = 30  # 30 seconds timeout for stalled downloads

        with open(filepath, mode, encoding=None if "b" in mode else "utf-8") as f, tqdm(
            desc=filepath.name,
            total=total_size,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
            initial=existing_size,
        ) as pbar:
            for data in response.iter_content(chunk_size=chunk_size):
                if not data:  # Check for empty chunks
                    if pbar.n == last_received:  # No progress since last chunk
                        logging.warning("Download appears stalled - no data received")
                        return False
                    continue

                size = f.write(data)
                pbar.update(size)
                last_received = pbar.n

                if pbar.n > total_size:  # Sanity check
                    logging.error(f"Received more data than expected: {pbar.n} > {total_size}")
                    return False

        if os.path.getsize(filepath) != total_size:
            logging.error(f"Download incomplete: {os.path.getsize(filepath)} != {total_size}")
            return False

        logging.info(f"Download completed successfully: {filepath}")
        return True

    except IOError as e:
        logging.error("Failed to write file: %s", str(e))
        return False
    except MemoryError as e:
        logging.error("Memory error during download: %s", str(e))
        return False
    except Exception as e:
        logging.error(f"Unexpected error during download: {str(e)}")
        return False


def download_file(
    url: str,
    destination: str,
    filename_pattern: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> str:
    """
    PURPOSE: Download a file from a URL with support for custom filename patterns.

    PARAMS:
        url (str): The URL to download the file from.
        destination (str): The directory to save the downloaded file.
        filename_pattern (Optional[str]): The pattern to use for the filename.
        metadata (Optional[Dict[str, Any]]): Metadata to use for filename placeholders.
        api_key (Optional[str]): API key for authentication.

    RETURNS:
        str: The path to the downloaded file.
    """
    # Ensure destination directory exists
    Path(destination).mkdir(parents=True, exist_ok=True)

    # Set up headers with API key if provided
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        # Make the request to get the file
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()

        # Extract original filename from Content-Disposition or URL
        original_filename = extract_filename_from_response(response, url)

        # Process custom filename pattern if provided
        if filename_pattern:
            filename = process_filename_pattern(filename_pattern, metadata, original_filename)
        else:
            filename = original_filename

        # Create full filepath
        filepath = Path(destination) / filename

        # Get file size from headers
        total_size = int(response.headers.get('content-length', 0))

        # Download the file with progress tracking
        success = download_with_progress(response, filepath, total_size)

        if success:
            return str(filepath)
        else:
            logging.error(f"Failed to download {url}")
            return ""

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {str(e)}")
        return ""
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return ""


def extract_filename_from_response(response: Response, url: str) -> str:
    """
    PURPOSE: Extract the filename from the response headers or URL.

    PARAMS:
        response (Response): The HTTP response.
        url (str): The URL of the request.

    RETURNS:
        str: The extracted filename.
    """
    # Try to get filename from Content-Disposition header
    content_disposition = response.headers.get('content-disposition', '')
    if 'filename=' in content_disposition:
        try:
            filename = re.findall('filename=(.+)', content_disposition)[0].strip('"')
            return filename
        except:
            pass

    # Fall back to URL if Content-Disposition parsing fails
    return os.path.basename(url.split('?')[0])


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added support for custom filename patterns.
- Integrated with filename_pattern module for processing patterns.
- Improved error handling for requests.

## FUTURE TODOs:
- Add support for download resumption with custom filenames.
- Consider adding file integrity verification.
"""
