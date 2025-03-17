import re
import logging
from typing import Optional
from model_info import get_model_info


def extract_model_id(url: str) -> Optional[str]:
    """
    Extract the model ID from a civitai.com URL.
    PARAMS:
        url (str): The normalized civitai.com URL
    RETURNS:
        Optional[str]: The model ID if found, None otherwise
    """
    try:
        # Match /models/{id} pattern
        match = re.search(r"/models/(\d+)", url)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        logging.error(f"Failed to extract model ID: {str(e)}")
        return None


def extract_download_url(url: str) -> Optional[str]:
    """
    Extract the actual download URL from a civitai.com URL using the API.
    If the URL is already a direct download URL, return it as is.
    PARAMS:
        url (str): The normalized civitai.com URL
    RETURNS:
        Optional[str]: The actual download URL if found, None otherwise
    """
    # If it's already a direct download URL, return it
    if "/api/download/models/" in url:
        return url
    # Otherwise, try to extract model ID and get download URL from API
    model_id = extract_model_id(url)
    if not model_id:
        logging.error("Could not extract model ID from URL")
        return None
    model_info = get_model_info(model_id)
    if not model_info:
        return None
    try:
        # Get the latest version's download URL
        latest_version = model_info["modelVersions"][0]
        download_url = latest_version["downloadUrl"]
        logging.debug(f"Found download URL: {download_url}")
        return download_url
    except (KeyError, IndexError) as e:
        logging.error(f"Failed to extract download URL from API response: {str(e)}")
        return None
