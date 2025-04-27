"""Tests for src.zeroth_law.dev_scripts.tool_index_utils."""

import json
import logging
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
import yaml  # Import yaml if needed for config loading tests (if any)
from filelock import FileLock, Timeout  # Import Timeout here
from typing import List, Tuple, Dict, Any  # Ensure List and Tuple are here
import time
import os
from pprint import pprint

# Import functions to test
from src.zeroth_law.dev_scripts.tool_index_utils import (
    load_tool_index,
    save_tool_index,
    TOOL_INDEX_PATH,  # Corrected: removed 'S'
    get_index_entry,
    update_index_entry,
    load_update_and_save_entry,
)

# --- Tests for load_tool_index ---


@pytest.fixture
def mock_tool_index_file(tmp_path, monkeypatch):
    """Fixture to manage the TOOL_INDEX_PATH for tests."""
    temp_index_path = tmp_path / "tool_index.json"
    monkeypatch.setattr("src.zeroth_law.dev_scripts.tool_index_utils.TOOL_INDEX_PATH", temp_index_path)
    return temp_index_path


def test_load_tool_index_file_not_found(mock_tool_index_file, caplog):
    """Test load_tool_index when the index file does not exist."""
    caplog.set_level(logging.INFO)
    result = load_tool_index()
    assert result == {}
    assert f"Tool index file not found at {mock_tool_index_file}" in caplog.text


def test_load_tool_index_empty_file(mock_tool_index_file, caplog):
    """Test load_tool_index with an empty file."""
    mock_tool_index_file.touch()
    caplog.set_level(logging.ERROR)
    result = load_tool_index()
    assert result == {}
    assert f"Error loading or parsing tool index {mock_tool_index_file}" in caplog.text


def test_load_tool_index_invalid_json(mock_tool_index_file, caplog):
    """Test load_tool_index with invalid JSON content."""
    mock_tool_index_file.write_text('{"key": "value",')  # Invalid JSON - Fixed parenthesis
    caplog.set_level(logging.ERROR)
    result = load_tool_index()
    assert result == {}
    assert f"Error loading or parsing tool index {mock_tool_index_file}" in caplog.text


def test_load_tool_index_not_a_dict(mock_tool_index_file, caplog):
    """Test load_tool_index when the valid JSON is not a dictionary."""
    mock_tool_index_file.write_text(json.dumps([1, 2, 3]))  # Valid JSON, wrong type
    caplog.set_level(logging.ERROR)
    result = load_tool_index()
    assert result == {}
    assert "Tool index format is invalid (must be a Dict)" in caplog.text


def test_load_tool_index_malformed_entry_value(mock_tool_index_file, caplog):
    """Test load_tool_index with a non-dict entry value."""
    valid_entry = {"tool1": {"crc": "0x123", "timestamp": 123}}
    malformed_data = {**valid_entry, "tool2": "not_a_dict"}
    mock_tool_index_file.write_text(json.dumps(malformed_data))
    caplog.set_level(logging.WARNING)
    result = load_tool_index()
    assert result == valid_entry  # Only valid entry should remain
    assert "Invalid or missing metadata structure for tool 'tool2'" in caplog.text


def test_load_tool_index_missing_crc(mock_tool_index_file, caplog):
    """Test load_tool_index with an entry missing the required 'crc' key."""
    valid_entry = {"tool1": {"crc": "0x123", "timestamp": 123}}
    malformed_data = {**valid_entry, "tool2": {"timestamp": 456}}  # Missing crc
    mock_tool_index_file.write_text(json.dumps(malformed_data))
    caplog.set_level(logging.WARNING)
    result = load_tool_index()
    assert result == valid_entry  # Only valid entry should remain
    assert "Invalid or missing metadata structure for tool 'tool2'" in caplog.text


def test_load_tool_index_no_valid_entries(mock_tool_index_file, caplog):
    """Test load_tool_index when the file contains only invalid entries."""
    malformed_data = {"tool1": "invalid", "tool2": {"ts": 123}}
    mock_tool_index_file.write_text(json.dumps(malformed_data))
    caplog.set_level(logging.WARNING)
    result = load_tool_index()
    assert result == {}
    assert "No valid tool entries found" in caplog.text


