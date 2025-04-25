"""Tests for src/zeroth_law/dev_scripts/baseline_writers.py."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
import logging
import os
import sys
import importlib
from src.zeroth_law.dev_scripts.baseline_writers import (
    write_ground_truth_txt,
    ensure_skeleton_json_exists,
    _generate_basic_skeleton,
    main as baseline_writers_main,
)

# Remove the placeholder test
# def test_baseline_writers_run():
#     """Ensures the test file has at least one test."""
#     assert True


# --- Tests for TOOLS_DIR_ROOT logic ---


def test_tools_dir_root_via_env_var(monkeypatch, tmp_path):
    """Test TOOLS_DIR_ROOT via env var by importing *after* setting env var."""
    test_path = tmp_path / "env_var_tools"
    monkeypatch.setenv("ZEROTH_LAW_TEST_TOOLS_DIR", str(test_path))

    # Ensure module isn't already cached from previous tests
    module_name = "src.zeroth_law.dev_scripts.baseline_writers"
    if module_name in sys.modules:
        del sys.modules[module_name]

    # Import the module AFTER setting the env var
    import src.zeroth_law.dev_scripts.baseline_writers as bw

    assert bw.TOOLS_DIR_ROOT == test_path
    # Cleanup module cache
    del sys.modules[module_name]


def test_tools_dir_root_fallback_no_env_var(monkeypatch):
    """Test TOOLS_DIR_ROOT fallback by importing *after* unsetting env var."""
    monkeypatch.delenv("ZEROTH_LAW_TEST_TOOLS_DIR", raising=False)

    # Ensure module isn't already cached
    module_name = "src.zeroth_law.dev_scripts.baseline_writers"
    if module_name in sys.modules:
        del sys.modules[module_name]

    # Import the module AFTER unsetting the env var
    import src.zeroth_law.dev_scripts.baseline_writers as bw

    # Calculate expected path (assuming __file__ is defined in test context)
    try:
        expected_path = Path(bw.__file__).resolve().parents[3] / "src" / "zeroth_law" / "tools"
        assert bw.TOOLS_DIR_ROOT == expected_path
    except AttributeError:
        # If bw.__file__ doesn't exist in test context, this test is less meaningful
        # but we check it doesn't crash and TOOLS_DIR_ROOT got some value
        assert isinstance(bw.TOOLS_DIR_ROOT, Path)

    # Cleanup module cache
    del sys.modules[module_name]


# Note: Testing the NameError fallback within the TOOLS_DIR_ROOT logic
# is complex because it requires creating an execution context where __file__
# is undefined *during module import*. Given the pragma added,
# we will skip explicitly testing this rare fallback.

# --- Tests for write_ground_truth_txt ---


def test_write_ground_truth_txt_success(tmp_path: Path):
    """Test successfully writing a ground truth TXT file."""
    tool_dir = tmp_path / "test_tool"
    tool_id = "test_tool_cmd"
    content = "Line 1\nLine 2"

    # Act
    success = write_ground_truth_txt(tool_dir, tool_id, content)

    # Assert
    assert success
    output_file = tool_dir / f"{tool_id}.txt"
    assert output_file.is_file()
    assert output_file.read_text() == content


def test_write_ground_truth_txt_creates_dir(tmp_path: Path):
    """Test that the target directory is created if it doesn't exist."""
    tool_dir = tmp_path / "new_test_tool"
    tool_id = "new_tool_cmd"
    content = "Content here"

    assert not tool_dir.exists()  # Ensure dir doesn't exist initially

    # Act
    success = write_ground_truth_txt(tool_dir, tool_id, content)

    # Assert
    assert success
    assert tool_dir.is_dir()
    output_file = tool_dir / f"{tool_id}.txt"
    assert output_file.is_file()
    assert output_file.read_text() == content


# --- Tests for ensure_skeleton_json_exists ---


def test_ensure_skeleton_json_exists_creates_new(tmp_path: Path):
    """Test creating a new skeleton JSON when one doesn't exist."""
    tool_dir = tmp_path / "skel_tool"
    tool_id = "skel_tool_cmd"
    cmd_seq = ["skel_tool", "cmd"]
    output_json_path = tool_dir / f"{tool_id}.json"

    assert not output_json_path.exists()

    # Act
    success = ensure_skeleton_json_exists(tool_dir, tool_id, cmd_seq)

    # Assert
    assert success
    assert tool_dir.is_dir()
    assert output_json_path.is_file()

    # Verify content matches expected basic skeleton
    with open(output_json_path, "r") as f:
        data = json.load(f)

    assert data["command_sequence"] == cmd_seq
    assert data["description"] == ""  # Check specific fields if needed
    assert data["usage"] == ""
    assert isinstance(data["options"], list)
    assert isinstance(data["arguments"], list)
    assert isinstance(data["subcommands"], list)
    assert "metadata" in data
    assert "ground_truth_crc" in data["metadata"]
    assert data["metadata"]["ground_truth_crc"] == "0x00000000"
    assert "file_status" not in data["metadata"]  # Ensure disallowed key isn't present


def test_ensure_skeleton_json_exists_skips_existing(tmp_path: Path):
    """Test that an existing skeleton JSON file is not overwritten."""
    tool_dir = tmp_path / "existing_skel_tool"
    tool_id = "existing_cmd"
    cmd_seq = ["existing_skel_tool", "cmd"]
    output_json_path = tool_dir / f"{tool_id}.json"

    # Create a dummy existing file
    tool_dir.mkdir(parents=True, exist_ok=True)
    initial_content = {"existing": True, "metadata": {"ground_truth_crc": "0x12345678"}}
    output_json_path.write_text(json.dumps(initial_content))

    # Act
    success = ensure_skeleton_json_exists(tool_dir, tool_id, cmd_seq)

    # Assert
    assert success  # Function should report success even if skipped
    assert output_json_path.is_file()

    # Verify content was NOT changed
    with open(output_json_path, "r") as f:
        data = json.load(f)
    assert data == initial_content


