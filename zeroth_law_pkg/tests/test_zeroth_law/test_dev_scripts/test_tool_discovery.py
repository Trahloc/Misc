"""Tests for src/zeroth_law/dev_scripts/tool_discovery.py."""

import logging
from pathlib import Path
from unittest.mock import patch
import sys  # Added import sys here, check if it was missing before

import pytest  # Added missing import
import yaml
import textwrap

# Import functions/constants to test
from src.zeroth_law.dev_scripts.tool_discovery import (
    load_tools_config,
    get_potential_managed_tools,
    get_existing_tool_dirs,  # Ensure this is imported
    PYPROJECT_PATH,
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

# --- Fixtures ---


@pytest.fixture
def mock_pyproject_file(tmp_path, monkeypatch):
    """Fixture to create a temporary pyproject.toml and patch the constant."""
    # Use a subdirectory within tmp_path to mimic workspace structure if needed
    # For simplicity, place pyproject.toml directly in tmp_path for this test
    mock_file = tmp_path / "pyproject.toml"
    # Patch the constant in the module *where it is used* (tool_discovery)
    monkeypatch.setattr("src.zeroth_law.dev_scripts.tool_discovery.PYPROJECT_PATH", mock_file)
    # Ensure the directory exists if placing it deeper
    mock_file.parent.mkdir(parents=True, exist_ok=True)
    # Start with an empty file, tests will write content as needed
    mock_file.touch()
    yield mock_file
    # Cleanup happens automatically with tmp_path


@pytest.fixture
def mock_venv_bin(tmp_path, monkeypatch):
    """Fixture to create a mock venv bin directory."""
    # ... existing code ...


# --- Tests for load_tools_config (Reading pyproject.toml) ---


def test_load_tools_config_file_not_found(mock_pyproject_file, monkeypatch, caplog):
    """Test behavior when pyproject.toml doesn't exist."""
    # Ensure the mocked file does not exist for this test
    mock_pyproject_file.unlink()
    caplog.set_level(logging.ERROR)
    config = load_tools_config()
    assert config == {"managed_tools": [], "excluded_executables": []}
    assert f"Configuration file not found: {mock_pyproject_file}" in caplog.text


def test_load_tools_config_empty_file(mock_pyproject_file, caplog):
    """Test behavior with an empty pyproject.toml file."""
    # File is empty by default from fixture
    caplog.set_level(logging.ERROR)
    config = load_tools_config()
    # Should return defaults as the structure [tool.zeroth-law...] won't exist
    assert config == {"managed_tools": [], "excluded_executables": []}
    # No error expected here, just missing keys treated as empty lists
    assert not caplog.records


def test_load_tools_config_invalid_toml(mock_pyproject_file, caplog):
    """Test behavior with invalid TOML content."""
    mock_pyproject_file.write_text("invalid toml content = [", encoding="utf-8")
    caplog.set_level(logging.ERROR)
    config = load_tools_config()
    assert config == {"managed_tools": [], "excluded_executables": []}
    assert f"Error loading or parsing {mock_pyproject_file}" in caplog.text


def test_load_tools_config_missing_zlt_section(mock_pyproject_file):
    """Test when [tool.zeroth-law] section is missing."""
    mock_pyproject_file.write_text('[project]\nname = "test"')
    config = load_tools_config()
    assert config == {"managed_tools": [], "excluded_executables": []}


def test_load_tools_config_missing_managed_tools_section(mock_pyproject_file):
    """Test when [tool.zeroth-law.managed-tools] is missing."""
    content = textwrap.dedent(
        """
        [tool.zeroth-law]
        # other_config = true
    """
    )
    mock_pyproject_file.write_text(content)
    config = load_tools_config()
    assert config == {"managed_tools": [], "excluded_executables": []}


def test_load_tools_config_missing_whitelist_blacklist(mock_pyproject_file):
    """Test when whitelist/blacklist keys are missing within managed-tools."""
    content = textwrap.dedent(
        """
        [tool.zeroth-law.managed-tools]
        # empty section
    """
    )
    mock_pyproject_file.write_text(content)
    config = load_tools_config()
    assert config == {"managed_tools": [], "excluded_executables": []}


def test_load_tools_config_invalid_whitelist_type(mock_pyproject_file, caplog):
    """Test when whitelist is not a list of strings."""
    content = textwrap.dedent(
        """
        [tool.zeroth-law.managed-tools]
        whitelist = "not_a_list"
        blacklist = []
    """
    )
    mock_pyproject_file.write_text(content)
    caplog.set_level(logging.ERROR)
    config = load_tools_config()
    assert config == {"managed_tools": [], "excluded_executables": []}
    assert "must be a list of strings" in caplog.text


def test_load_tools_config_invalid_blacklist_type(mock_pyproject_file, caplog):
    """Test when blacklist is not a list of strings."""
    content = textwrap.dedent(
        """
        [tool.zeroth-law.managed-tools]
        whitelist = []
        blacklist = 123 # not a list
    """
    )
    mock_pyproject_file.write_text(content)
    caplog.set_level(logging.ERROR)
    config = load_tools_config()
    assert config == {"managed_tools": [], "excluded_executables": []}
    assert "must be a list of strings" in caplog.text


def test_load_tools_config_success(mock_pyproject_file):
    """Test successful loading of configuration."""
    content = textwrap.dedent(
        """
        [tool.zeroth-law.managed-tools]
        whitelist = ["toolA", "toolB"]
        blacklist = ["toolC"]
    """
    )
    mock_pyproject_file.write_text(content)
    config = load_tools_config()
    assert config == {
        "managed_tools": ["toolA", "toolB"],
        "excluded_executables": ["toolC"],
    }


# --- Tests for get_potential_managed_tools ---
# ... existing code ...