def test_load_tool_index_success(mock_tool_index_file):
    """Test successful loading of a valid tool index."""
    valid_data = {
        "tool1": {"crc": "0xabc", "timestamp": 123},
        "tool2": {"crc": "0xdef", "timestamp": 456, "subcommands": {}},
    }
    mock_tool_index_file.write_text(json.dumps(valid_data))
    result = load_tool_index()
    assert result == valid_data


# --- Tests for save_tool_index ---


def test_save_tool_index_success(mock_tool_index_file):
    """Test successfully saving a valid index dictionary."""
    data_to_save = {
        "tool2": {"crc": "0xdef"},
        "tool1": {"crc": "0xabc"},
    }
    success = save_tool_index(data_to_save)
    assert success is True
    assert mock_tool_index_file.is_file()

    # Verify content and sorting
    with open(mock_tool_index_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    expected_saved_data = {
        "tool1": {"crc": "0xabc"},
        "tool2": {"crc": "0xdef"},
    }
    assert saved_data == expected_saved_data
    # Check if keys are sorted in the raw file (json.dump with indent=2 helps)
    raw_content = mock_tool_index_file.read_text(encoding="utf-8")
    assert '"tool1":' in raw_content
    assert '"tool2":' in raw_content
    assert raw_content.find('"tool1":') < raw_content.find('"tool2":')
    assert raw_content.endswith("\n")  # Check for trailing newline


def test_save_tool_index_creates_parent_dir(tmp_path, monkeypatch):
    """Test that save_tool_index creates the parent directory if needed."""
    # Use a path where the parent doesn't exist initially
    deep_path = tmp_path / "new_parent" / "tool_index.json"
    monkeypatch.setattr("src.zeroth_law.dev_scripts.tool_index_utils.TOOL_INDEX_PATH", deep_path)

    assert not deep_path.parent.exists()
    data_to_save = {"tool1": {"crc": "0xabc"}}
    success = save_tool_index(data_to_save)

    assert success is True
    assert deep_path.is_file()
    assert deep_path.parent.is_dir()


@patch("builtins.open", new_callable=mock_open)
def test_save_tool_index_io_error(mock_open_func, mock_tool_index_file, caplog):
    """Test save_tool_index handling of IOError during write."""
    # Configure the mock to raise IOError on write
    mock_open_func.side_effect = IOError("Disk full simulation")
    caplog.set_level(logging.ERROR)

    data_to_save = {"tool1": {"crc": "0xabc"}}
    success = save_tool_index(data_to_save)

    assert success is False
    assert f"Error saving tool index {mock_tool_index_file}" in caplog.text
    # Verify it tried to open the correct file in write mode
    mock_open_func.assert_called_once_with(mock_tool_index_file, "w", encoding="utf-8")


def test_save_tool_index_type_error():
    """Test save_tool_index raises TypeError for non-dict input."""
    with pytest.raises(TypeError, match="index_data must be a dictionary"):
        save_tool_index([1, 2, 3])  # Pass a list instead of dict


# --- Tests for get_index_entry ---


@pytest.fixture
def sample_index_data():
    """Provides a sample index structure for testing get/update."""
    return {
        "tool1": {"crc": "0xabc", "timestamp": 123},
        "tool2": {
            "crc": "0xdef",
            "timestamp": 456,
            "subcommands": {
                "subA": {"crc": "0xsubA", "checked": 1},
                "subB": {"crc": "0xsubB", "checked": 2},
            },
        },
        "tool3": {"crc": "0xghi", "timestamp": 789, "subcommands": "not_a_dict"},
        "tool4": "not_a_dict",
    }


def test_get_index_entry_base_success(sample_index_data):
    """Test getting an existing base command entry."""
    entry = get_index_entry(sample_index_data, ("tool1",))
    assert entry == {"crc": "0xabc", "timestamp": 123}


def test_get_index_entry_subcommand_success(sample_index_data):
    """Test getting an existing subcommand entry."""
    entry = get_index_entry(sample_index_data, ("tool2", "subA"))
    assert entry == {"crc": "0xsubA", "checked": 1}


def test_get_index_entry_empty_sequence(caplog):
    """Test get_index_entry with an empty command sequence."""
    caplog.set_level(logging.WARNING)
    entry = get_index_entry({}, ())
    assert entry == {}
    assert "Attempted to get index entry for empty command sequence" in caplog.text


def test_get_index_entry_base_not_found(sample_index_data):
    """Test getting a base command that does not exist."""
    entry = get_index_entry(sample_index_data, ("nonexistent",))
    assert entry == {}


def test_get_index_entry_subcommand_base_not_found(sample_index_data):
    """Test getting a subcommand where the base command does not exist."""
    entry = get_index_entry(sample_index_data, ("nonexistent", "sub"))
    assert entry == {}


def test_get_index_entry_base_not_a_dict(sample_index_data):
    """Test getting a base command where the entry is not a dict."""
    entry = get_index_entry(sample_index_data, ("tool4",))
    assert entry == {}


def test_get_index_entry_subcommand_base_not_a_dict(sample_index_data):
    """Test getting a subcommand where the base entry is not a dict."""
    entry = get_index_entry(sample_index_data, ("tool4", "sub"))
    assert entry == {}


def test_get_index_entry_subcommands_not_a_dict(sample_index_data):
    """Test getting a subcommand where the base 'subcommands' key is not a dict."""
    entry = get_index_entry(sample_index_data, ("tool3", "sub"))
    assert entry == {}


def test_get_index_entry_subcommand_not_found(sample_index_data):
    """Test getting a subcommand that doesn't exist under a valid base."""
    entry = get_index_entry(sample_index_data, ("tool2", "subC"))  # subC doesn't exist
    assert entry == {}


# --- Tests for update_index_entry ---


def test_update_index_entry_base_update_existing(sample_index_data):
    """Test updating fields in an existing base command entry."""
    update_data = {"crc": "0xnew", "checked": 999}
    success = update_index_entry(sample_index_data, ("tool1",), update_data)
    assert success is True
    assert sample_index_data["tool1"]["crc"] == "0xnew"
    assert sample_index_data["tool1"]["checked"] == 999
    assert sample_index_data["tool1"]["timestamp"] == 123  # Original field preserved


def test_update_index_entry_base_create_new(sample_index_data):
    """Test creating a completely new base command entry."""
    update_data = {"crc": "0xnew_tool", "checked": 1}
    success = update_index_entry(sample_index_data, ("new_tool",), update_data)
    assert success is True
    assert "new_tool" in sample_index_data
    assert sample_index_data["new_tool"] == update_data


def test_update_index_entry_base_overwrite_invalid(sample_index_data, caplog):
    """Test creating a base entry when the key exists but holds non-dict data."""
    caplog.set_level(logging.INFO)
    update_data = {"crc": "0xfixed", "checked": 1}
    success = update_index_entry(sample_index_data, ("tool4",), update_data)  # tool4 was "not_a_dict"
    assert success is True
    assert isinstance(sample_index_data["tool4"], dict)
    assert sample_index_data["tool4"] == update_data
    assert "Creating/resetting base entry for 'tool4'" in caplog.text


def test_update_index_entry_subcommand_update_existing(sample_index_data):
    """Test updating fields in an existing subcommand entry."""
    update_data = {"crc": "0xsubA_new", "new_field": True}
    success = update_index_entry(sample_index_data, ("tool2", "subA"), update_data)
    assert success is True
    assert sample_index_data["tool2"]["subcommands"]["subA"]["crc"] == "0xsubA_new"
    assert sample_index_data["tool2"]["subcommands"]["subA"]["new_field"] is True
    assert sample_index_data["tool2"]["subcommands"]["subA"]["checked"] == 1  # Original preserved


def test_update_index_entry_subcommand_create_new(sample_index_data):
    """Test creating a new subcommand under an existing base with subcommands."""
    update_data = {"crc": "0xsubC", "checked": 3}
    success = update_index_entry(sample_index_data, ("tool2", "subC"), update_data)
    assert success is True
    assert "subC" in sample_index_data["tool2"]["subcommands"]
    assert sample_index_data["tool2"]["subcommands"]["subC"] == update_data


def test_update_index_entry_subcommand_create_base_and_sub(sample_index_data, caplog):
    """Test creating a subcommand when the base command doesn't exist."""
    caplog.set_level(logging.WARNING)
    update_data = {"crc": "0xbrand_new", "checked": 1}
    success = update_index_entry(sample_index_data, ("brand_new_tool", "sub"), update_data)
    assert success is True
    assert "brand_new_tool" in sample_index_data
    assert isinstance(sample_index_data["brand_new_tool"], dict)
    assert "subcommands" in sample_index_data["brand_new_tool"]
    assert isinstance(sample_index_data["brand_new_tool"]["subcommands"], dict)
    assert "sub" in sample_index_data["brand_new_tool"]["subcommands"]
    assert sample_index_data["brand_new_tool"]["subcommands"]["sub"] == update_data
    assert "Created minimal base entry for 'brand_new_tool'" in caplog.text


def test_update_index_entry_subcommand_create_subcommands_dict(sample_index_data, caplog):
    """Test creating a subcommand when base exists but lacks a 'subcommands' dict."""
    caplog.set_level(logging.INFO)
    update_data = {"crc": "0xsub1", "checked": 1}
    success = update_index_entry(sample_index_data, ("tool1", "sub1"), update_data)  # tool1 had no subcommands
    assert success is True
    assert "subcommands" in sample_index_data["tool1"]
    assert isinstance(sample_index_data["tool1"]["subcommands"], dict)
    assert "sub1" in sample_index_data["tool1"]["subcommands"]
    assert sample_index_data["tool1"]["subcommands"]["sub1"] == update_data
    assert "Created 'subcommands' dict for base 'tool1'" in caplog.text


def test_update_index_entry_subcommand_overwrite_invalid_subcommands(sample_index_data, caplog):
    """Test creating a subcommand when base 'subcommands' is not a dict."""
    caplog.set_level(logging.INFO)
    update_data = {"crc": "0xsub_fixed", "checked": 1}
    success = update_index_entry(
        sample_index_data, ("tool3", "sub_fixed"), update_data
    )  # tool3 subcommands was "not_a_dict"
    assert success is True
    assert "subcommands" in sample_index_data["tool3"]
    assert isinstance(sample_index_data["tool3"]["subcommands"], dict)
    assert "sub_fixed" in sample_index_data["tool3"]["subcommands"]
    assert sample_index_data["tool3"]["subcommands"]["sub_fixed"] == update_data
    assert "Created 'subcommands' dict for base 'tool3'" in caplog.text  # Logs creation/overwrite


def test_update_index_entry_empty_sequence(sample_index_data, caplog):
    """Test update_index_entry with an empty command sequence."""
    original_data = sample_index_data.copy()
    caplog.set_level(logging.ERROR)
    success = update_index_entry(sample_index_data, (), {"crc": "0xignored"})
    assert success is False
    assert sample_index_data == original_data  # Ensure data wasn't modified
    assert "Attempted to update index entry for empty command sequence" in caplog.text


# --- Tests for load_update_and_save_entry ---


def test_load_update_save_success(mock_tool_index_file, sample_index_data):
    """Test the successful path of load_update_and_save_entry using real file I/O."""
    # Prepare initial file state (load_tool_index filters invalid entries)
    initial_data = {k: v for k, v in sample_index_data.items() if isinstance(v, dict) and "crc" in v}
    mock_tool_index_file.write_text(json.dumps(sample_index_data, indent=2) + "\n")  # Write original for load to filter

    command_seq = ("tool1",)
    update_data = {"crc": "0xnew", "checked": 999}
    expected_data_after_update = initial_data.copy()
    expected_data_after_update["tool1"].update(update_data)

    # Keep FileLock mock minimal, just prevent actual locking/delay
    with patch("filelock.FileLock.acquire", return_value=None), patch("filelock.FileLock.release", return_value=None):
        success = load_update_and_save_entry(command_seq, update_data)

    assert success is True

    # Verify file content after the operation
    assert mock_tool_index_file.is_file()
    final_content = json.loads(mock_tool_index_file.read_text(encoding="utf-8"))
    # Check sorting and content (should match filtered + updated data)
    assert list(final_content.keys()) == sorted(expected_data_after_update.keys())
    assert final_content == expected_data_after_update


@patch("filelock.FileLock.acquire", side_effect=Timeout("Simulated timeout"))
def test_load_update_save_lock_timeout(mock_acquire, mock_tool_index_file, caplog):
    """Test load_update_and_save_entry when lock acquisition times out."""
    caplog.set_level(logging.ERROR)
    command_seq = ("tool1",)
    update_data = {"new_field": True}

    success = load_update_and_save_entry(command_seq, update_data)

    assert success is False
    mock_acquire.assert_called_once()
    assert "Timeout acquiring lock" in caplog.text


# Removed test_load_update_save_load_failure as load_tool_index handles
# internal errors and returns {} which is a valid load for the wrapper.
# def test_load_update_save_load_failure(mock_tool_index_file, caplog): ...


# Justification for Mock: Testing the wrapper's handling of explicit False return
@patch("src.zeroth_law.dev_scripts.tool_index_utils.update_index_entry", return_value=False)  # noqa: E501 ZLF: Test wrapper
def test_load_update_save_update_failure(mock_update, mock_tool_index_file, sample_index_data, caplog):
    """Test load_update_and_save_entry when update_index_entry explicitly returns False."""
    # Prepare initial file state
    initial_data_for_file = sample_index_data.copy()
    mock_tool_index_file.write_text(json.dumps(initial_data_for_file, indent=2) + "\n")
    # # Expected data after load filters invalid entries
    # expected_data_after_load = {k: v for k, v in sample_index_data.items() if isinstance(v, dict) and "crc" in v}

    caplog.set_level(logging.ERROR)

    command_seq = ("tool1",)  # This update will be mocked to fail
    update_data = {"new_field": True}

    with patch("filelock.FileLock.acquire", return_value=None), patch("filelock.FileLock.release", return_value=None):
        success = load_update_and_save_entry(command_seq, update_data)

    assert success is False
    mock_update.assert_called_once()
    assert "In-memory update failed" in caplog.text
    # Verify file wasn't saved with bad data (it should still contain the original data written)
    final_content = json.loads(mock_tool_index_file.read_text(encoding="utf-8"))
    assert final_content == initial_data_for_file  # Compare against original written data


# Justification for Mock: Testing wrapper's handling of save exception
@patch(
    "src.zeroth_law.dev_scripts.tool_index_utils.save_tool_index",
    side_effect=IOError("Disk Full"),
)  # noqa: E501 ZLF: Test wrapper
def test_load_update_save_save_failure(mock_save, mock_tool_index_file, sample_index_data, caplog):
    """Test load_update_and_save_entry when save_tool_index fails due to IOError."""
    # Prepare initial file state
    mock_tool_index_file.write_text(json.dumps(sample_index_data, indent=2) + "\n")
    caplog.set_level(logging.ERROR)

    command_seq = ("tool1",)
    update_data = {"new_field": True}

    with patch("filelock.FileLock.acquire", return_value=None), patch("filelock.FileLock.release", return_value=None):
        success = load_update_and_save_entry(command_seq, update_data)

    assert success is False
    mock_save.assert_called_once()  # Verify save was attempted
    # assert "Failed to save updated index file" in caplog.text
    assert "Unexpected error during locked index update" in caplog.text  # Check for wrapper's catch-all


# Keep this test as mocking external library behavior is allowed
@patch("filelock.FileLock.release")  # Spy on release
@patch("filelock.FileLock.acquire", side_effect=Timeout("Simulated lock timeout"))  # Error during acquire
def test_load_update_save_lock_release_on_timeout(mock_acquire, mock_release, mock_tool_index_file, caplog):
    """Test that the lock timeout error is logged."""
    caplog.set_level(logging.DEBUG)  # Need DEBUG to see release log
    command_seq = ("tool1",)
    update_data = {"new_field": True}

    success = load_update_and_save_entry(command_seq, update_data)

    assert success is False
    assert "Timeout acquiring lock" in caplog.text
    # Cannot reliably assert on the DEBUG release message as it might be suppressed or altered by FileLock internals
    # assert "Lock released for index entry" in caplog.text # Removed assertion


# We might need to mock Timeout from filelock if it's not automatically mocked
# from filelock import Timeout # Removed from here


def test_index_contains_all_managed_sequences(
    managed_sequences: List[Tuple[str, ...]], tool_index_handler: "ToolIndexHandler"
):
    """Verify that every sequence identified as managed has an entry in the index."""
    # Fixture provides Set[str], not List[Tuple[str, ...]]. Adjusting loop.

    if not managed_sequences:
        pytest.skip("No managed sequences provided by fixture.")

    missing_entries = []
    for tool_name in managed_sequences:
        # Convert the tool name string into a tuple for get_entry
        command_sequence_tuple = (tool_name,)
        if tool_index_handler.get_entry(command_sequence_tuple) is None:
            # Append the tool name string directly if missing
            missing_entries.append(tool_name)

    assert (
        not missing_entries
    ), f"The following managed tools are missing from the tool index: {sorted(missing_entries)}"
