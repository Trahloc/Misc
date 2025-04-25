import pytest
from src.zeroth_law.lib.crc import calculate_crc32

# Test cases with known CRC32 values (calculated using online tools or python zlib)
# Note: Python's zlib.crc32 might differ from other tools if not handled carefully (e.g., initial value)
# The important thing is consistency with the function's own output.
# Values confirmed via python interpreter: `hex(zlib.crc32(b'...') & 0xffffffff)`

TEST_CASES = [
    ("", "0x00000000"),  # Empty string
    ("test", "0xD87F7E0C"),
    ("Hello, World!", "0xEC4AC3D0"),
    ("The quick brown fox jumps over the lazy dog", "0x414FA339"),
    ("123456789", "0xCBF43926"),
    # Test with some special characters
    ("~!@#$%^&*()_+`-=", "0x9E0445FB"),
    # Test with unicode characters (ensure UTF-8 encoding is handled)
    ("你好，世界", "0xACF5DA54"),
    # Test a longer string
    (
        "This is a somewhat longer test string to see how the CRC32 calculation behaves.",
        "0xE08926F0",
    ),
    # Test string with leading/trailing whitespace (should be included in CRC)
    ("  leading and trailing spaces  ", "0x6C9A1D3E"),
    # Test string with embedded newline
    ("Line1\nLine2", "0x703B499E"),
]


@pytest.mark.parametrize("input_string, expected_crc_hex", TEST_CASES)
def test_calculate_crc32_known_values(input_string: str, expected_crc_hex: str):
    """Test calculate_crc32 against a set of known input/output pairs."""
    assert calculate_crc32(input_string) == expected_crc_hex


def test_calculate_crc32_type():
    """Test that the function returns a string."""
    result = calculate_crc32("test")
    assert isinstance(result, str)


def test_calculate_crc32_format():
    """Test that the output string is correctly formatted (0x prefix, 8 hex digits)."""
    result = calculate_crc32("another test")
    assert result.startswith("0x")
    assert len(result) == 10  # 0x + 8 hex digits
    # Check if the part after 0x contains valid hex characters
    hex_part = result[2:]
    assert all(c in "0123456789ABCDEF" for c in hex_part)


def test_calculate_crc32_consistency():
    """Test that calling the function twice with the same input yields the same output."""
    input_str = "consistent input"
    result1 = calculate_crc32(input_str)
    result2 = calculate_crc32(input_str)
    assert result1 == result2
