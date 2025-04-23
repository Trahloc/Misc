"""Tests for src/zeroth_law/dev_scripts/tool_discovery.py."""

import logging
from pathlib import Path
from unittest.mock import patch
import sys  # Added import sys here, check if it was missing before

import pytest  # Added missing import
import yaml

# Import functions/constants to test
from src.zeroth_law.dev_scripts.tool_discovery import (
    load_tools_config,
    save_tools_config,
    get_potential_managed_tools,
    get_existing_tool_dirs,  # Ensure this is imported
    TOOLS_CONFIG_PATH,
    TOOLS_DIR,
)

# --- Tests for get_existing_tool_dirs ---


@pytest.fixture
def mock_tools_dir(tmp_path, monkeypatch):
    """Fixture to manage the TOOLS_DIR for tests."""
    temp_tools_dir = tmp_path / "src" / "zeroth_law" / "tools"
    # Don't create it yet, let tests decide
    monkeypatch.setattr("src.zeroth_law.dev_scripts.tool_discovery.TOOLS_DIR", temp_tools_dir)
    return temp_tools_dir


def test_get_existing_tool_dirs_success(mock_tools_dir):
    """Test finding existing tool directories."""
    mock_tools_dir.mkdir(parents=True)
    (mock_tools_dir / "tool1").mkdir()
    (mock_tools_dir / "tool2").mkdir()
    (mock_tools_dir / "a_file.txt").touch()
    (mock_tools_dir / ".hidden_dir").mkdir()

    result = get_existing_tool_dirs()
    expected = {"tool1", "tool2", ".hidden_dir"}  # Includes hidden
    assert result == expected


def test_get_existing_tool_dirs_base_not_found(mock_tools_dir):
    """Test when the base tools directory does not exist."""
    # Do not create mock_tools_dir
    result = get_existing_tool_dirs()
    assert result == set()


def test_get_existing_tool_dirs_empty(mock_tools_dir):
    """Test when the base tools directory exists but is empty."""
    mock_tools_dir.mkdir(parents=True)
    result = get_existing_tool_dirs()
    assert result == set()


def test_get_existing_tool_dirs_only_files(mock_tools_dir):
    """Test when the base tools directory contains only files."""
    mock_tools_dir.mkdir(parents=True)
    (mock_tools_dir / "file1.py").touch()
    (mock_tools_dir / "config.json").touch()
    result = get_existing_tool_dirs()
    assert result == set()


# --- Tests for __main__ block ---
# TODO (Consider if testing the script execution directly is needed)
