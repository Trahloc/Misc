"""
Tests for src/zeroth_law/lib/tool_index_handler.py
"""

import pytest
import json
from pathlib import Path
from typing import Any, Dict, Tuple, Optional
from unittest.mock import patch, mock_open

# Module under test
from zeroth_law.lib.tool_index_handler import ToolIndexHandler

# --- Helper Fixtures ---


@pytest.fixture
def mock_index_file(tmp_path: Path) -> Path:
    """Provides a path for a temporary mock index file."""
    return tmp_path / "tool_index.json"


@pytest.fixture
def sample_index_data() -> Dict[str, Any]:
    """Provides sample index data."""
    return {
        "toolA": {"crc": "0x1111", "checked_timestamp": 1678886400.0},
        "toolB_sub1": {"crc": "0x2222", "checked_timestamp": 1678886500.0},
    }


# --- Tests for ToolIndexHandler --- #


def test_load_tool_index_success(mock_index_file: Path, sample_index_data: Dict[str, Any]):
    """Test successful loading of the index via the constructor."""
    mock_index_file.write_text(json.dumps(sample_index_data), encoding="utf-8")
    handler = ToolIndexHandler(mock_index_file)
    assert handler.get_raw_index_data() == sample_index_data


def test_load_tool_index_file_not_found(mock_index_file: Path):
    """Test initialization when the index file doesn't exist."""
    assert not mock_index_file.exists()  # Ensure it doesn't exist
    handler = ToolIndexHandler(mock_index_file)
    assert handler.get_raw_index_data() == {}  # Should initialize empty


def test_load_tool_index_invalid_json(mock_index_file: Path):
    """Test initialization with an invalid JSON file."""
    mock_index_file.write_text("this is not json", encoding="utf-8")
    handler = ToolIndexHandler(mock_index_file)
    assert handler.get_raw_index_data() == {}  # Should initialize empty


def test_load_tool_index_json_not_dict(mock_index_file: Path):
    """Test initialization when JSON is valid but not a dictionary."""
    mock_index_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    handler = ToolIndexHandler(mock_index_file)
    assert handler.get_raw_index_data() == {}  # Should initialize empty


# Test cases for get_entry
GET_ENTRY_TEST_CASES = [
    (("toolA",), ("toolA",), {"crc": "0x1111", "checked_timestamp": 1678886400.0}),
    (("toolB", "sub1"), ("toolB", "sub1"), {"crc": "0x2222", "checked_timestamp": 1678886500.0}),
    (("toolC",), ("toolC",), None),  # Not in index
    ((), (), None),  # Empty sequence
]


@pytest.mark.parametrize("sequence, tool_id_ignored, expected_entry", GET_ENTRY_TEST_CASES)
def test_get_index_entry(
    mock_index_file: Path,
    sample_index_data: Dict[str, Any],
    sequence: Tuple[str, ...],
    tool_id_ignored: Tuple[str, ...],  # No longer needed as input
    expected_entry: Optional[Dict[str, Any]],
):
    """Tests retrieving entries using get_entry."""
    mock_index_file.write_text(json.dumps(sample_index_data), encoding="utf-8")
    handler = ToolIndexHandler(mock_index_file)
    assert handler.get_entry(sequence) == expected_entry


# --- Tests for update_entry ---


def test_update_index_entry_existing(mock_index_file: Path, sample_index_data: Dict[str, Any]):
    """Test updating an existing entry."""
    mock_index_file.write_text(json.dumps(sample_index_data), encoding="utf-8")
    handler = ToolIndexHandler(mock_index_file)

    sequence = ("toolA",)
    update_data = {"crc": "0xAAAA", "new_field": True}
    handler.update_entry(sequence, update_data)

    expected_data = sample_index_data.copy()
    expected_data["toolA"].update(update_data)

    assert handler.get_entry(sequence) == expected_data["toolA"]
    assert handler._dirty is True  # Check dirty flag


def test_update_index_entry_new(mock_index_file: Path, sample_index_data: Dict[str, Any]):
    """Test adding a new entry."""
    mock_index_file.write_text(json.dumps(sample_index_data), encoding="utf-8")
    handler = ToolIndexHandler(mock_index_file)

    sequence = ("newTool", "sub")
    update_data = {"crc": "0xBBBB", "checked_timestamp": 1700000000.0}
    handler.update_entry(sequence, update_data)

    expected_data = sample_index_data.copy()
    expected_data["newTool_sub"] = update_data  # Key is joined sequence

    assert handler.get_entry(sequence) == update_data
    assert handler.get_raw_index_data() == expected_data
    assert handler._dirty is True


def test_update_index_entry_empty_sequence(mock_index_file: Path, sample_index_data: Dict[str, Any]):
    """Test attempting to update with an empty sequence."""
    initial_data = sample_index_data.copy()
    mock_index_file.write_text(json.dumps(initial_data), encoding="utf-8")
    handler = ToolIndexHandler(mock_index_file)

    handler.update_entry((), {"crc": "0xCCCC"})

    # Data should remain unchanged
    assert handler.get_raw_index_data() == initial_data
    assert handler._dirty is False


# TODO: Add tests for get_tool_definition if needed
# TODO: Add tests for saving the index if that functionality is added

# <<< ZEROTH LAW FOOTER >>>
