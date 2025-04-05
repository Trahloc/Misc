"""
Filename generator for Civitai downloads.

This module provides functionality for generating custom filenames based on
model metadata from Civitai, following specific patterns.
"""

import re
import zlib
import os
import logging
from typing import Dict, Optional, Any, Tuple
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

# Regular expression for extracting version ID from URL paths
VERSION_ID_PATTERN = r"/models/(\d+)"


def calculate_crc32(data: str) -> str:
    """
    Calculate CRC32 hash of a string and return it as uppercase hex.

    Args:
        data: String to calculate CRC32 for

    Returns:
        Uppercase hex string of CRC32 hash

    Example:
        >>> calculate_crc32("test")
        '0C7E7FD8'
    """
    crc32_value = zlib.crc32(data.encode())
    return format(crc32_value & 0xFFFFFFFF, "08X")


def extract_version_id_from_url(url: str) -> Optional[str]:
    """
    Extract version ID from a Civitai URL.

    Args:
        url: Civitai URL to extract version ID from

    Returns:
        Version ID as string or None if not found

    Example:
        >>> extract_version_id_from_url("https://civitai.com/api/download/models/1448477")
        '1448477'
    """
    # First try to extract from URL path for API download URLs
    parsed_url = urlparse(url)
    path = parsed_url.path

    # Direct match for /api/download/models/{id} pattern
    if "/api/download/models/" in path:
        model_id = path.split("/api/download/models/")[-1].split("?")[0]
        if model_id and model_id.isdigit():
            return model_id

    # Try to extract from query parameters
    query_params = parse_qs(parsed_url.query)
    model_version_id = query_params.get("modelVersionId", [None])[0]

    # If not in query params, try to extract from path
    if model_version_id is None:
        if "models/" in path:
            match = re.search(r"/models/(\d+)", path)
            if match:
                model_version_id = match.group(1)

    return model_version_id


def determine_model_type(metadata: Dict[str, Any]) -> str:
    """
    Determine the model type from metadata.

    Args:
        metadata: Model metadata from Civitai API

    Returns:
        Model type identifier (e.g., 'LORA', 'MODEL', etc.)

    Example:
        >>> determine_model_type({"type": "LORA"})
        'LORA'
    """
    model_type = metadata.get("type", "")
    return model_type.upper() if model_type else "UNKNOWN"


def extract_model_info(metadata: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Extract model ID, base model name, and model name from metadata.

    Args:
        metadata: Model metadata from Civitai API

    Returns:
        Tuple of (model_id, base_model, model_name)

    Example:
        >>> extract_model_info({"id": "101892", "baseModel": "SD XL 1.0", "name": "Illustrious_XL"})
        ('101892', 'SDXL10', 'Illustrious_XL')
    """
    model_id = str(metadata.get("id", "unknown"))

    # Get base model and normalize it (remove spaces, special chars)
    base_model = metadata.get("baseModel", "")
    base_model = re.sub(r"[^a-zA-Z0-9]", "", base_model)

    # Get model name
    model_name = metadata.get("name", "")

    return model_id, base_model, model_name


def extract_original_filename(metadata: Dict[str, Any]) -> str:
    """
    Extract original filename from metadata.

    Args:
        metadata: Model metadata from Civitai API

    Returns:
        Original filename

    Example:
        >>> extract_original_filename({"files": [{"name": "model.safetensors"}]})
        'model.safetensors'
    """
    # Try to get filename from files array
    files = metadata.get("files", [])
    if files and isinstance(files, list) and len(files) > 0:
        return files[0].get("name", "unknown.safetensors")

    return "unknown.safetensors"


def generate_custom_filename(url: str, metadata: Dict[str, Any]) -> str:
    """
    Generate custom filename based on specified pattern.

    Pattern: [TYPE]-[BaseModel]-[ModelID]-[VersionID]--[ModelName]--[CRC32]-[OriginalFilename]

    Args:
        url: Download URL
        metadata: Model metadata from Civitai API

    Returns:
        Generated filename following the pattern

    Example:
        >>> generate_custom_filename(
        ...     "https://civitai.com/api/download/models/1448477",
        ...     {"id": "101892", "name": "Illustrious_XL", "baseModel": "Illustrious", "type": "LORA",
        ...      "files": [{"name": "RetroToonXL_Style-10-IL.safetensors"}]}
        ... )
        'LORA-Illustrious-101892-1448477--Illustrious_XL--A6C7C357-RetroToonXL_Style-10-IL.safetensors'
    """
    # Extract all components
    version_id = extract_version_id_from_url(url) or "unknown"
    model_type = determine_model_type(metadata)
    model_id, base_model, model_name = extract_model_info(metadata)
    original_filename = extract_original_filename(metadata)

    # Calculate CRC32 of the model name
    crc32_hash = calculate_crc32(model_name)

    # Construct filename
    filename = f"{model_type}-{base_model}-{model_id}-{version_id}--{model_name}--{crc32_hash}-{original_filename}"

    # Ensure the filename is valid for the filesystem
    filename = sanitize_filename(filename)

    return filename


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be valid for the filesystem.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename

    Example:
        >>> sanitize_filename('file/with\\invalid:chars?')
        'file_with_invalid_chars_'
    """
    # Replace characters that are invalid in filenames
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)

    # Ensure filename is not too long (max 255 characters)
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[: 255 - len(ext)] + ext

    return sanitized
