"""
# PURPOSE: Tests for filename_pattern.py.

## DEPENDENCIES:
- pytest: For running tests.
- unittest.mock: For mocking dependencies.
- civit.filename_pattern: The module under test.

## TODO: None
"""

import pytest
from unittest import mock
import os
import zlib
from pathlib import Path

from src.civit.filename_pattern import process_filename_pattern, prepare_metadata, sanitize_filename


def test_process_filename_pattern_basic():
    """Test the basic functionality of process_filename_pattern."""
    pattern = "{model_id}_{model_name}.{ext}"
    metadata = {"model_id": "123", "model_name": "test_model"}
    original_filename = "original.png"

    result = process_filename_pattern(pattern, metadata, original_filename)

    assert result == "123_test_model.png"


def test_process_filename_pattern_with_missing_placeholder():
    """Test process_filename_pattern with a missing placeholder."""
    pattern = "{model_id}_{missing_placeholder}.{ext}"
    metadata = {"model_id": "123"}
    original_filename = "original.png"

    result = process_filename_pattern(pattern, metadata, original_filename)

    # Should fall back to original filename when placeholders are missing
    assert result == original_filename


def test_process_filename_pattern_with_invalid_pattern():
    """Test process_filename_pattern with an invalid pattern."""
    pattern = None  # Invalid pattern
    metadata = {"model_id": "123", "model_name": "test_model"}
    original_filename = "original.png"

    result = process_filename_pattern(pattern, metadata, original_filename)

    # Should fall back to original filename for invalid pattern
    assert result == original_filename


def test_prepare_metadata_adds_extension():
    """Test that prepare_metadata adds file extension from original filename."""
    metadata = {"model_id": "123", "model_name": "test_model"}
    original_filename = "original.png"

    result = prepare_metadata(metadata, original_filename)

    assert result["ext"] == "png"
    assert result["original_filename"] == original_filename


def test_prepare_metadata_generates_crc32():
    """Test that prepare_metadata generates the CRC32 value."""
    metadata = {"model_id": "123", "model_name": "test_model"}
    original_filename = "original.png"

    expected_crc32 = format(zlib.crc32(original_filename.encode()) & 0xFFFFFFFF, '08X')

    result = prepare_metadata(metadata, original_filename)

    assert result["crc32"] == expected_crc32


def test_prepare_metadata_preserves_existing_crc32():
    """Test that prepare_metadata preserves existing CRC32 if provided."""
    metadata = {"model_id": "123", "model_name": "test_model", "crc32": "CUSTOM123"}
    original_filename = "original.png"

    result = prepare_metadata(metadata, original_filename)

    # Should keep the provided CRC32 value
    assert result["crc32"] == "CUSTOM123"


def test_sanitize_filename_removes_invalid_chars():
    """Test that sanitize_filename removes invalid characters."""
    filename = 'test<>:"/\\|?*file.png'

    result = sanitize_filename(filename)

    # Invalid characters should be replaced with underscores
    assert '<' not in result
    assert '>' not in result
    assert ':' not in result
    assert '"' not in result
    assert '/' not in result
    assert '\\' not in result
    assert '|' not in result
    assert '?' not in result
    assert '*' not in result


def test_sanitize_filename_handles_empty_result():
    """Test that sanitize_filename handles cases where sanitization would result in an empty string."""
    filename = '???'  # Only invalid characters

    result = sanitize_filename(filename)

    # Should use a default name when sanitization would result in an empty string
    assert result == "download"


def test_process_filename_pattern_with_crc32():
    """Test that process_filename_pattern handles CRC32 in the pattern."""
    pattern = "{model_id}_{model_name}_{crc32}.{ext}"
    metadata = {"model_id": "123", "model_name": "test_model"}
    original_filename = "original.png"

    expected_crc32 = format(zlib.crc32(original_filename.encode()) & 0xFFFFFFFF, '08X')

    result = process_filename_pattern(pattern, metadata, original_filename)

    expected_result = f"123_test_model_{expected_crc32}.png"
    assert result == expected_result


"""
## KNOWN ERRORS: None

## IMPROVEMENTS: Initial implementation.

## FUTURE TODOs:
- Add more test cases for complex patterns and edge cases.
"""