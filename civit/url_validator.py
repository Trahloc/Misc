import re
import requests
from typing import Optional, Dict, Tuple, Union, List
from urllib.parse import urlparse, parse_qs


def validate_url(
    url: str, url_type: Optional[str] = None, check_existence: bool = False
) -> str:
    """
    Validate a URL and return a normalized version if valid.

    Args:
        url: URL string to validate
        url_type: Type of URL to validate ("model", "image", "api")
        check_existence: Whether to check if the URL exists

    Returns:
        str: Normalized URL if valid

    Raises:
        ValueError: If URL is invalid
        ConnectionError: If URL check fails due to connection issues
        TimeoutError: If URL check times out

    Examples:
        >>> validate_url("https://civitai.com/models/12345")
        'https://civitai.com/models/12345'
    """
    if not isinstance(url, str):
        raise ValueError("URL must be a string")

    parsed = urlparse(url)

    # Validate scheme
    if parsed.scheme not in ["http", "https"]:
        raise ValueError("Invalid URL scheme: must be http or https")

    # Type-specific validation
    if url_type == "model":
        if not is_valid_civitai_url(url):
            raise ValueError("Invalid model URL: must be a civitai.com model URL")
    elif url_type == "image":
        if not is_valid_image_url(url):
            if parsed.netloc not in [
                "image.civitai.com",
                "image-cdn.civitai.com",
            ] and not (
                parsed.netloc == "civitai.com"
                and parsed.path.startswith("/api/download/images/")
            ):
                raise ValueError("Invalid image URL domain")
            else:
                raise ValueError("Invalid image URL format")
    elif url_type == "api":
        if parsed.netloc != "civitai.com" or not parsed.path.startswith("/api/"):
            raise ValueError("Invalid API URL: must be a civitai.com API URL")

    # Check if the URL exists if requested
    if check_existence:
        try:
            response = requests.head(url, timeout=10)
            if response.status_code == 404:
                raise ValueError("URL not found")
            elif response.status_code >= 400:
                raise ValueError(
                    f"URL returned error status code: {response.status_code}"
                )
        except ConnectionError as e:
            raise ConnectionError(f"{e}")
        except TimeoutError as e:
            raise TimeoutError(f"{e}")

    return normalize_url(url)


def normalize_url(url: str) -> str:
    """
    Normalize URL format

    Args:
        url: URL to normalize

    Raises:
        ValueError: If URL is empty or invalid
    """
    if not url or not url.strip():
        raise ValueError("Empty URL provided")
    # Add logic to normalize URL
    # Example: Remove trailing slashes
    # Example: Convert to lowercase
    return url.strip()  # Placeholder for actual normalization logic


def is_valid_image_url(url: str) -> bool:
    """
    Validate if the URL is a valid Civitai image URL.

    Args:
        url: URL string to validate

    Returns:
        bool: True if URL is a valid Civitai image URL, False otherwise

    Examples:
        >>> is_valid_image_url("https://image.civitai.com/path/image.jpg")
        True
        >>> is_valid_image_url("https://example.com/image.jpg")
        False
    """
    if not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)

        # Check if the domain is valid for Civitai images
        valid_domains = ["image.civitai.com", "image-cdn.civitai.com"]
        is_api_download = parsed.netloc == "civitai.com" and parsed.path.startswith(
            "/api/download/images/"
        )

        if parsed.netloc not in valid_domains and not is_api_download:
            return False

        # For regular image domains, verify URL structure
        if parsed.netloc in valid_domains:
            # Expected format: domain/ID/optional-uuid/optional-params/filename
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 2:  # Need at least an ID and filename
                return False

        # Verify scheme is https
        if parsed.scheme != "https":
            return False

        return True
    except Exception:
        return False


def is_valid_civitai_url(url: str) -> bool:
    """
    Validate if the URL is a valid Civitai model URL.

    Args:
        url: URL string to validate

    Returns:
        bool: True if URL is a valid Civitai model URL, False otherwise

    Examples:
        >>> is_valid_civitai_url("https://civitai.com/models/12345")
        True
        >>> is_valid_civitai_url("https://example.com/models/12345")
        False
    """
    if not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)

        # Check if the domain is valid
        if parsed.netloc not in ["civitai.com", "www.civitai.com"]:
            return False

        # Check if the URL is a model URL or API download URL
        is_model_url = parsed.path.startswith("/models/")
        is_api_download = parsed.path.startswith("/api/download/models/")

        if not is_model_url and not is_api_download:
            return False

        # Verify scheme is https
        if parsed.scheme != "https":
            return False

        return True
    except Exception:
        return False
