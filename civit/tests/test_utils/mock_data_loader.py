import json
import os
from typing import Dict, Any, Optional


def get_mock_data_path(filename: str) -> str:
    """
    Get the absolute path to a mock data file.

    Args:
        filename: Name of the mock data file

    Returns:
        Absolute path to the mock data file
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "mock_data", filename)


def load_mock_model(model_name: str = "civitai_model.json") -> Dict[str, Any]:
    """
    Load a mock model from the mock_data directory.

    Args:
        model_name: Name of the mock model file

    Returns:
        Dict containing the mock model data
    """
    path = get_mock_data_path(model_name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_mock_version_metadata(version_id: str = "1447126") -> Dict[str, Any]:
    """
    Load a mock model version metadata from the mock_data directory.

    Args:
        version_id: ID of the version to load

    Returns:
        Dict containing the mock version metadata
    """
    path = get_mock_data_path(f"test_{version_id}_metadata.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_mock_response_for_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Return appropriate mock data based on the URL pattern.

    Args:
        url: The URL being requested

    Returns:
        Dict containing the appropriate mock data for the URL
    """
    # Model version ID extraction
    import re

    version_match = re.search(r"/models/(\d+)", url)

    if "download/models/1447126" in url:
        return load_mock_version_metadata("1447126")
    elif "download/models/1436228" in url:
        return load_mock_version_metadata("1436228")
    elif version_match:
        # Try to load based on model ID
        model_id = version_match.group(1)
        try:
            return load_mock_model()
        except FileNotFoundError:
            return None

    return None
