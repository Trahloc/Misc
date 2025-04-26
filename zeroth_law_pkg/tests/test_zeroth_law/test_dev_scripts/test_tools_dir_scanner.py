from pathlib import Path

import pytest

from zeroth_law.dev_scripts.tools_dir_scanner import get_tool_dirs


def test_scan_with_tool_dirs(tmp_path):
    """Test scanning a directory containing valid tool directories under alphabetical dirs."""
    tools_base_dir = tmp_path / "tools"
    expected_tools = {"tool_a", "tool_b", "another_tool"}

    # Create dummy tool directories directly under the base path
    for tool_name in expected_tools:
        # Removed the logic for creating nested alphabetical directories
        tool_dir = tools_base_dir / tool_name
        tool_dir.mkdir(parents=True, exist_ok=True)

    # Create a dummy file in the root to ensure only dirs are picked up
    (tools_base_dir / "some_file.txt").touch()
    # Removed creation of nested dummy file
    # (tools_base_dir / "t").mkdir(parents=True, exist_ok=True)
    # (tools_base_dir / "t" / "another_file.txt").touch()

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
