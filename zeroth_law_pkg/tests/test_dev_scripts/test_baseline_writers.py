"""Tests for src/zeroth_law/dev_scripts/baseline_writers.py."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from src.zeroth_law.dev_scripts.baseline_writers import (
    write_ground_truth_txt,
    ensure_skeleton_json_exists,
    _generate_basic_skeleton,
)

# Remove the placeholder test
# def test_baseline_writers_run():
#     """Ensures the test file has at least one test."""
#     assert True


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
    """Test write_ground_truth_txt error handling for IOError."""
    mock_file.side_effect = IOError("Simulated I/O error")
    tool_dir = tmp_path / "error_tool_txt_io"
    tool_id = "error_cmd_txt_io"
    content = "Fail content"

    # Act
    success = write_ground_truth_txt(tool_dir, tool_id, content)

    # Assert
    assert not success  # Expect failure
    mock_file.assert_called_once_with(tool_dir / f"{tool_id}.txt", "w", encoding="utf-8")


@patch("builtins.open", new_callable=mock_open)
def test_write_ground_truth_txt_exception(mock_file, tmp_path: Path):
    """Test write_ground_truth_txt error handling for generic Exception."""
    mock_file.side_effect = Exception("Simulated generic write error")
    tool_dir = tmp_path / "error_tool_txt_generic"
    tool_id = "error_cmd_txt_generic"
    content = "Fail content"

    # Act
    success = write_ground_truth_txt(tool_dir, tool_id, content)

    # Assert
    assert not success  # Expect failure
    # We might not reach the open call if mkdir fails, but let's assume it does for now
    # If Path.mkdir were to raise, we'd need another test or adjust this.
    # mock_file.assert_called_once_with(tool_dir / f"{tool_id}.txt", "w", encoding="utf-8")


@patch("builtins.open", new_callable=mock_open)
def test_ensure_skeleton_json_exists_io_error(mock_file, tmp_path: Path):
    """Test ensure_skeleton_json_exists error handling for IOError."""
    mock_file.side_effect = IOError("Simulated I/O error")
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


@patch("builtins.open", new_callable=mock_open)
def test_ensure_skeleton_json_exists_exception(mock_file, tmp_path: Path):
    """Test ensure_skeleton_json_exists error handling for generic Exception."""
    mock_file.side_effect = Exception("Simulated generic write error")
    tool_dir = tmp_path / "error_tool_json_generic"
    tool_id = "error_cmd_json_generic"
    cmd_seq = ["error_tool_json_generic", "cmd"]
    output_json_path = tool_dir / f"{tool_id}.json"

    assert not output_json_path.exists()

    # Act
    success = ensure_skeleton_json_exists(tool_dir, tool_id, cmd_seq)

    # Assert
    assert not success  # Expect failure
    # Again, assuming mkdir works, the open call should be attempted
    # mock_file.assert_called_once_with(output_json_path, "w", encoding="utf-8")
