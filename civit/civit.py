from typing import Dict, Any, Optional
import re
import logging
import requests
from urllib.parse import urlparse
from filename_generator import extract_version_id_from_url
from download_handler import DownloadHandler
import sys
import tqdm
import os

logger = logging.getLogger(__name__)

def get_model_metadata(url: str) -> Optional[Dict[str, Any]]:
    """
    Get model metadata from Civitai API based on the URL.

    Args:
        url: URL of the model

    Returns:
        Model metadata dict or None if not available
    """
    try:
        # Extract version ID from the URL
        version_id = extract_version_id_from_url(url)
        if not version_id:
            logger.warning(f"Could not extract version ID from URL: {url}")
            return None

        logger.debug(f"Extracted version ID: {version_id} from URL: {url}")

        # Construct API URL to get model version info
        api_url = f"https://civitai.com/api/v1/model-versions/{version_id}"
        logger.debug(f"Requesting version data from: {api_url}")

        # Make API request
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        version_data = response.json()
        logger.debug(f"Received version data for ID: {version_id}")

        # Fetch model info using model ID from version data
        model_id = version_data.get('modelId')
        if not model_id:
            logger.warning("Model ID not found in version data")
            return None
        model_api_url = f"https://civitai.com/api/v1/models/{model_id}"
        logger.debug(f"Model ID from version data: {model_id}")
        logger.debug(f"Requesting model data from: {model_api_url}")

        model_response = requests.get(model_api_url, timeout=10)
        model_response.raise_for_status()
        model_data = model_response.json()
        logger.debug(f"Received model data for ID: {model_id}")

        # Combine data for our metadata format
        metadata = {
            "id": model_id,
            "name": model_data.get('name', ''),
            "baseModel": model_data.get('baseModel', ''),
            "type": model_data.get('type', ''),
            "files": version_data.get('files', [])
        }
        logger.info(f"Retrieved metadata for model: {metadata['name']}, type: {metadata['type']}, baseModel: {metadata['baseModel']}")
        return metadata
    except Exception as e:
        logger.warning(f"Failed to retrieve model metadata: {str(e)}")
        if "-v" in sys.argv:
            import traceback
            logger.debug(f"Metadata retrieval traceback: {traceback.format_exc()}")
        return None

def download_model(model_url: str, output_dir: str, use_custom_naming: bool = True, overwrite: bool = False) -> str:
    """
    Download a model from Civitai.

    Args:
        model_url: URL of the model to download
        output_dir: Directory to save the model to
        use_custom_naming: Whether to use custom naming pattern
        overwrite: Whether to overwrite existing files

    Returns:
        Path to the downloaded file
    """
    # Validate URL
    if not validate_url(model_url):
        raise ValueError(f"Invalid URL: {model_url}")

    # Set up progress bar for downloads
    def progress_callback(downloaded, total):
        filename = os.path.basename(output_dir)
        progress = downloaded / total if total > 0 else 0
        tqdm.write(f"\rDownloading {filename}: {progress:.1%}", end="")

    # Fetch model metadata if we're using custom naming
    metadata = None
    if use_custom_naming:
        logger.info("Fetching model metadata for custom filename...")
        metadata = get_model_metadata(model_url)
        if metadata:
            logger.info(f"Using custom naming for {metadata.get('name', 'unknown model')}")
        else:
            logger.warning("Could not retrieve model metadata, will use default filename")

    # Pass the metadata and custom naming flag to the download handler
    download_handler = DownloadHandler()
    downloaded_file = download_handler.download_file(
        model_url,
        output_dir,
        progress_callback=progress_callback,
        metadata=metadata,
        use_custom_naming=use_custom_naming,
        overwrite=overwrite
    )

    return downloaded_file

def parse_arguments():
    # ...existing code...

    # Add overwrite argument
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        help="Overwrite existing files"
    )
    parser.set_defaults(overwrite=False)

    # Add a new argument for toggling custom naming
    parser.add_argument(
        "--custom-naming",
        dest="custom_naming",
        action="store_true",
        help="Use custom naming pattern for downloaded files"
    )
    parser.add_argument(
        "--no-custom-naming",
        dest="custom_naming",
        action="store_false",
        help="Disable custom naming pattern for downloaded files"
    )
    parser.set_defaults(custom_naming=True)

def main():
    # ...existing code...

    try:
        # Pass the custom naming and overwrite flags to the download function
        downloaded_file = download_model(
            args.url,
            args.output_dir,
            use_custom_naming=args.custom_naming,
            overwrite=args.overwrite
        )
        # ...existing code...
