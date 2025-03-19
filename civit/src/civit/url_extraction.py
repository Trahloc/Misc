import re
import logging
from typing import Optional
from .model_info import get_model_info


def extract_model_id(url: str) -> Optional[str]:
    """
    Extract the model ID from a civitai.com URL.
    PARAMS:
        url (str): The normalized civitai.com URL
    RETURNS:
        Optional[str]: The model ID if found, None otherwise
    """
    try:
        logging.debug(f"Extracting model ID from URL: {url}")
        # Match both /models/{id} and /api/download/models/{id} patterns
        match = re.search(r"/(?:api/download/)?models/(\d+)", url)
        if match:
            model_id = match.group(1)
            logging.debug(f"Found model ID: {model_id}")
            return model_id
        logging.error(f"Could not find model ID in URL: {url}")
        return None
    except Exception as e:
        logging.error(f"Failed to extract model ID: {str(e)}")
        return None


def extract_download_url(url: str, api_key: Optional[str] = None) -> Optional[str]:
    """
    Extract the actual download URL from a civitai.com URL using the API.
    If the URL is already a direct download URL, return it as is.
    PARAMS:
        url (str): The normalized civitai.com URL
        api_key (Optional[str]): The API key for authentication
    RETURNS:
        Optional[str]: The actual download URL if found, None otherwise
    """
    # If it's already a direct download URL, return it
    if "/api/download/models/" in url:
        logging.debug(f"URL is already a direct download URL: {url}")
        return url

    # Try to extract model ID and get download URL from API
    model_id = extract_model_id(url)
    if not model_id:
        logging.error("Could not extract model ID from URL")
        return None

    logging.info(f"Fetching model info for model ID: {model_id}")
    model_info = get_model_info(model_id, api_key=api_key)
    if not model_info:
        logging.error(f"Could not fetch model info for model ID: {model_id}")
        return None

    try:
        # Get the latest version's download URL
        latest_version = model_info["modelVersions"][0]
        download_url = latest_version["downloadUrl"]
        logging.debug(f"Found download URL: {download_url}")
        return download_url
    except (KeyError, IndexError) as e:
        logging.error(
            f"Failed to extract download URL from API response: {str(e)}\n"
            f"Response structure may have changed or model {model_id} may not be available"
        )
        return None
    except Exception as e:
        logging.error(f"Unexpected error extracting download URL: {str(e)}")
        return None
