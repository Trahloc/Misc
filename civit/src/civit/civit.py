"""
Download files from civitai.com with proper URL handling and logging support.
This module coordinates the download process using specialized modules for each aspect.
"""

import logging
import sys
import signal
import time
from typing import Optional, Union, Tuple
from pathlib import Path
import configparser
import requests

from download_resumption import prepare_resumption
from response_handler import process_response_headers
from download_handler import download_with_progress
from url_validator import validate_url, normalize_url
from url_extraction import extract_download_url
from signal_handler import signal_handler
from logging_setup import setup_logging
from api_key import get_api_key


def download_file(
    url: str,
    output_dir: str = ".",
    api_key: Optional[str] = None,
    retries: int = 3,
    delay: int = 5,
    timeout: Union[int, Tuple[int, int]] = (30, 60),
) -> Union[str, dict]:
    """
    Coordinate the download process for a file from civitai.com.

    PARAMS:
        url (str): The URL to download from
        output_dir (str): Directory to save the downloaded file
        api_key (Optional[str]): Civitai API key for authentication
        retries (int): Number of retries for rate limiting
        delay (int): Delay between retries in seconds
        timeout (Union[int, Tuple[int, int]]): Request timeout in seconds, either a number for both connect and read
               timeouts, or a tuple of (connect_timeout, read_timeout)

    RETURNS:
        Union[str, dict]: 
            - On success: String containing the path to the downloaded file
            - On failure: Dictionary with error details:
                * 'error': Error type identifier (e.g., 'http_error', 'timeout')
                * 'message': Human-readable description of the error
                * 'status_code': HTTP status code if applicable, otherwise None
    """
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        logging.error("Failed to create output directory %s: %s", output_dir, str(e))
        return {
            'error': 'file_system_error',
            'message': f"Failed to create output directory {output_dir}: {str(e)}",
            'status_code': None
        }

    # Always try to get API key from environment if not provided
    if not api_key:
        api_key = get_api_key()
        if api_key:
            visible_part = api_key[:4] if len(api_key) > 4 else ""
            logging.debug(f"Using API key from environment (starts with: {visible_part}...)")

    for attempt in range(retries):
        if attempt > 0:
            logging.info(f"Retry attempt {attempt + 1}/{retries}")

        try:
            if not validate_url(url):
                logging.error("URL validation failed for: %s", url)
                return {
                    'error': 'invalid_url',
                    'message': f"URL validation failed for: {url}",
                    'status_code': None
                }

            normalized_url = normalize_url(url)
            if not normalized_url:
                return {
                    'error': 'url_normalization_failed',
                    'message': f"Could not normalize URL: {url}",
                    'status_code': None
                }

            # Log the state of authorization before each request
            if api_key:
                visible_part = api_key[:4] if len(api_key) > 4 else ""
                logging.debug(f"Making authenticated request with API key (starts with: {visible_part}...)")
            else:
                logging.debug("Making unauthenticated request - no API key available")

            download_url = extract_download_url(normalized_url, api_key=api_key)
            if not download_url:
                logging.error("Could not extract download URL")
                return {
                    'error': 'extract_url_failed',
                    'message': f"Could not extract download URL from: {normalized_url}",
                    'status_code': None
                }

            # Set up headers with API key for the actual download
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                logging.debug("Added Authorization header for download request")
            logging.debug(f"Request headers: {headers}")

            filepath = Path(output_dir) / "download.bin"  # Default name, will be updated from response
            _, existing_size, file_mode = prepare_resumption(filepath, headers)

            logging.info("Starting download from %s", download_url)
            logging.debug("Making download request with parameters:")
            logging.debug(f"  URL: {download_url}")
            logging.debug(f"  Headers: {headers}")
            logging.debug(f"  Stream: True")
            logging.debug(f"  Timeout: {timeout}")

            response = requests.get(
                download_url,
                stream=True,
                headers=headers,
                timeout=timeout
            )

            # Log response details in debug mode
            logging.debug(f"Response status code: {response.status_code}")
            logging.debug(f"Response headers: {dict(response.headers)}")

            if response.status_code == 401:
                logging.error("Authentication failed - please verify your API key is valid")
                logging.error("Response from server: %s", response.text)
                return {
                    'error': 'authentication_failed',
                    'message': "Authentication failed - please verify your API key is valid",
                    'status_code': 401
                }

            response.raise_for_status()

            # Process response headers to get filename and size information
            filename, total_size, is_resuming = process_response_headers(response, existing_size)
            filepath = Path(output_dir) / filename

            if is_resuming:
                logging.info(f"Resuming download from {existing_size} bytes")
            else:
                logging.info(f"Starting new download, total size: {total_size} bytes")

            # Download the file with progress tracking
            success = download_with_progress(
                response, filepath, total_size, existing_size, file_mode
            )

            if success:
                logging.info(f"Download completed successfully: {filepath}")
                return str(filepath)
            else:
                logging.error("Download failed or was incomplete")
                if attempt < retries - 1:  # Not the last attempt
                    continue
                return {
                    'error': 'download_incomplete',
                    'message': "Download failed or was incomplete",
                    'status_code': None
                }

        except requests.exceptions.HTTPError as e:
            status_code = None
            if e.response is not None:
                status_code = e.response.status_code
                logging.error(f"Response from server: {e.response.text}")
                if e.response.status_code == 401:
                    logging.error("Unauthorized - Invalid or missing API key")
                    logging.error("Please check that your API key is set correctly in the CIVITAPI environment variable")
                    return {
                        'error': 'unauthorized',
                        'message': "Unauthorized - Invalid or missing API key",
                        'status_code': 401
                    }  # Don't retry on auth errors
                elif e.response.status_code == 403:
                    logging.error("Access forbidden - API key required")
                    return {
                        'error': 'forbidden',
                        'message': "Access forbidden - API key required",
                        'status_code': 403
                    }  # Don't retry on auth errors
                elif e.response.status_code == 429:  # Rate limit exceeded
                    if attempt < retries - 1:  # Not the last attempt
                        logging.warning(f"Rate limit exceeded. Waiting {delay} seconds before retry...")
                        time.sleep(delay)
                        continue
            logging.error("HTTP error during download: %s", str(e))
            return {
                'error': 'http_error',
                'message': f"HTTP error during download: {str(e)}",
                'status_code': status_code
            }
        except requests.exceptions.Timeout:
            logging.error(f"Request timed out after {timeout} seconds")
            if attempt < retries - 1:  # Not the last attempt
                continue
            return {
                'error': 'timeout',
                'message': f"Request timed out after {timeout} seconds",
                'status_code': None
            }
        except requests.exceptions.RequestException as e:
            logging.error("Request error during download: %s", str(e))
            return {
                'error': 'request_error',
                'message': f"Request error during download: {str(e)}",
                'status_code': None
            }
        except (OSError, IOError) as e:
            logging.error("System error during download: %s", str(e))
            return {
                'error': 'system_error',
                'message': f"System error during download: {str(e)}",
                'status_code': None
            }
        except Exception as e:
            logging.error(f"Unexpected error during download: {str(e)}")
            return {
                'error': 'unexpected_error',
                'message': f"Unexpected error during download: {str(e)}",
                'status_code': None
            }

    return {
        'error': 'max_retries_exceeded',
        'message': f"Maximum retry count ({retries}) exceeded",
        'status_code': None
    }


