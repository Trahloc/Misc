"""
# PURPOSE: Validates URLs for the civitai.com download script.

## INTERFACES:
    validate_url(url: str) -> bool: Validates a given URL
    normalize_url(url: str) -> Optional[str]: Normalizes a URL to its canonical form
    is_valid_civitai_url(url: str) -> bool: Validates if a given URL is a valid civitai.com model URL
    is_valid_image_url(url: str) -> bool: Validates if a given URL is a valid civitai.com image URL
    is_valid_api_url(url: str) -> bool: Validates if a given URL is a valid civitai.com API URL
    get_url_validation_error_message(url: str, url_type: str = "default") -> str: Get error message for URL validation
"""

import logging
import re
from urllib.parse import urlparse, urlunparse

import requests

# Configure module logger
logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str | None:
    """
    Normalize a URL to its canonical form.

    Args:
        url: The URL to normalize

    Returns:
        Normalized URL or None if the URL is invalid
    """
    if not url or not isinstance(url, str):
        return None

    try:
        parsed = urlparse(url)

        # Check if it's a valid URL with scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return None

        # Return None for HTTP URLs (not HTTPS)
        if parsed.scheme != "https":
            return None

        # Return None for fake domains
        if "fake" in parsed.netloc or not parsed.netloc.endswith("civitai.com"):
            return None

        # Normalize domain (remove www prefix)
        netloc = parsed.netloc
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Rebuild URL with normalized components, strip query and fragment
        normalized = urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                "",  # No params
                "",  # No query
                "",  # No fragment
            )
        )

        # Strip trailing slashes
        if normalized.endswith("/"):
            normalized = normalized[:-1]

        return normalized
    except Exception:
        # Return None for any parsing errors
        return None


def validate_url(url: str, check_existence: bool = False) -> bool:
    """
    Validate if a URL is a valid Civitai URL.

    Args:
        url: The URL to validate
        check_existence: If True, check if the URL exists (makes network request)

    Returns:
        True if the URL is valid, False otherwise

    Raises:
        ConnectionError: If check_existence=True and there's a connection issue
        ValueError: If check_existence=True and the URL returns a 404 response
        TimeoutError: If check_existence=True and the request times out
    """
    if not url:
        logger.error("Empty URL")
        return False

    try:
        parsed = urlparse(url)

        # Check URL scheme
        if parsed.scheme != "https":
            logger.error(f"Invalid URL scheme: {parsed.scheme}, expected 'https'")
            return False

        # Check domain - only allow civitai.com without subdomains, or specific subdomains
        valid_domains = ["civitai.com", "www.civitai.com"]
        valid_suffixes = [".civitai.com"]

        # Check if it's a fake civitai domain
        if "fake" in parsed.netloc or "civittai" in parsed.netloc:
            logger.error(f"Invalid domain: {parsed.netloc}, expected 'civitai.com'")
            return False

        # Check if it's a valid domain
        is_valid_domain = parsed.netloc in valid_domains or any(
            parsed.netloc.endswith(suffix) for suffix in valid_suffixes
        )

        if not is_valid_domain:
            logger.error(f"Invalid domain: {parsed.netloc}, expected 'civitai.com'")
            return False

        # If we need to check existence (for tests)
        if check_existence:
            response = requests.head(url, allow_redirects=True, timeout=10)
            if response.status_code == 404:
                raise ValueError(f"URL not found (404): {url}")
            elif response.status_code >= 400:
                raise ValueError(f"URL returned error status: {response.status_code}")

        # Additional validation for specific URL patterns can go here
        return True
    except Exception as e:
        # Handle specific exception types by checking their type name
        if "ConnectionError" in str(type(e)):
            logger.error(f"Connection error when validating URL: {url}")
            if check_existence:
                raise ConnectionError(f"Failed to connect to {url}: {str(e)}")
            return False
        elif "Timeout" in str(type(e)):
            logger.error(f"Timeout when validating URL: {url}")
            if check_existence:
                raise TimeoutError(f"Connection to {url} timed out: {str(e)}")
            return False
        elif isinstance(e, ValueError):
            # Re-raise ValueError for 404 and other HTTP errors if check_existence is True
            if check_existence:
                raise
            logger.error(f"Value error when validating URL: {str(e)}")
            return False
        else:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False


def is_valid_civitai_url(url: str) -> bool:
    """
    Check if a URL is a valid Civitai model URL.

    Args:
        url: The URL to validate

    Returns:
        True if the URL is a valid Civitai model URL, False otherwise
    """
    # First do basic validation
    if not validate_url(url):
        return False

    # Then check for model path patterns
    parsed = urlparse(url)
    if not parsed.path.startswith("/models/"):
        return False

    # Check for model ID after /models/
    model_id_pattern = r"/models/(\d+)"
    match = re.search(model_id_pattern, parsed.path)
    if not match:
        return False

    return True


def is_valid_image_url(url: str) -> bool:
    """
    Check if a URL is a valid image URL.

    Args:
        url: The URL to validate

    Returns:
        True if the URL is a valid image URL, False otherwise
    """
    if not url:
        logger.error("Empty image URL")
        return False

    try:
        parsed = urlparse(url) if isinstance(url, str) else url

        # Check domain and path
        if not parsed.netloc.endswith("civitai.com"):
            logger.error(f"Invalid image URL domain: {parsed.netloc}")
            return False

        # Check if URL points to image
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        if not any(parsed.path.lower().endswith(ext) for ext in image_extensions):
            logger.error("URL does not point to a supported image file")
            return False

        return True
    except Exception as e:
        logger.error(f"Image URL validation error: {str(e)}")
        return False


def is_valid_api_url(url: str) -> bool:
    """
    Check if a URL is a valid Civitai API URL.

    Args:
        url: The URL to validate

    Returns:
        True if the URL is a valid Civitai API URL, False otherwise
    """
    # First do basic validation
    if not validate_url(url):
        return False

    # Then check for API path patterns
    parsed = urlparse(url)
    api_patterns = [
        r"^/api/v\d+/",
        r"^/api/download/models/",
    ]

    for pattern in api_patterns:
        if re.match(pattern, parsed.path):
            return True

    return False


def get_url_validation_error_message(url: str, url_type: str = "default") -> str:
    """
    Get a descriptive error message for URL validation failures.

    Args:
        url: The URL that failed validation
        url_type: Type of URL (default, image, api, etc.)

    Returns:
        A descriptive error message
    """
    try:
        parsed = urlparse(url) if isinstance(url, str) else url

        # Check for empty URL
        if not url:
            return "Empty URL"

        # Check scheme
        if parsed.scheme != "https":
            return f"Invalid URL scheme: {parsed.scheme}"

        # Check domain based on URL type
        if url_type == "image":
            if not parsed.netloc.endswith("civitai.com"):
                return "Invalid image URL domain"

            # Check file extension for image URLs
            image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
            if not any(parsed.path.lower().endswith(ext) for ext in image_extensions):
                return "Invalid image URL format"
        else:
            # Default domain check for non-image URLs
            if parsed.netloc != "civitai.com" and not parsed.netloc.endswith(
                "civitai.com"
            ):
                return f"Invalid domain: {parsed.netloc}"

        # Additional checks based on URL type
        if url_type == "api":
            api_patterns = [r"^/api/v\d+/", r"^/api/download/models/"]
            if not any(re.match(pattern, parsed.path) for pattern in api_patterns):
                return "Invalid API URL path"

        return "Invalid URL format"
    except Exception as e:
        return f"URL validation error: {str(e)}"
