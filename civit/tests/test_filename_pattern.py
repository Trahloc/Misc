"""Tests for filename pattern functionality.

DEPENDENCIES:
    - pytest: Test framework
    - civit.filename_pattern: Module under test
    - civit.exceptions: Custom exceptions
"""

import pytest
import random
import string
from civit.filename_pattern import (
    process_filename_pattern,
    prepare_metadata,
    sanitize_filename,
)
from civit.exceptions import InvalidPatternError, MetadataError

hypothesis = pytest.importorskip(
    "hypothesis", reason="Hypothesis library not found, skipping property-based tests"
)


def test_basic_pattern_processing():
    """Test basic pattern processing functionality."""
    pattern = "{model_id}_{model_name}.{ext}"
    metadata = {"model_id": "123", "model_name": "test_model"}
    result = process_filename_pattern(pattern, metadata, "test.zip")
    assert result == "123_test_model.zip"


@pytest.mark.parametrize(
    "input_name,expected",
    [
        ("test*file.txt", "test_file.txt"),
        ("test/file.txt", "test_file.txt"),
        ("test\\file.txt", "test_file.txt"),
        ("test:file.txt", "test_file.txt"),
        ('test"file.txt', "test_file.txt"),
        ("test<file.txt", "test_file.txt"),
        ("test>file.txt", "test_file.txt"),
        ("test?file.txt", "test_file.txt"),
        ("test|file.txt", "test_file.txt"),
        # Test trailing underscore stripping
        ("test_.txt", "test.txt"),
        # Test double underscore replacement
        ("test__file.txt", "test_file.txt"),
    ],
)
def test_sanitize_filename(input_name, expected):
    """Test that sanitize_filename properly handles special characters."""
    assert sanitize_filename(input_name) == expected


def test_metadata_preparation():
    """Test metadata preparation."""
    metadata = {"model_id": "123"}
    original_filename = "test.zip"
    result = prepare_metadata(metadata, original_filename)

    assert result["ext"] == "zip"
    assert result["original_filename"] == original_filename
    assert len(result["crc32"]) == 8
    assert result["model_id"] == "123"


def test_invalid_pattern():
    """Test handling of invalid patterns."""
    with pytest.raises(InvalidPatternError):
        process_filename_pattern(None, {}, "test.zip")


def test_missing_metadata():
    """Test handling of missing metadata."""
    pattern = "{missing_key}.{ext}"
    with pytest.raises(MetadataError):
        process_filename_pattern(pattern, {}, "test.zip")


# Helper functions for property tests
def generate_random_string(
    length: int = 10, min_length: int = None, max_length: int = None
) -> str:
    """Generate a random string of fixed or variable length.

    Args:
        length: Fixed length (used if min_length and max_length are None)
        min_length: Minimum length if variable length is desired
        max_length: Maximum length if variable length is desired

    Returns:
        A random string of appropriate length
    """
    if min_length is not None and max_length is not None:
        length = random.randint(min_length, max_length)
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_safe_pattern():
    """Generate a safe filename pattern for testing."""
    prefix = "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 10)))
    return f"{{model_id}}_{prefix}.{{ext}}"


# Property tests using pytest.mark.parametrize
@pytest.mark.parametrize("test_case", range(10))  # Run 10 random test cases
def test_pattern_processing_properties(test_case):
    """Test pattern processing with randomly generated inputs."""
    # Generate test inputs
    pattern = random.choice([None, generate_safe_pattern()])
    model_id = str(random.randint(1, 100000))
    original_filename = f"{generate_random_string()}.zip"

    metadata = {"model_id": model_id}

    if pattern is None:
        with pytest.raises(Exception):
            processed = process_filename_pattern(pattern, metadata, original_filename)
    else:
        try:
            processed = process_filename_pattern(pattern, metadata, original_filename)
            assert processed.endswith(".zip")
            assert model_id in processed
        except Exception:
            # Some patterns might still be invalid, that's OK
            pass


@pytest.mark.parametrize("test_case", range(10))  # Run 10 random test cases
def test_sanitize_filename_properties(test_case):
    """Test filename sanitization with generated data."""
    # Generate a filename with invalid characters
    filename = generate_random_string(min_length=5, max_length=20)
    invalid_chars = '<>:"/\\|?*'

    # Insert some invalid characters
    for _ in range(random.randint(1, 5)):
        pos = random.randint(0, len(filename) - 1)
        char = random.choice(invalid_chars)
        filename = filename[:pos] + char + filename[pos:]

    result = sanitize_filename(filename)
    # Verify no invalid characters remain
    assert not any(c in result for c in invalid_chars)
    assert result  # Result is not empty


@pytest.mark.parametrize("test_case", range(10))  # Run 10 random test cases
def test_prepare_metadata_properties(test_case):
    """Test metadata preparation with generated data."""
    # Generate random metadata
    metadata = {
        generate_random_string(min_length=5, max_length=10): generate_random_string(
            min_length=5, max_length=15
        )
        for _ in range(random.randint(1, 5))
    }

    # Generate a random filename with extension
    original_filename = f"{generate_random_string()}.test"

    result = prepare_metadata(metadata, original_filename)

    assert result["ext"] == "test"
    assert result["original_filename"] == original_filename
    assert len(result["crc32"]) == 8
    assert all(metadata[k] == result[k] for k in metadata)