def download_files(
    urls: list[str],
    output_dir: str = ".",
    api_key: Optional[str] = None,
    timeout: Union[int, Tuple[int, int]] = (30, 60)
) -> bool:
    """
    Download multiple files from civitai.com and save them to the specified directory.

    PARAMS:
        urls (list[str]): List of URLs to download from
        output_dir (str): Directory to save the downloaded files
        api_key (Optional[str]): Civitai API key for authentication
        timeout (Union[int, Tuple[int, int]]): Request timeout in seconds, either a number for both connect and read
               timeouts, or a tuple of (connect_timeout, read_timeout)

    RETURNS:
        bool: True if all downloads are successful, False otherwise
    """
    # Create the output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    success = True
    for url in urls:
        try:
            result = download_file(url, output_dir, api_key, timeout=timeout)
            if isinstance(result, dict):  # Error occurred
                success = False
                error_msg = result.get('message', 'Unknown error')
                error_type = result.get('error', 'unknown_error')
                status_code = result.get('status_code')
                
                if status_code:
                    logging.error(f"Failed to download {url}: {error_type} (Status: {status_code}) - {error_msg}")
                else:
                    logging.error(f"Failed to download {url}: {error_type} - {error_msg}")
            else:
                logging.info(f"Successfully downloaded to: {result}")
        except Exception as e:
            logging.error(f"Error downloading {url}: {str(e)}")
            success = False
    return success


def load_config(config_file: str) -> configparser.ConfigParser:
    """
    Load configuration settings from a file.

    PARAMS:
        config_file (str): Path to the configuration file

    RETURNS:
        configparser.ConfigParser: Loaded configuration settings
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def main() -> int:
    """
    Entry point for the civit downloader script.
    Parses command line arguments and initiates the download process.

    RETURNS:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Set up signal handling for graceful interruption
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Use dedicated CLI module for argument parsing
    from cli import parse_args
    args = parse_args()

    # Calculate verbosity level
    verbosity = sum([args.verbose, args.very_verbose * 2])
    setup_logging(verbosity)
    logging.debug("Starting civit downloader with verbosity level %d", verbosity)

    # Load configuration file if provided
    config = None
    if args.config:
        try:
            config = load_config(args.config)
        except Exception as e:
            logging.error(f"Failed to load config file: {str(e)}")
            return 1

    # Let environment variable take precedence over command line
    api_key = get_api_key() or args.api_key or (config and config.get("DEFAULT", "api_key"))

    if not api_key:
        logging.warning("No API key provided. Some downloads may fail.")

    # Create output directory if it doesn't exist
    output_dir = Path(
        args.output_dir
        or (config and config.get("DEFAULT", "output_dir", fallback="."))
    )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create output directory: {str(e)}")
        return 1

    if download_files(args.urls, str(output_dir), api_key):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""
## Current Known Errors

None - Implementation complete

## Improvements Made

- Fixed Content-Range header parsing to properly handle the format "bytes start-end/total"
- Simplified download resumption logic and removed duplicate code
- Ensure output directories are created before attempting downloads
- Updated download_files to continue downloading even when some files fail
- Fixed resumable download validation to properly check start position
- Added better error handling and logging for various download scenarios

## Future TODOs

- Add support for custom filename handling
- Add parallel download support for multiple files
- Consider adding a configuration file for default settings
- Add rate limiting handling
