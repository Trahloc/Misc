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
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests
import blake3
import re
from .filename_generator import generate_custom_filename, extract_model_components
from .download_handler import get_model_metadata

logger = logging.getLogger(__name__)

def calculate_blake3_hash(filepath: Path) -> str:
    """Calculate BLAKE3 hash of a file."""
    hasher = blake3.blake3()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def matches_custom_format(filename: str) -> bool:
    """Check if a filename matches our custom format."""
    # Example format: LORA-Illustrious-1204563-1447126-Style_B-EA1FC919-114441204-ma1ma1helmes_b-000014.safetensors
    pattern = r'^[A-Z]+-[^-]+-\d+-\d+-[^-]+-[A-F0-9]{8}-\d+-[^.]+\.(safetensors|pt|ckpt|pth)$'
    return bool(re.match(pattern, filename))

def extract_ids_from_custom_format(filename: str) -> Optional[Tuple[str, str]]:
    """Extract model ID and version ID from a custom format filename."""
    pattern = r'^[A-Z]+-[^-]+-(\d+)-(\d+)-'
    match = re.match(pattern, filename)
    if match:
        return match.group(1), match.group(2)
    return None

def extract_ids_from_original_format(filename: str) -> Optional[Tuple[str, str]]:
    """Extract model ID and version ID from an original format filename."""
    # Example: FLUX_[pro]_1.1_Style_Lora_Extreme_Detailer_for_[FLUX_+_ILLUSTRIOUS]-vFLUX_v0.1_strong_version
    # Try to find version ID in the filename
    version_pattern = r'v(\d+)'
    version_match = re.search(version_pattern, filename)
    if not version_match:
        return None
        
    version_id = version_match.group(1)
    
    # For model ID, we'll need to search Civitai
    return None, version_id

def get_metadata_from_ids(model_id: Optional[str], version_id: Optional[str], api_key: Optional[str] = None) -> Optional[Dict]:
    """Get model metadata from Civitai API using model and version IDs."""
    try:
        if version_id:
            # Try to get metadata directly from version ID
            return get_model_metadata(version_id, api_key)
            
        if model_id:
            # If we only have model ID, get the latest version
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                
            url = f"https://civitai.com/api/v1/models/{model_id}"
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data.get('modelVersions'):
                # Get the first (latest) version
                version_id = data['modelVersions'][0]['id']
                return get_model_metadata(version_id, api_key)
                
        return None
    except Exception as e:
        logger.error(f"Failed to get metadata from IDs: {e}")
        return None

def get_metadata_from_hash(file_hash: str, api_key: Optional[str] = None) -> Optional[Dict]:
    """Get model metadata from Civitai API using file hash."""
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        # Use the correct endpoint for hash lookup
        url = f"https://civitai.com/api/v1/model-versions/by-hash/{file_hash}"
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        # The response is already in the correct format (model version metadata)
        return response.json()
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"No model version found with hash {file_hash}")
        else:
            logger.error(f"Failed to get metadata from hash: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to get metadata from hash: {e}")
        return None

def get_metadata_for_file(filepath: Path, api_key: Optional[str] = None) -> Optional[Dict]:
    """Get metadata for a file using multiple methods."""
    filename = filepath.name
    
    # First try to extract IDs from custom format
    ids = extract_ids_from_custom_format(filename)
    if ids:
        model_id, version_id = ids
        metadata = get_metadata_from_ids(model_id, version_id, api_key)
        if metadata:
            return metadata
            
    # Then try to extract IDs from original format
    ids = extract_ids_from_original_format(filename)
    if ids:
        model_id, version_id = ids
        metadata = get_metadata_from_ids(model_id, version_id, api_key)
        if metadata and 'files' in metadata and metadata['files']:
            return metadata
            
    # If we got metadata but no file info, or if ID lookup failed,
    # fall back to hash lookup
    logger.debug("Falling back to hash lookup")
    file_hash = calculate_blake3_hash(filepath)
    return get_metadata_from_hash(file_hash, api_key)

def verify_file(filepath: Path, api_key: Optional[str] = None, rename: bool = False, extensions: Optional[list[str]] = None, force_process: bool = False) -> bool:
    """
    Verify a single file and optionally rename it to match the custom format.
    
    Args:
        filepath: Path to the file to verify
        api_key: Optional API key for Civitai
        rename: Whether to rename files that don't match the format
        extensions: Optional list of file extensions to process
        force_process: Whether to process the file regardless of extension
        
    Returns:
        bool: True if file is valid or was successfully renamed
    """
    if not filepath.exists():
        logger.error(f"File does not exist: {filepath}")
        return False
        
    # Check if file has a supported extension, unless force_process is True
    if not force_process and extensions and filepath.suffix.lower() not in extensions:
        logger.debug(f"Skipping {filepath.name} - not a supported file type")
        return True  # Return True since this isn't a failure, just a skip
        
    if matches_custom_format(filepath.name):
        logger.info(f"File {filepath.name} already matches custom format")
        return True
        
    if not rename:
        logger.warning(f"File {filepath.name} does not match custom format")
        return False
        
    # Get metadata using multiple methods
    metadata = get_metadata_for_file(filepath, api_key)
    
    if not metadata:
        logger.error(f"Could not find metadata for file {filepath.name}")
        return False
        
    # Generate new filename
    new_filename = generate_custom_filename(metadata)
    if not new_filename:
        logger.error(f"Failed to generate new filename for {filepath.name}")
        return False
        
    # Rename the file
    try:
        new_path = filepath.parent / new_filename
        if new_path.exists():
            logger.warning(f"Target filename {new_filename} already exists")
            return False
            
        filepath.rename(new_path)
        logger.info(f"Renamed {filepath.name} to {new_filename}")
        return True
    except OSError as e:
        logger.error(f"Failed to rename file: {e}")
        return False

def verify_directory(directory: Path, api_key: Optional[str] = None, rename: bool = False, extensions: Optional[list[str]] = None) -> Dict[str, bool]:
    """
    Verify all files in a directory and optionally rename them.
    
    Args:
        directory: Directory to verify
        api_key: Optional API key for Civitai
        rename: Whether to rename files that don't match the format
        extensions: Optional list of file extensions to process
        
    Returns:
        Dict mapping filenames to verification status
    """
    if not directory.exists():
        logger.error(f"Directory does not exist: {directory}")
        return {}
        
    if not directory.is_dir():
        logger.error(f"Path is not a directory: {directory}")
        return {}
        
    results = {}
    for filepath in directory.glob('*'):
        if filepath.is_file():
            results[str(filepath)] = verify_file(filepath, api_key, rename, extensions, force_process=False)
            
    return results 