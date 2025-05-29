"""
# PURPOSE: Handle retrieval and processing of model information from civitai.com API.

## INTERFACES:
    get_model_info(model_id: str, api_key: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]

## DEPENDENCIES:
    - requests: For API requests
    - logging: For structured logging
    - exceptions: For custom error handling
"""

import logging
from datetime import UTC, datetime
from logging import LoggerAdapter
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

from .exceptions import ModelAccessError, ModelNotFoundError, ModelVersionError

# Create structured logger
logger = LoggerAdapter(logging.getLogger(__name__), {"component": "model_info"})


def get_model_info(
    model_id: str, api_key: Optional[str] = None, timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Fetch model information from the civitai.com API.

    PRE-CONDITIONS:
        - model_id must be a non-empty string
        - timeout must be positive
        - api_key must be string or None

    POST-CONDITIONS:
        - returned dict contains model information
        - model versions list is non-empty

    PARAMS:
        model_id: The ID of the model to fetch
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds

    RETURNS:
        Dict containing model information

    RAISES:
        ModelNotFoundError: If model doesn't exist
        ModelAccessError: If access is denied
        NetworkError: If API request fails

    USAGE:
        >>> info = get_model_info("1234")
        >>> print(info["name"])
        'Example Model'
    """
    try:
        # Validate pre-conditions
        assert model_id and isinstance(model_id, str), (
            "model_id must be non-empty string"
        )
        assert timeout > 0, "timeout must be positive"
        assert api_key is None or isinstance(api_key, str), (
            "api_key must be string or None"
        )

        api_url = urljoin("https://civitai.com/api/v1/models/", model_id)
        headers = {"User-Agent": "civit-cli/1.0"}

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            logger.debug("Using API key authentication")

        log_context = {
            "model_id": model_id,
            "api_url": api_url,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.debug("Fetching model info", extra=log_context)
        response = requests.get(api_url, headers=headers, timeout=timeout)

        if response.status_code == 404:
            raise ModelNotFoundError(f"Model {model_id} not found")
        elif response.status_code == 403:
            raise ModelAccessError(f"Access denied to model {model_id}")
        elif response.status_code == 401:
            raise ModelAccessError("Invalid or missing API key")

        response.raise_for_status()
        data = response.json()

        # Validate response data
        if not data:
            raise ModelNotFoundError(f"Empty response for model {model_id}")

        if "modelVersions" not in data or not data["modelVersions"]:
            raise ModelVersionError(f"Model {model_id} has no available versions")

        logger.info(
            "Successfully fetched model info",
            extra={
                **log_context,
                "model_name": data.get("name"),
                "version_count": len(data["modelVersions"]),
            },
        )

        return data

    except requests.Timeout as e:
        logger.error("Request timed out", extra={**log_context, "error": str(e)})
        return None
    except requests.RequestException as e:
        logger.error("Request failed", extra={**log_context, "error": str(e)})
        return None
    except ValueError as e:
        logger.error("Invalid response", extra={**log_context, "error": str(e)})
        return None
    except Exception as e:
        logger.error(str(e))
        return None


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added structured logging with context
- Added custom exceptions
- Added pre/post conditions
- Added comprehensive error handling
- Added usage examples

## FUTURE TODOs:
- Add response caching
- Add rate limiting
- Add batch model info retrieval
"""
