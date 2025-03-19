# FILE: src/civit/filename_pattern.py
"""
# PURPOSE: Handles filename pattern parsing and validation for custom filenames.

## INTERFACES: process_filename_pattern(pattern: str, metadata: dict, original_filename: str) -> str: Process a filename pattern with metadata and returns a valid filename.

## DEPENDENCIES: re, os, zlib, logging - For regular expressions, file operations, CRC32 computation, and logging.

## TODO: None
"""

import re
import os
import zlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional


def process_filename_pattern(pattern: str, metadata: Dict[str, Any], original_filename: str) -> str:
    """
    PURPOSE: Process a filename pattern with metadata and return a valid filename.

    PARAMS:
        pattern (str): The pattern to use for the filename with placeholders like {model_id}_{model_name}.
        metadata (Dict[str, Any]): Metadata to use for filename placeholders.
        original_filename (str): The original filename to use as fallback and for extension extraction.

    RETURNS:
        str: The processed filename with placeholders replaced by metadata values.
    """
    if not pattern or not isinstance(pattern, str):
        logging.warning("Invalid filename pattern, using original filename")
        return original_filename

    # Prepare the metadata
    processed_metadata = prepare_metadata(metadata, original_filename)

    try:
        # Replace placeholders with values from metadata
        filename = pattern.format(**processed_metadata)

        # Ensure the filename is safe and valid
        sanitized_filename = sanitize_filename(filename)

        # Make sure we have a proper extension
        if not Path(sanitized_filename).suffix and Path(original_filename).suffix:
            sanitized_filename = f"{sanitized_filename}{Path(original_filename).suffix}"

        return sanitized_filename
    except KeyError as e:
        logging.warning(f"Missing placeholder in filename pattern: {e}")
        return original_filename
    except Exception as e:
        logging.error(f"Error processing filename pattern: {e}")
        return original_filename


def prepare_metadata(metadata: Optional[Dict[str, Any]], original_filename: str) -> Dict[str, Any]:
    """
    PURPOSE: Prepare metadata for filename pattern processing.

    PARAMS:
        metadata (Optional[Dict[str, Any]]): User-provided metadata dictionary.
        original_filename (str): The original filename.

    RETURNS:
        Dict[str, Any]: Processed metadata including defaults and computed values.
    """
    result = metadata.copy() if metadata else {}

    # Extract extension from the original filename
    _, ext = os.path.splitext(original_filename)
    ext = ext.lstrip('.')  # Remove the leading dot

    # Add extension to metadata
    result['ext'] = ext

    # Add original filename to metadata
    result['original_filename'] = original_filename

    # Generate CRC32 checksum if not provided
    if 'crc32' not in result:
        crc32 = format(zlib.crc32(original_filename.encode()) & 0xFFFFFFFF, '08X')
        result['crc32'] = crc32

    return result


def sanitize_filename(filename: str) -> str:
    """
    PURPOSE: Sanitize the filename to ensure it's safe and valid.

    PARAMS:
        filename (str): The filename to sanitize.

    RETURNS:
        str: The sanitized filename.
    """
    # Replace undesirable characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)

    # Replace multiple consecutive underscores with a single one
    sanitized = re.sub(r'_+', '_', sanitized)

    # Remove leading/trailing dots and spaces (not allowed in Windows)
    sanitized = sanitized.strip('. _')  # Added underscore to strip

    # Ensure the filename is not empty or just underscores
    if not sanitized or sanitized == '_':
        sanitized = "download"

    return sanitized


"""
## KNOWN ERRORS: None

## IMPROVEMENTS: Initial implementation.

## FUTURE TODOs:
- Add support for more advanced template expressions.
- Consider adding filename length limits for different filesystems.
"""