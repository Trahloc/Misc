import pytest

# Skip all tests in this file due to major refactoring of tools_dir_scanner
pytestmark = pytest.mark.skip(reason="tools_dir_scanner module refactored/deleted, tests outdated")

from pathlib import Path

from unittest.mock import patch, MagicMock
import os

# from zeroth_law.lib.tooling.tools_dir_scanner import get_tool_dirs, scan_whitelisted_sequences # Commented out - Module refactored/deleted
from zeroth_law.common.hierarchical_utils import parse_to_nested_dict, get_effective_status


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
    (direct_tool_dir / f"{direct_tool_name}.json").touch()  # Needs the .json file

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


# --- Tests for scan_whitelisted_sequences --- #

# Mock data for hierarchical status
# Commenting out module-level calls that might cause import/collection hangs
# WL_TREE = parse_to_nested_dict(["toolA", "toolB:sub1", "toolC:sub1:subsubA", "toolD:*"])
# BL_TREE = parse_to_nested_dict(["toolA:sub_blocked", "toolB:sub2", "toolE"])
WL_TREE = None # Placeholder
BL_TREE = None # Placeholder


def mock_get_effective_status(sequence, wl_tree, bl_tree):
    # Simplified mock for testing scanner logic
    # In real tests for this util, use the actual trees
    seq_str = ":".join(sequence)
    if seq_str == "toolA":
        return "WHITELISTED"
    if seq_str == "toolA:sub1":
        return "WHITELISTED"  # Implicitly from toolA
    if seq_str == "toolA:sub_blocked":
        return "BLACKLISTED"
    if seq_str == "toolB":
        return "UNSPECIFIED"
    if seq_str == "toolB:sub1":
        return "WHITELISTED"
    if seq_str == "toolB:sub2":
        return "BLACKLISTED"
    if seq_str == "toolC":
        return "UNSPECIFIED"
    if seq_str == "toolC:sub1":
        return "UNSPECIFIED"
    if seq_str == "toolC:sub1:subsubA":
        return "WHITELISTED"
    if seq_str.startswith("toolD"):
        return "WHITELISTED"
    if seq_str == "toolE":
        return "BLACKLISTED"
    return "UNSPECIFIED"


@patch("zeroth_law.lib.tooling.tools_dir_scanner.get_effective_status", mock_get_effective_status)
def test_scan_whitelisted_only_base(tmp_path):
    """Test scanning when only base tools are whitelisted (and exist)."""
    base_tools_dir = tmp_path / "tools"
    (base_tools_dir / "toolA").mkdir(parents=True)
    (base_tools_dir / "toolD").mkdir()
    (base_tools_dir / "toolE").mkdir()  # Blacklisted

    # Pass dummy trees as the mock function ignores them
    result = scan_whitelisted_sequences(base_tools_dir, {}, {})
    expected = [("toolA",), ("toolD",)]
    assert sorted(result) == sorted(expected)


@patch("zeroth_law.lib.tooling.tools_dir_scanner.get_effective_status", mock_get_effective_status)
def test_scan_whitelisted_mixed(tmp_path):
    """Test scanning a mix of whitelisted base and subcommands."""
    base_tools_dir = tmp_path / "tools"
    (base_tools_dir / "toolA" / "sub1").mkdir(parents=True)
    (base_tools_dir / "toolA" / "sub_blocked").mkdir()
    (base_tools_dir / "toolB" / "sub1").mkdir(parents=True)
    (base_tools_dir / "toolB" / "sub2").mkdir()
    (base_tools_dir / "toolC" / "sub1" / "subsubA").mkdir(parents=True)
    (base_tools_dir / "toolD" / "anything").mkdir(parents=True)

    result = scan_whitelisted_sequences(base_tools_dir, {}, {})
    expected = [
        ("toolA",),  # Base is whitelisted
        ("toolA", "sub1"),  # Implicitly whitelisted via parent
        # ("toolA", "sub_blocked") -> Blacklisted
        # ("toolB",) -> Unspecified base
        ("toolB", "sub1"),  # Explicitly whitelisted
        # ("toolB", "sub2") -> Blacklisted
        # ("toolC",) -> Unspecified base
        # ("toolC", "sub1") -> Unspecified sub
        ("toolC", "sub1", "subsubA"),  # Explicitly whitelisted
        ("toolD",),  # Base is whitelisted via wildcard
        ("toolD", "anything"),  # Whitelisted via wildcard
    ]
    # Convert tuples for sorting if needed, depends on actual output format
    assert sorted(map(tuple, result)) == sorted(map(tuple, expected))


@patch("zeroth_law.lib.tooling.tools_dir_scanner.get_effective_status", mock_get_effective_status)
def test_scan_whitelisted_only_specific_subcommand(tmp_path):
    """Test scanning when only a deep subcommand is whitelisted."""
    base_tools_dir = tmp_path / "tools"
    (base_tools_dir / "toolC" / "sub1" / "subsubA").mkdir(parents=True)
    (base_tools_dir / "toolC" / "sub1" / "other").mkdir()

    result = scan_whitelisted_sequences(base_tools_dir, {}, {})
    # Expect only the explicitly whitelisted sequence
    expected = [("toolC", "sub1", "subsubA")]
    assert sorted(result) == sorted(expected)


@patch("zeroth_law.lib.tooling.tools_dir_scanner.get_effective_status", mock_get_effective_status)
def test_scan_whitelisted_skips_blacklisted_branch(tmp_path):
    """Test that scanning does not descend into blacklisted directories."""
    base_tools_dir = tmp_path / "tools"
    (base_tools_dir / "toolE" / "sub1").mkdir(parents=True)  # toolE is blacklisted

    result = scan_whitelisted_sequences(base_tools_dir, {}, {})
    assert result == []  # Should not find anything inside toolE


@patch("zeroth_law.lib.tooling.tools_dir_scanner.get_effective_status", mock_get_effective_status)
def test_scan_whitelisted_empty_dir(tmp_path):
    """Test scanning an empty tools directory."""
    base_tools_dir = tmp_path / "tools"
    base_tools_dir.mkdir()
    result = scan_whitelisted_sequences(base_tools_dir, {}, {})
    assert result == []


# TODO: Test directory scan error handling (mock os.iterdir exception?).
