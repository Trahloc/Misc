import hashlib
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import urlparse

import requests
from tqdm.auto import tqdm

from .test_utils import test_aware

logger = logging.getLogger(__name__)

# Rate limiting
_last_request_time = 0
_MIN_REQUEST_INTERVAL = 1.0  # Minimum seconds between requests


def _rate_limit():
    """Ensure we don't make requests too quickly."""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    if time_since_last < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - time_since_last)
    _last_request_time = time.time()


def check_existing_download(file_path: str) -> Tuple[bool, int]:
    """Check if a file exists and get its size."""
    try:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            return True, size
        return False, 0
    except Exception:
        return False, 0


@test_aware
def get_metadata_from_ids(
    model_id: str, version_id: str, api_key: Optional[str] = None
) -> Optional[Dict]:
    """Get model metadata from Civitai using model and version IDs."""
    try:
        _rate_limit()  # Apply rate limiting
        url = f"https://civitai.com/api/v1/model-versions/{version_id}"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

        logger.debug(f"Fetching model metadata from {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        logger.debug(f"Model metadata response: {response.text}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get model metadata: {e}")
        if hasattr(e.response, "status_code"):
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response text: {e.response.text}")
        return None


@test_aware
def get_metadata_from_hash(
    file_hash: str, api_key: Optional[str] = None
) -> Optional[Dict]:
    """Get model metadata from Civitai using file hash."""
    try:
        _rate_limit()  # Apply rate limiting
        url = f"https://civitai.com/api/v1/model-versions/by-hash/{file_hash}"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

        logger.debug(f"Fetching model metadata from {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        logger.debug(f"Model metadata response: {response.text}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get model metadata: {e}")
        if hasattr(e.response, "status_code"):
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response text: {e.response.text}")
        return None


def calculate_file_hash(
    filepath: str, algorithm: str = "sha256", block_size: int = 65536
) -> str:
    """
    Calculate hash of a file.

    Args:
        filepath: Path to the file
        algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')
        block_size: Size of blocks to read

    Returns:
        Hex digest of the file hash
    """
    if algorithm == "md5":
        hasher = hashlib.md5()
    elif algorithm == "sha1":
        hasher = hashlib.sha1()
    else:
        hasher = hashlib.sha256()

    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            hasher.update(block)
    return hasher.hexdigest()


def verify_download_integrity(
    filepath: str, expected_hash: Optional[str] = None, hash_type: str = "sha256"
) -> bool:
    """
    Verify the integrity of a downloaded file.

    Args:
        filepath: Path to the downloaded file
        expected_hash: Expected hash value
        hash_type: Type of hash to calculate

    Returns:
        True if integrity check passes, False otherwise
    """
    if not expected_hash:
        logger.warning("No hash provided for integrity check")
        return True

    file_hash = calculate_file_hash(filepath, hash_type)

    if file_hash.lower() == expected_hash.lower():
        logger.info(f"Integrity check passed: {hash_type} hash matches")
        return True
    else:
        logger.warning(f"Integrity check failed: {hash_type} hash mismatch")
        logger.warning(f"Expected: {expected_hash}")
        logger.warning(f"Got: {file_hash}")
        return False


def get_direct_download_url(
    model_id: str, api_key: Optional[str] = None, query_params: Optional[str] = None
) -> Optional[Tuple[str, Dict[str, str], requests.Response]]:
    """Get the direct download URL from Civitai API.

    Returns:
        Tuple of (download_url, response_headers, response) or None if failed
    """
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Use the download API endpoint with query parameters
        base_url = f"https://civitai.com/api/download/models/{model_id}"
        download_url = f"{base_url}{query_params if query_params else ''}"
        logger.debug(f"Fetching download URL from {download_url}")
        logger.debug(f"Request headers: {headers}")
        response = requests.get(
            download_url,
            headers=headers,
            timeout=(5, None),
            allow_redirects=True,
            stream=True,
        )
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")

        if response.status_code == 401:
            logger.error(
                "Authentication required. Please provide an API key using the CIVITAPI environment variable."
            )
            logger.error(f"Response: {response.text}")
            return None

        if response.status_code == 404:
            logger.error(f"Download URL not found. Full response: {response.text}")
            return None

        response.raise_for_status()

        # Return the final URL, headers, and the response object
        final_url = response.url
        logger.debug(f"Got final download URL: {final_url}")
        return final_url, dict(response.headers), response

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error getting direct download URL: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response headers: {dict(e.response.headers)}")
            logger.error(f"Response text: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting direct download URL: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return None


@test_aware
def download_file(
    url: str,
    output_dir: Union[str, Path],
    api_key: Optional[str] = None,
    resume: bool = False,
    filename: Optional[str] = None,
    custom_name: Optional[str] = None,
    timeout: Tuple[int, Optional[int]] = (5, 30),
) -> Union[str, Dict[str, Any]]:
    """
    Download a file from a URL to the specified directory.

    This function handles the entire download process including:
    - Validating and preparing the download URL
    - Getting file details with a HEAD request
    - Determining the appropriate filename
    - Setting up resume capabilities if supported
    - Downloading the file with progress tracking
    - Validating the download completion

    The function implements error handling for various network and server issues:
    - Connection timeouts
    - Read timeouts
    - HTTP errors (404, 403, etc.)
    - Connection errors
    - General request errors

    Args:
        url (str): The URL to download the file from. Should be a valid HTTP/HTTPS URL.
        output_dir (Union[str, Path]): Directory where the file will be saved. Will be created if it doesn't exist.
        api_key (Optional[str], optional): API key for authentication with Civitai API. Defaults to None.
        resume (bool, optional): Whether to attempt to resume interrupted downloads. Defaults to False.
        filename (Optional[str], optional): Override the filename from the URL/headers. Defaults to None.
        custom_name (Optional[str], optional): Custom filename that takes precedence over all other naming methods. Defaults to None.
        timeout (Tuple[int, Optional[int]], optional): Connection and read timeout in seconds (connect_timeout, read_timeout). Defaults to (5, 30).

    Returns:
        Union[str, Dict[str, Any]]:
            - On success: The full path to the downloaded file (str)
            - On failure: A dictionary with error details with the following keys:
                * 'error': Error type identifier (e.g., 'connection_timeout', 'http_error')
                * 'message': Human-readable description of the error
                * 'status_code': HTTP status code if applicable, otherwise None

            Possible error types include:
                * 'invalid_api_key': The API key format is invalid
                * 'connection_timeout': Connection to the server timed out
                * 'read_timeout': The server took too long to respond or send data
                * 'http_error': HTTP error occurred (e.g., 404, 403)
                * 'connection_error': Failed to establish connection to the server
                * 'request_error': General request error
                * 'unexpected_error': Any other unexpected error during download

    Examples:
        # Basic download
        result = download_file("https://example.com/file.zip", "/downloads")
        if isinstance(result, str):
            print(f"Download successful: {result}")
        else:
            print(f"Download failed: {result['message']}")

        # Download with resume and custom name
        result = download_file(
            "https://civitai.com/api/download/models/12345",
            "/downloads",
            api_key="your_api_key",
            resume=True,
            custom_name="my_custom_filename.zip"
        )
    """
    try:
        # Convert output_dir to Path if it's a string
        output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Setup base headers (used for HEAD initially)
        head_headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

        # Validate API key format if provided
        if api_key and not isinstance(api_key, str):
            return {
                "error": "invalid_api_key",
                "message": "API key must be a string",
                "status_code": None,
            }

        try:
            # Get head response for filename and resume support
            head_response = requests.head(
                url, headers=head_headers, timeout=timeout, allow_redirects=True
            )
            head_response.raise_for_status()  # Check HEAD request status
        except requests.exceptions.ConnectTimeout:
            return {
                "error": "connection_timeout",
                "message": f"Connection timed out when attempting to connect to {url}",
                "status_code": None,
            }
        except requests.exceptions.ReadTimeout:
            return {
                "error": "read_timeout",
                "message": f"Server took too long to respond from {url}",
                "status_code": None,
            }
        except requests.exceptions.HTTPError as e:
            return {
                "error": "http_error",
                "message": f"HTTP error occurred: {str(e)}",
                "status_code": e.response.status_code
                if hasattr(e, "response")
                else None,
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "connection_error",
                "message": f"Failed to connect to {url}. Check your internet connection.",
                "status_code": None,
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": "request_error",
                "message": f"Request error: {str(e)}",
                "status_code": getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None,
            }

        output_filename = (
            custom_name
            if custom_name
            else (
                filename
                if filename
                else _extract_filename_from_response(head_response, url)
            )
        )

        # Create full output path
        output_path = output_dir / output_filename

        # Check if file exists and get its size
        exists, size = check_existing_download(str(output_path))

        # Prepare headers for the GET request (start with head_headers)
        get_headers = head_headers.copy()

        # Check if server supports resume and modify GET headers if needed
        supports_resume = False
        if resume and exists:
            supports_resume = "accept-ranges" in map(
                str.lower, head_response.headers.keys()
            )  # Case-insensitive check
            if supports_resume:
                get_headers["Range"] = f"bytes={size}-"
                logger.info(f"Resuming download from byte {size}")
            else:
                logger.info(
                    "Server does not support resume or file doesn't exist; starting download from beginning."
                )

        try:
            # Download the file using GET headers
            response = requests.get(
                url, headers=get_headers, stream=True, timeout=timeout
            )
            response.raise_for_status()  # Raise an exception for bad status codes
        except requests.exceptions.ConnectTimeout:
            return {
                "error": "connection_timeout",
                "message": f"Connection timed out when attempting to download from {url}",
                "status_code": None,
            }
        except requests.exceptions.ReadTimeout:
            return {
                "error": "read_timeout",
                "message": f"Download timed out. Server took too long to send data from {url}",
                "status_code": None,
            }
        except requests.exceptions.HTTPError as e:
            return {
                "error": "http_error",
                "message": f"HTTP error occurred during download: {str(e)}",
                "status_code": e.response.status_code
                if hasattr(e, "response")
                else None,
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "connection_error",
                "message": f"Connection lost while downloading from {url}",
                "status_code": None,
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": "request_error",
                "message": f"Error during download: {str(e)}",
                "status_code": getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None,
            }

        # Determine total size and initial size based on resume status
        if resume and exists and supports_resume and response.status_code == 206:
            # Partial content response
            content_range = response.headers.get("content-range", "bytes 0-0/0")
            total_size = int(content_range.split("/")[1])
            initial_size = size
            mode = "ab"  # Append mode
        else:
            # Full download or resume not possible/needed
            total_size = int(response.headers.get("content-length", 0))
            initial_size = 0
            mode = "wb"  # Write mode (overwrite)

        # Check if total_size is valid
        if total_size == 0:
            logger.warning(
                "Content-Length header missing or zero, cannot show progress accurately."
            )
            total_size = None  # Set to None for indeterminate progress bar

        with open(output_path, mode) as f:
            with tqdm(
                total=total_size,
                initial=initial_size,
                unit="B",
                unit_scale=True,
                desc=output_filename,
                leave=False,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        # Final size check after download
        final_size = os.path.getsize(output_path)
        if total_size is not None and final_size != total_size:
            logger.warning(
                f"Download completed, but final size ({final_size}) does not match expected total size ({total_size})."
            )
            # Consider if this should raise an error or just warn

        return str(output_path)
    except Exception as e:
        logger.error(f"Unexpected error during download: {str(e)}")
        return {
            "error": "unexpected_error",
            "message": f"An unexpected error occurred during download: {str(e)}",
            "status_code": None,
        }


def _extract_filename_from_response(response: requests.Response, url: str) -> str:
    """Extract filename from response headers or URL."""
    # Try to get filename from Content-Disposition header
    content_disposition = response.headers.get("Content-Disposition", "")
    if content_disposition:
        matches = re.findall(
            "filename[^;=\n]*=((['\"]).*?\2|[^;\n]*)", content_disposition
        )
        if matches:
            filename = matches[0][0].strip("\"'")
            return filename

    # Fallback to URL path
    url_path = urlparse(url).path
    filename = os.path.basename(url_path)
    return filename.split("?")[0]  # Remove query parameters
