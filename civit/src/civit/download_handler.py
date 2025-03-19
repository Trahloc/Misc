"""
# PURPOSE: Manages file download and progress.

## INTERFACES: download_file(url: str, destination: str, filename_pattern: str = "{model_id}_{model_name}_{version}.{ext}", metadata: dict = None, api_key: str = None) -> str: Downloads a file with custom filename patterns.

## DEPENDENCIES: requests, os, boto3

## TODO: Add support for setting custom patterns for downloaded filenames.
- Support for using metadata from civitai model (e.g., model name, version, etc.) in filename.
- Allow configurable placeholders like {model_id}_{model_name}_{version}.{ext}.
- Implement filename pattern parsing and validation.
- Update download handler to use custom filename patterns.
- Add unit tests for custom filename functionality.
- Update documentation to include custom filename usage.
"""

import logging
from pathlib import Path
from tqdm import tqdm
from requests import Response
import os
import requests
import re
import zlib
import boto3
from botocore.exceptions import NoCredentialsError


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


def download_file(url: str, destination: str, filename_pattern: str = "{model_type}-{base_model}-{civit_website_model_name}-{model_id}-{crc32}-{original_filename}", metadata: dict = None, api_key: str = None) -> str:
    """
    PURPOSE: Download a file from a URL with support for custom filename patterns.

    CONTEXT: Uses requests for HTTP operations.

    PARAMS:
    - url (str): The URL to download the file from.
    - destination (str): The directory to save the downloaded file.
    - filename_pattern (str): The pattern to use for the filename.
    - metadata (dict): Metadata to use for filename placeholders.
    - api_key (str): API key for authentication.

    RETURNS: str: The path to the downloaded file.
    """
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    # Get the direct download URL from the Civitai API
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    direct_url = response.json().get('downloadUrl')

    # Download the file from the direct URL
    response = requests.get(direct_url, stream=True)
    response.raise_for_status()

    # Extract original filename from URL
    original_filename = direct_url.split('/')[-1]

    # Generate CRC32 checksum of the original filename
    crc32 = format(zlib.crc32(original_filename.encode()) & 0xFFFFFFFF, '08X')

    # Generate filename using the pattern and metadata
    if metadata:
        metadata.update({
            "crc32": crc32,
            "original_filename": original_filename
        })
        filename = filename_pattern.format(**metadata)
    else:
        filename = original_filename

    # Ensure the filename is safe and valid
    filename = sanitize_filename(filename)

    # Save the file to the destination
    filepath = os.path.join(destination, filename)
    total_size = int(response.headers.get('content-length', 0))
    download_with_progress(response, Path(filepath), total_size)
    return filepath

def sanitize_filename(filename: str) -> str:
    """
    PURPOSE: Sanitize the filename to ensure it is safe and valid.

    PARAMS:
    - filename (str): The filename to sanitize.

    RETURNS: str: The sanitized filename.
    """
    # Replace undesirable characters with underscores
    return re.sub(r'[^\w\-_\.]', '_', filename)

"""
## KNOWN ERRORS: None

## IMPROVEMENTS: Added support for custom filename patterns.

## FUTURE TODOs: Consider adding more placeholders for filename patterns.
"""