# --- Tests for Error Handling ---


@patch("builtins.open", new_callable=mock_open)
def test_write_ground_truth_txt_io_error(mock_file, tmp_path: Path):
    """Test write_ground_truth_txt error handling for IOError during write."""
    # Ensure the mock file handle raises IOError when written to
    mock_file.return_value.__enter__.return_value.write.side_effect = IOError("Simulated I/O error")
    tool_dir = tmp_path / "error_tool_txt_io"
    tool_id = "error_cmd_txt_io"
    content = "Fail content"
    output_file = tool_dir / f"{tool_id}.txt"

    # Act
    success = write_ground_truth_txt(tool_dir, tool_id, content)

    # Assert
    assert not success  # Expect failure
    mock_file.assert_called_once_with(output_file, "w", encoding="utf-8")
    mock_file.return_value.__enter__.return_value.write.assert_called_once_with(content)


@patch("src.zeroth_law.dev_scripts.baseline_writers.Path.mkdir")
def test_write_ground_truth_txt_exception(mock_mkdir, tmp_path: Path):
    """Test write_ground_truth_txt error handling for generic Exception during mkdir."""
    mock_mkdir.side_effect = Exception("Simulated generic mkdir error")
    tool_dir = tmp_path / "error_tool_txt_mkdir"
    tool_id = "error_cmd_txt_mkdir"
    content = "Fail content"

    # Act
    success = write_ground_truth_txt(tool_dir, tool_id, content)

    # Assert
    assert not success  # Expect failure
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


@patch("builtins.open", new_callable=mock_open)
def test_ensure_skeleton_json_exists_io_error(mock_file, tmp_path: Path):
    """Test ensure_skeleton_json_exists error handling for IOError during write."""
    mock_file.return_value.__enter__.return_value.write.side_effect = IOError("Simulated I/O error")
    tool_dir = tmp_path / "error_tool_json_io"
    tool_id = "error_cmd_json_io"
    cmd_seq = ["error_tool_json_io", "cmd"]
    output_json_path = tool_dir / f"{tool_id}.json"

    assert not output_json_path.exists()

    # Act
    success = ensure_skeleton_json_exists(tool_dir, tool_id, cmd_seq)

    # Assert
    assert not success  # Expect failure
    mock_file.assert_called_once_with(output_json_path, "w", encoding="utf-8")
    # Check that write was attempted on the file handle (json.dump calls write multiple times)
    assert mock_file.return_value.__enter__.return_value.write.call_count > 0


@patch("src.zeroth_law.dev_scripts.baseline_writers.Path.mkdir")
def test_ensure_skeleton_json_exists_exception(mock_mkdir, tmp_path: Path):
    """Test ensure_skeleton_json_exists error handling for generic Exception during mkdir."""
    mock_mkdir.side_effect = Exception("Simulated generic mkdir error")
    tool_dir = tmp_path / "error_tool_json_mkdir"
    tool_id = "error_cmd_json_mkdir"
    cmd_seq = ["error_tool_json_mkdir", "cmd"]
    output_json_path = tool_dir / f"{tool_id}.json"

    assert not output_json_path.exists()

    # Act
    success = ensure_skeleton_json_exists(tool_dir, tool_id, cmd_seq)

    # Assert
    assert not success  # Expect failure
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


# --- Test __main__ execution ---


def test_main_execution(tmp_path: Path, monkeypatch, caplog):
    """Test running the script's main logic by calling the main() function."""
    test_tools_root = tmp_path / "main_test_direct_call"
    monkeypatch.setenv("ZEROTH_LAW_TEST_TOOLS_DIR", str(test_tools_root))

    caplog.set_level(logging.INFO)

    # Reload the module AFTER setting the env var to ensure TOOLS_DIR_ROOT is updated
    # Need to import the module itself for reload
    import src.zeroth_law.dev_scripts.baseline_writers as bw_module

    importlib.reload(bw_module)

    # Call the main function *from the reloaded module*
    bw_module.main()  # Use reloaded module's main

    # Assertions: Check logs captured by caplog
    assert f"Using test tools directory from env var: {test_tools_root}" in caplog.text
    assert "Testing baseline_writers..." in caplog.text
    assert "TXT write successful." in caplog.text
    assert "TXT content verified." in caplog.text
    assert "Skeleton ensure (1) successful." in caplog.text
    assert "Skeleton content verified." in caplog.text
    assert "Skeleton ensure (2) successful (as expected)." in caplog.text
    assert "Verified skeleton was not overwritten." in caplog.text
    assert "Testing finished." in caplog.text
    assert "Cleaning up test files..." in caplog.text  # Verify cleanup started

    # Check filesystem cleanup
    test_tool_name = "_test_writer_tool"
    test_tool_id = "_test_writer_tool_sub"
    test_tool_dir = test_tools_root / test_tool_name
    test_txt_file = test_tool_dir / f"{test_tool_id}.txt"
    test_json_file = test_tool_dir / f"{test_tool_id}.json"
    assert not test_txt_file.exists(), "Test TXT file was not cleaned up"
    assert not test_json_file.exists(), "Test JSON file was not cleaned up"
    if test_tool_dir.exists():
        assert not list(test_tool_dir.glob("*")), f"Test directory {test_tool_dir} not empty after cleanup"


# --- End of File ---
