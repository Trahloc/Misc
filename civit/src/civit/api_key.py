import os
import logging
from typing import Optional


def get_api_key() -> Optional[str]:
    """
    Get the Civitai API key from environment variable.

    The API key should be set in the CIVITAPI environment variable:
    export CIVITAPI=your_api_key_here

    RETURNS:
        Optional[str]: API key if found, None otherwise
    """
    api_key = os.environ.get("CIVITAPI")
    if not api_key:
        logging.error(
            "CIVITAPI environment variable not set. Please set it with:\n"
            "export CIVITAPI=your_api_key_here\n"
            "You can get an API key from: https://civitai.com/user/account"
        )
        return None

    # Log partial key for debugging
    visible_part = api_key[:4] if len(api_key) > 4 else ""
    logging.debug(f"Retrieved API key from environment (starts with: {visible_part}...)")
    return api_key
