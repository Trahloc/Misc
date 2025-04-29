from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

from zeroth_law.lib.tooling.tools_dir_scanner import get_tool_dirs


def test_scan_with_tool_dirs(tmp_path):
    """Test scanning a directory containing valid tool directories.

    NOTE: get_tool_dirs only scans DIRECT children of the base directory.
    It does NOT recursively scan into subdirs like 'a/', 'b/'.
    This test reflects that behavior.
    """
    tools_base_dir = tmp_path / "tools"
    tools_base_dir.mkdir(parents=True, exist_ok=True)

    # Create a valid direct tool directory
    direct_tool_name = "another_tool"
    direct_tool_dir = tools_base_dir / direct_tool_name
    direct_tool_dir.mkdir()
    (direct_tool_dir / f"{direct_tool_name}.json").touch() # Needs the .json file

    # Create nested directories that should NOT be found by get_tool_dirs
    nested_dir_a = tools_base_dir / "a"
    nested_dir_a.mkdir()
    (nested_dir_a / "tool_a").mkdir()

    nested_dir_b = tools_base_dir / "b"
    nested_dir_b.mkdir()
    (nested_dir_b / "tool_b").mkdir()

    # Create dummy files to ensure only dirs are picked up
    (tools_base_dir / "some_file.txt").touch()
    (nested_dir_a / "another_file.txt").touch()

    # Expected result: Only the direct tool directory
    expected_tools = {direct_tool_name}

    found_tools = get_tool_dirs(tools_base_dir)

    assert found_tools == expected_tools


def test_scan_empty_directory(tmp_path):
    """Test scanning an empty tools directory."""
    tools_base_dir = tmp_path / "tools"
    tools_base_dir.mkdir(parents=True, exist_ok=True)

    found_tools = get_tool_dirs(tools_base_dir)

    assert found_tools == set()


def test_scan_missing_directory():
    """Test scanning when the base tools directory does not exist."""
    missing_path = Path("./non_existent_tools_dir")
    if missing_path.exists():  # Ensure it's gone
        if missing_path.is_dir():
            missing_path.rmdir()
        else:
            missing_path.unlink()

    # Should return an empty set if the base directory is missing
    found_tools = get_tool_dirs(missing_path)
    assert found_tools == set()


def test_scan_directory_with_only_files(tmp_path):
    """Test scanning a directory containing only files, no tool subdirs."""
    tools_base_dir = tmp_path / "tools"
    tools_base_dir.mkdir(parents=True, exist_ok=True)
    (tools_base_dir / "file1.json").touch()
    (tools_base_dir / "tool_index.lock").touch()

    found_tools = get_tool_dirs(tools_base_dir)

    assert found_tools == set()
