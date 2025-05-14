"""
# PURPOSE: Verify and optionally rename files to match the custom format.

## INTERFACES:
    verify_file(filepath: Path, api_key: Optional[str] = None, rename: bool = False, extensions: Optional[list[str]] = None) -> bool
    verify_directory(directory: Path, api_key: Optional[str] = None, rename: bool = False, extensions: Optional[list[str]] = None) -> Dict[str, bool]

## DEPENDENCIES:
    pathlib: Path handling
    logging: Logging functionality
    requests: API calls
    blake3: File hashing
    re: Regular expressions
"""

import logging
import os
import re
from typing import Dict, List, Optional, Tuple

import blake3

from .download_handler import get_metadata_from_hash, get_metadata_from_ids
from .filename_generator import generate_custom_filename

logger = logging.getLogger(__name__)


def calculate_blake3_hash(filepath: str) -> str:
    """Calculate BLAKE3 hash of a file."""
    try:
        hasher = blake3.blake3()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except ImportError:
        logger.error(
            "BLAKE3 library not found. Please install it with: pip install blake3"
        )
        return None


def check_filename_format(filename: str) -> bool:
    """Check if filename matches our custom format."""
    # Format: LORA-Flux_1_D-{model_name}-{model_id}-{crc32}-{file_size}-{original_filename}
    parts = filename.split("-")
    if len(parts) < 6:  # Need at least 6 parts for our format
        return False

    # Check if first part is LORA-Flux_1_D
    if not parts[0].startswith("LORA-Flux_1_D"):
        return False

    # Check if last part is the original filename
    if not parts[-1]:
        return False

    return True


def extract_ids_from_custom_format(filename: str) -> Optional[Tuple[str, str]]:
    """Extract model ID and version ID from a custom format filename."""
    pattern = r"^[A-Z]+-[^-]+-(\d+)-(\d+)-"
    match = re.match(pattern, filename)
    if match:
        return match.group(1), match.group(2)
    return None


def extract_ids_from_original_format(filename: str) -> Optional[Tuple[str, str]]:
    """Extract model ID and version ID from an original format filename."""
    # Example: FLUX_[pro]_1.1_Style_Lora_Extreme_Detailer_for_[FLUX_+_ILLUSTRIOUS]-vFLUX_v0.1_strong_version
    # Try to find version ID in the filename
    version_pattern = r"v(\d+)"
    version_match = re.search(version_pattern, filename)
    if not version_match:
        return None

    version_id = version_match.group(1)

    # For model ID, we'll need to search Civitai
    return None, version_id


def get_metadata_from_file(
    filepath: str, api_key: Optional[str] = None
) -> Optional[Dict]:
    """Get model metadata by calculating file hash and querying Civitai API."""
    # Calculate BLAKE3 hash
    file_hash = calculate_blake3_hash(filepath)
    if not file_hash:
        return None

    # Try to get metadata from hash
    metadata = get_metadata_from_hash(file_hash, api_key)
    if metadata:
        return metadata

    # If hash lookup fails, try to extract IDs from filename
    filename = os.path.basename(filepath)
    if check_filename_format(filename):
        parts = filename.split("-")
        model_id = parts[2]  # Model ID is the third part
        version_id = parts[2]  # For now, use model ID as version ID
        return get_metadata_from_ids(model_id, version_id, api_key)

    return None


def verify_file(
    filepath: str,
    rename: bool = False,
    api_key: Optional[str] = None,
    extensions: Optional[List[str]] = None,
) -> bool:
    """Verify a single file and optionally rename it to match custom format."""
    if extensions is None:
        extensions = [".safetensors", ".pt", ".ckpt", ".pth"]

    try:
        filepath = os.path.abspath(filepath)
        logger.info(f"Verifying file: {filepath}")

        # Check if filename already matches our format
        filename = os.path.basename(filepath)
        if check_filename_format(filename):
            logger.info(f"File already matches custom format: {filename}")
            return True

        # Get metadata from Civitai
        metadata = get_metadata_from_file(filepath, api_key)
        if not metadata:
            logger.warning(f"Could not get metadata for file: {filepath}")
            return False

        if rename:
            # Generate new filename
            new_filename = generate_custom_filename(metadata)
            if not new_filename:
                logger.error(f"Failed to generate custom filename for: {filepath}")
                return False

            # Rename file
            new_path = os.path.join(os.path.dirname(filepath), new_filename)
            try:
                os.rename(filepath, new_path)
                logger.info(f"Renamed file to: {new_filename}")
            except OSError as e:
                logger.error(f"Failed to rename file: {e}")
                return False

        return True
    except Exception as e:
        logger.error(f"Error verifying file {filepath}: {e}")
        return False


def verify_directory(
    directory: str,
    rename: bool = False,
    api_key: Optional[str] = None,
    extensions: Optional[List[str]] = None,
    recursive: bool = False,
) -> bool:
    """Verify all files in a directory and optionally rename them to match custom format.

    Args:
        directory: Directory to verify
        rename: Whether to rename files that don't match the format
        api_key: Optional API key for Civitai
        extensions: List of file extensions to process
        recursive: Whether to process subdirectories recursively

    Returns:
        bool: True if all files were verified successfully
    """
    if extensions is None:
        extensions = [".safetensors", ".pt", ".ckpt", ".pth"]

    try:
        directory = os.path.abspath(directory)
        logger.info(f"Verifying directory: {directory}")

        success = True
        for entry in os.listdir(directory):
            path = os.path.join(directory, entry)
            if os.path.isfile(path):
                # Only check extension for files in directory mode
                if not any(path.lower().endswith(ext.lower()) for ext in extensions):
                    logger.debug(f"Skipping unsupported file type: {path}")
                    continue
                if not verify_file(path, rename, api_key, extensions):
                    success = False
            elif os.path.isdir(path) and recursive:
                if not verify_directory(path, rename, api_key, extensions, recursive):
                    success = False

        return success
    except Exception as e:
        logger.error(f"Error verifying directory {directory}: {e}")
        return False
