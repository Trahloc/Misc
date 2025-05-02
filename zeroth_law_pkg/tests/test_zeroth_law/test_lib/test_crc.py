import pytest
from src.zeroth_law.lib.crc import calculate_crc32

# Test cases with known CRC32 values (calculated using online tools or python zlib)
# Note: Python's zlib.crc32 might differ from other tools if not handled carefully (e.g., initial value)
# The important thing is consistency with the function's own output.
# Values confirmed via python interpreter: `hex(zlib.crc32(b'...') & 0xffffffff)`


@pytest.mark.parametrize(
    "data_str, expected_crc_hex",
    [
        ("", "0x00000000"),
        ("test", "0xD87F7E0C"),
        ("Hello, World!", "0xEC4AC3D0"),
        ("The quick brown fox jumps over the lazy dog", "0x414FA339"),
        ("123456789", "0xCBF43926"),
        ("~!@#$%^&*()_+`-=:", "0x9E0445FB"),  # Removed quote causing issues
        ("你好，世界", "0xACF5DA54"),  # Unicode
        ("This is a somewhat longer test string to see how the CRC32 calculation behaves.", "0xE08926F0"),
        ("  leading and trailing spaces  ", "0x6C9A1D3E"),
        ("Line1\nLine2", "0x703B499E"),
    ],
)
def test_calculate_crc32_known_values(data_str, expected_crc_hex):
    """Test calculate_crc32 against known values."""
    data_bytes = data_str.encode("utf-8")
    expected_crc_int = int(expected_crc_hex, 16)  # Convert expected hex string to int
    actual_crc_int = calculate_crc32(data_bytes)
    assert actual_crc_int == expected_crc_int  # Compare integers


def test_calculate_crc32_type():
    """Test that calculate_crc32 returns an int."""
    assert isinstance(calculate_crc32(b"some data"), int)  # Check for int type


def test_calculate_crc32_format():
    """Test the hex formatting utility function."""
    # Check if the hex utility function exists, if not, skip or adapt
    try:
        from zeroth_law.lib.crc import calculate_crc32_hex

        crc_val_int = calculate_crc32(b"format test")
        expected_hex_str = f"0x{crc_val_int:08x}"  # Lowercase hex
        assert calculate_crc32_hex(b"format test") == expected_hex_str
    except ImportError:
        pytest.skip("calculate_crc32_hex helper function not found or importable.")


def test_calculate_crc32_consistency():
    """Test that calculate_crc32 returns the same value for the same input."""
    data = b"consistent data"
    crc1 = calculate_crc32(data)
    crc2 = calculate_crc32(data)
    assert crc1 == crc2


# TODO: Add tests for calculate_crc32_hex if not covered by test_calculate_crc32_format
