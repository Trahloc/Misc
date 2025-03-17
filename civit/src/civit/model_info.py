import logging
import requests
from typing import Optional, Dict, Any


def get_model_info(model_id: str) -> Optional[Dict[Any, Any]]:
    """
    Fetch model information from the civitai.com API.
    PARAMS:
        model_id (str): The ID of the model to fetch information for
    RETURNS:
        Optional[Dict[Any, Any]]: Model information if successful, None otherwise
    """
    api_url = f"https://civitai.com/api/v1/models/{model_id}"
    try:
        logging.debug("Fetching model info from %s", api_url)
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        logging.error("Failed to fetch model info: %s", str(e))
        return None
    except Exception as e:
        logging.error("Unexpected error fetching model info: %s", str(e))
        return None
