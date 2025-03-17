import os
import logging
from typing import Optional


def get_api_key() -> Optional[str]:
    """
    Get the Civitai API key from environment variable.
    RETURNS:
        Optional[str]: API key if found, None otherwise
    """
    api_key = os.environ.get("CIVITAPI")
    if not api_key:
        logging.error("CIVITAPI environment variable not set")
        return None
    return api_key
