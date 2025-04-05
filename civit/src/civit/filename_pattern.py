# FILE: src/civit/filename_pattern.py
"""
# PURPOSE: Process and generate file names based on patterns and metadata.

## INTERFACES:
    - process_filename_pattern(pattern: str, metadata: Dict, original_filename: str) -> str
    - prepare_metadata(metadata: Dict, original_filename: str) -> Dict
    - sanitize_filename(filename: str) -> str

## DEPENDENCIES:
    - re: Regular expressions for pattern matching
    - os: For file path handling
    - zlib: For CRC32 hash generation
"""

import re
import zlib
import os
from typing import Dict, Any
from ..filename_generator import sanitize_filename
from .exceptions import InvalidPatternError, MetadataError


def process_filename_pattern(
    pattern: str, metadata: Dict[str, Any], original_filename: str
) -> str:
    """
    Process a filename pattern to create a custom filename.

    Args:
        pattern: The pattern template with {placeholders}
        metadata: Dict containing values to substitute into the pattern
        original_filename: Original filename to extract extension from

    Returns:
        Processed filename string
    """
    if not pattern:
        raise InvalidPatternError("Pattern cannot be empty")

    # Prepare metadata with additional fields and defaults
    prepared_metadata = prepare_metadata(metadata, original_filename)

    try:
        # Replace placeholders in the pattern
        result = pattern.format(**prepared_metadata)

        # Sanitize the final filename to ensure it's safe across platforms
        return sanitize_filename(result)
    except KeyError as e:
        missing_key = str(e).strip("'")
        raise MetadataError(f"Missing required metadata field: {missing_key}")


def prepare_metadata(
    metadata: Dict[str, Any], original_filename: str
) -> Dict[str, Any]:
    """
    Prepare metadata for filename pattern processing.

    Args:
        metadata: Original metadata
        original_filename: Original filename

    Returns:
        Enhanced metadata with additional fields
    """
    result = metadata.copy()

    # Extract extension from original filename
    if "." in original_filename:
        ext = original_filename.rsplit(".", 1)[1]
    else:
        ext = ""

    # Add useful fields that aren't in the original metadata
    result.update(
        {
            "original_filename": original_filename,
            "ext": ext,
            "crc32": format(zlib.crc32(original_filename.encode()) & 0xFFFFFFFF, "08x"),
        }
    )

    # Sanitize all metadata values that will be used in filenames
    # Leave hyphens intact for now as they'll be handled by the final sanitize_filename call
    for key, value in list(result.items()):
        if isinstance(value, str):
            # Convert all individual field values to be safe for filename use
            result[key] = sanitize_field_value(value)

    return result


def sanitize_field_value(value: str) -> str:
    """
    Sanitize individual field values before they're used in filenames.
    This preserves hyphens as they're used for field separation.

    Args:
        value: String value to sanitize

    Returns:
        Sanitized string with invalid chars replaced by underscores
    """
    # Replace invalid characters with underscores (but leave hyphens intact)
    invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*", " "]
    result = value
    for char in invalid_chars:
        result = result.replace(char, "_")

    # Clean up multiple and trailing underscores
    while "__" in result:
        result = result.replace("__", "_")

    return result.rstrip("_")
