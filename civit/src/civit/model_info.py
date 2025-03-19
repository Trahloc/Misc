import logging
import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin


def get_model_info(model_id: str, api_key: Optional[str] = None, timeout: int = 30) -> Optional[Dict[Any, Any]]:
    """
    Fetch model information from the civitai.com API.

    PARAMS:
        model_id (str): The ID of the model to fetch information for
        api_key (Optional[str]): The API key for authentication
        timeout (int): Request timeout in seconds

    RETURNS:
        Optional[Dict[Any, Any]]: Model information if successful, None otherwise
    """
    api_url = urljoin("https://civitai.com/api/v1/models/", model_id)

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        logging.debug("Using API key for authentication")

    try:
        logging.debug("Fetching model info from %s", api_url)
        response = requests.get(api_url, headers=headers, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        if not data:
            logging.error("Received empty response from API")
            return None

        if "modelVersions" not in data or not data["modelVersions"]:
            logging.error("Model has no available versions")
            return None

        logging.debug("Successfully fetched model info")
        return data

    except requests.exceptions.Timeout:
        logging.error("Request timed out after %d seconds", timeout)
        return None
    except requests.exceptions.HTTPError as e:
        if e.response is not None:
            if e.response.status_code == 404:
                logging.error("Model not found (404)")
            elif e.response.status_code == 403:
                logging.error("Access forbidden - API key may be required")
            elif e.response.status_code == 401:
                logging.error("Unauthorized - Invalid or missing API key")
            elif e.response.status_code == 429:
                logging.error("Rate limit exceeded")
            else:
                logging.error("HTTP error %d: %s", e.response.status_code, str(e))
        return None
    except requests.exceptions.RequestException as e:
        logging.error("Request failed: %s", str(e))
        return None
    except ValueError as e:
        logging.error("Failed to parse API response: %s", str(e))
        return None
    except Exception as e:
        logging.error("Unexpected error fetching model info: %s", str(e))
        return None
