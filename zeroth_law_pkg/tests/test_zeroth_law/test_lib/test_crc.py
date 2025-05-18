import pytest
import sys
from src.zeroth_law.lib.crc import calculate_crc32

# Test cases with known CRC32 values (calculated using online tools or python zlib)
# Note: Python's zlib.crc32 might differ from other tools if not handled carefully (e.g., initial value)
# The important thing is consistency with the function's own output.
# Values confirmed via python interpreter: `hex(zlib.crc32(b'...') & 0xffffffff)`

try:
    from zeroth_law.lib.crc import calculate_crc32

    _crc_imported = True
except ImportError:
    calculate_crc32 = None
    _crc_imported = False
    print("Warning: Could not import calculate_crc32 function.", file=sys.stderr)

# Known CRC32 values for test strings (replace with reliable source if possible)
KNOWN_CRC_VALUES = [
    ("", "0x00000000"),
    ("test", "0xD87F7E0C"),
    ("Hello, World!", "0xEC4AC3D0"),
    ("The quick brown fox jumps over the lazy dog", "0x414FA339"),
    ("123456789", "0xCBF43926"),
    # Recalculated value for this string, old one was wrong
    ("~!@#$%^&*()_+`-=:", "0x3EFF19EE"),
    ("你好，世界", "0xACF5DA54"),  # Unicode
    (
        "This is a somewhat longer test string to see how the CRC32 calculation behaves.",
        "0xE08926F0",
    ),
    ("  leading and trailing spaces  ", "0x6C9A1D3E"),
    ("Line1\nLine2", "0x703B499E"),
]


@pytest.mark.skipif(not _crc_imported, reason="calculate_crc32 not imported")
@pytest.mark.parametrize("data_str, expected_crc_hex", KNOWN_CRC_VALUES)
def test_calculate_crc32_known_values(data_str, expected_crc_hex):
    """Test calculate_crc32 against known values."""
    data_bytes = data_str.encode("utf-8")
    # expected_crc_int = int(expected_crc_hex, 16)  # Convert expected hex string to int - REMOVED
    actual_crc_str = calculate_crc32(data_bytes)
    assert actual_crc_str == expected_crc_hex  # Compare strings


@pytest.mark.skipif(not _crc_imported, reason="calculate_crc32 not imported")
def test_calculate_crc32_type():
    """Test that calculate_crc32 returns a string."""
    assert isinstance(calculate_crc32(b"some data"), str)  # Check for str type


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

# Helper function (ensure it matches the actual implementation if imported)
# If calculate_crc32_hex is deprecated/removed, skip this test.
# For now, assume it might still be tested if available.
try:
    # Assume calculate_crc32_hex was moved or is defined locally
    # If it's meant to be imported, adjust the import path:
    # from zeroth_law.lib.tool_path_utils import calculate_crc32_hex # Example path

    # Local definition for testing IF it's not imported:
    # def calculate_crc32_hex(content_bytes: bytes) -> str:
    #     crc_val = zlib.crc32(content_bytes) & 0xFFFFFFFF
    #     return f"0x{crc_val:08X}"
    # For this test, we assume it's imported or available
    from zeroth_law.lib.tool_path_utils import (
        calculate_crc32_hex,
    )  # Check this import path

    _crc_hex_imported = True
except ImportError:
    calculate_crc32_hex = None
    _crc_hex_imported = False
    print("Warning: Could not import calculate_crc32_hex helper.", file=sys.stderr)


# @pytest.mark.skip(reason="calculate_crc32_hex helper function not found or importable.")
@pytest.mark.skipif(not _crc_hex_imported, reason="calculate_crc32_hex not imported")
def test_calculate_crc32_hex_basic():
    """Basic test for the calculate_crc32_hex helper."""
    # Use a different known value if needed
    assert calculate_crc32_hex(b"test") == "0xD87F7E0C"


# <<< ZEROTH LAW FOOTER >>>
