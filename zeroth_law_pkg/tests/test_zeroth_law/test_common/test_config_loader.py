# File: tests/test_config_loader.py
"""Tests for refactored configuration loading functions."""

import tomllib
from pathlib import Path
from unittest import mock
import copy
import pytest
import toml
import tomlkit
from unittest.mock import patch, mock_open
from pydantic import ValidationError

# Import necessary components from the config_loader module
from zeroth_law.common.config_loader import (
    DEFAULT_CONFIG,
    load_config,
    merge_with_defaults,
    find_pyproject_toml,  # Add missing function
    parse_toml_file,  # Add missing function
    extract_config_section,  # Add missing function
    TomlDecodeError,  # Add missing exception base class
    # Import constants used in tests (consider if they should be exposed or tests refactored)
    _CONFIG_PATH_ENV_VAR,  # Add missing constant
    _XDG_CONFIG_HOME_ENV_VAR,  # Add missing constant
    validate_config,
    parse_to_nested_dict,
    check_list_conflicts,
)
from zeroth_law.common.path_utils import ZLFProjectRootNotFoundError  # Import the exception
from zeroth_law.common.hierarchical_utils import ParsedHierarchy
from zeroth_law.config_defaults import DEFAULT_CONFIG as config_defaults
from tomlkit import parse as tomlkit_parse, dumps as tomlkit_dumps

# Import ConfigModel from correct location
from zeroth_law.common.config_validation import ConfigModel

# Commenting out potentially problematic import
# from zeroth_law.common.config_validation import (
#     validate_config,
#     ConfigModel
# )
from zeroth_law.common.path_utils import (
    find_project_root,
    # ZLFProjectRootNotFoundError,  # Already imported from config_loader
)

# Define sample data for hierarchical list parsing test
VALID_LIST_DATA = [
    "toolA",
    "toolB:sub1,sub2",
    "toolC:*",
    "toolD:subD1:subD2",
    "toolE:subE1:*",
    "toolF::invalid",  # Should be skipped by parser
    ":invalid",  # Should be skipped
    "toolG:subG1, subG2",  # Test whitespace
]

EXPECTED_PARSED_LIST = {
    "toolA": {"_explicit": True, "_all": False},
    "toolB": {
        "_explicit": False,
        "_all": False,
        "sub1": {"_explicit": True, "_all": False},
        "sub2": {"_explicit": True, "_all": False},
    },
    "toolC": {"_explicit": False, "_all": True},
    "toolD": {
        "_explicit": False,
        "_all": False,
        "subD1": {
            "_explicit": False,
            "_all": False,
            "subD2": {"_explicit": True, "_all": False},
        },
    },
    "toolE": {
        "_explicit": False,
        "_all": False,
        "subE1": {"_explicit": False, "_all": True},
    },
    "toolG": {
        "_explicit": False,
        "_all": False,
        "subG1": {"_explicit": True, "_all": False},
        "subG2": {"_explicit": True, "_all": False},
    },
}


def test_parse_toml_file_success(tmp_path):
    """Test successful parsing of a valid TOML file."""
    config_file = tmp_path / "pyproject.toml"
    with open(config_file, "wb") as f:
        f.write(
            b"""
[tool.zeroth-law]
max_complexity = 5
max_lines = 80
        """
        )

    result = parse_toml_file(config_file)
    assert isinstance(result, dict)
    assert "tool" in result
    assert "zeroth-law" in result["tool"]
    assert result["tool"]["zeroth-law"]["max_complexity"] == 5


def test_parse_toml_file_not_found():
    """Test handling of file not found during parsing."""
    with pytest.raises(FileNotFoundError):
        parse_toml_file(Path("/nonexistent/path"))


def test_parse_toml_file_import_error(tmp_path):
    """Test handling of an ImportError during TOML parsing."""
    # Create a file that exists
    config_file = tmp_path / "pyproject.toml"
    config_file.touch()

    # Mock the TOML loader to raise ImportError
    with mock.patch(
        "src.zeroth_law.common.config_loader._TOML_LOADER.load",
        side_effect=ImportError("No module named 'tomli'"),
    ):
        with pytest.raises(ImportError):
            parse_toml_file(config_file)


def test_parse_toml_file_decode_error(tmp_path):
    """Test handling of a TomlDecodeError during parsing."""
    # Create a file that exists
    config_file = tmp_path / "pyproject.toml"
    config_file.touch()

    # Create an exception that will match the TOML error check
    # Use tomllib.TOMLDecodeError directly
    class MockTOMLDecodeError(tomllib.TOMLDecodeError):
        pass

    # Mock the dependencies - mock tomllib.load
    with mock.patch(
        "src.zeroth_law.common.config_loader.tomllib.load",
        side_effect=MockTOMLDecodeError("Mock decode error"),
    ) as mock_load:
        # Act & Assert
        with pytest.raises(TomlDecodeError, match="Invalid TOML"):
            parse_toml_file(config_file)
        mock_load.assert_called_once()


def test_extract_config_section():
    """Test extracting a config section from TOML data."""
    # Sample parsed TOML data
    toml_data = {
        "tool": {
            "zeroth-law": {
                "max_complexity": 5,
                "max_lines": 80,
            }
        }
    }

    # Extract the section
    section = extract_config_section(toml_data, "tool.zeroth-law")
    assert section == {"max_complexity": 5, "max_lines": 80}


def test_extract_config_section_missing():
    """Test extracting a missing config section."""
    # Sample parsed TOML data with missing section
    toml_data = {"tool": {}}

    # Extract the section
    section = extract_config_section(toml_data, "tool.zeroth-law")
    assert section == {}


def test_extract_config_section_invalid_type():
    """Test extracting a section that is not a dictionary."""
    # Sample parsed TOML data with invalid section type
    toml_data = {"tool": {"zeroth-law": "not a dict"}}

    # Extract the section
    section = extract_config_section(toml_data, "tool.zeroth-law")
    assert section == {}


def test_merge_with_defaults():
    """Test merging custom config with defaults."""
    # Sample custom config
    custom_config = {"max_complexity": 5, "max_lines": 80}

    # Merge with defaults
    merged = merge_with_defaults(custom_config, DEFAULT_CONFIG)

    # Assertions
    assert merged["max_complexity"] == 5  # Custom value
    assert merged["max_lines"] == 80  # Custom value
    assert merged["max_parameters"] == DEFAULT_CONFIG["max_parameters"]  # Default
    assert "actions" not in merged  # Ensure actions key is excluded


def test_merge_with_defaults_validation_error():
    """Test handling validation errors during merging."""
    # Sample invalid config (non-integer complexity)
    invalid_config = {"max_complexity": "not an int"}

    # Merge with defaults (should not raise, but log a warning)
    with mock.patch("src.zeroth_law.common.config_loader.validate_config") as mock_validate:
        # Setup mock to raise exception with errors method
        class MockValidationError(Exception):
            def errors(self):
                return [{"loc": ("max_complexity",), "msg": "Not an integer"}]

        mock_validate.side_effect = MockValidationError("Validation error")
        merged = merge_with_defaults(invalid_config, DEFAULT_CONFIG)

    # Assert that the invalid field reverts to default
    assert merged["max_complexity"] == DEFAULT_CONFIG["max_complexity"]
    # Assert other fields retain their defaults
    assert merged["max_lines"] == DEFAULT_CONFIG["max_lines"]
    assert "actions" not in merged


def test_find_pyproject_toml_env_var(monkeypatch, tmp_path):
    """Test finding pyproject.toml using environment variable."""
    config_file = tmp_path / "custom_config.toml"
    config_file.touch()  # Create an empty file

    # Set environment variable
    monkeypatch.setenv(_CONFIG_PATH_ENV_VAR, str(config_file))

    # Find the config file
    found_path = find_pyproject_toml()
    assert found_path == config_file


def test_find_pyproject_toml_xdg(monkeypatch, tmp_path):
    """Test finding pyproject.toml in XDG config directory."""
    # Set up XDG config directory
    xdg_dir = tmp_path / ".config" / "zeroth-law"
    xdg_dir.mkdir(parents=True)
    config_file = xdg_dir / "pyproject.toml"
    config_file.touch()  # Create an empty file

    # Set environment variable
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

    # Mock environment variable absence
    monkeypatch.delenv(_CONFIG_PATH_ENV_VAR, raising=False)

    # Find the config file
    found_path = find_pyproject_toml()
    assert found_path == config_file


def test_find_pyproject_toml_cwd(monkeypatch, tmp_path):
    """Test finding pyproject.toml in current directory."""
    # Create config file in current directory
    config_file = tmp_path / "pyproject.toml"
    config_file.touch()  # Create an empty file

    # Mock environment variable absence
    monkeypatch.delenv(_CONFIG_PATH_ENV_VAR, raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    # Mock current working directory
    with mock.patch("pathlib.Path.cwd", return_value=tmp_path):
        # Find the config file
        found_path = find_pyproject_toml()
        assert found_path == config_file


def test_find_pyproject_toml_parent_dir(monkeypatch, tmp_path):
    """Test finding pyproject.toml in parent directory."""
    # Create directory structure
    parent_dir = tmp_path / "parent"
    child_dir = parent_dir / "child"
    parent_dir.mkdir()
    child_dir.mkdir()

    # Create config file in parent directory
    config_file = parent_dir / "pyproject.toml"
    config_file.touch()  # Create an empty file

    # Mock environment variable absence
    monkeypatch.delenv(_CONFIG_PATH_ENV_VAR, raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    # Mock current working directory
    with mock.patch("pathlib.Path.cwd", return_value=child_dir):
        # Find the config file
        found_path = find_pyproject_toml()
        assert found_path == config_file


def test_find_pyproject_toml_not_found(monkeypatch, tmp_path):
    """Test behavior when no pyproject.toml is found."""
    # Mock environment variable absence
    monkeypatch.delenv(_CONFIG_PATH_ENV_VAR, raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    # Mock current working directory to a directory without pyproject.toml
    with mock.patch("pathlib.Path.cwd", return_value=tmp_path):
        # Mock parent directories to ensure no config is found
        with mock.patch("pathlib.Path.parents", new_callable=mock.PropertyMock) as mock_parents:
            mock_parents.return_value = []
            # Find the config file
            found_path = find_pyproject_toml()
            assert found_path is None


def test_load_config_with_valid_file(tmp_path):
    """Test loading a valid configuration file."""
    config_file = tmp_path / "pyproject.toml"
    config_content = """
[tool.zeroth-law]
max_complexity = 5
max_lines = 80

[tool.zeroth-law.managed-tools]
whitelist = ["toolA", "toolC:sub1"]
blacklist = ["toolB:sub1"]

[tool.zeroth-law.actions.lint]
command = "flake8"
    """
    config_file.write_text(config_content, encoding="utf-8")

    # Call load_config using the explicit path override
    loaded_config = load_config(project_root=None, config_path_override=config_file)

    # Assertions
    assert loaded_config is not None
    assert loaded_config.get("max_complexity") == 5
    assert loaded_config.get("max_lines") == 80
    # Check that defaults are merged (example: exclude_dirs)
    assert "exclude_dirs" in loaded_config
    assert isinstance(loaded_config["exclude_dirs"], list)
    # Check parsed lists
    assert "parsed_whitelist" in loaded_config
    assert "parsed_blacklist" in loaded_config
    assert loaded_config["parsed_whitelist"] == {
        "toolA": {"_explicit": True, "_all": False},
        "toolC": {
            "sub1": {"_explicit": True, "_all": False},
            "_explicit": False,
            "_all": False,
        },
    }
    assert loaded_config["parsed_blacklist"] == {
        "toolB": {
            "sub1": {"_explicit": True, "_all": False},
            "_explicit": False,
            "_all": False,
        }
    }


def test_load_config_file_not_found():
    """Test behavior when the configuration file is not found."""
    # Mock find_pyproject_toml to return None
    with mock.patch("zeroth_law.common.config_loader.find_project_root", return_value=None):
        # Call load_config
        loaded_config = load_config(project_root=None)

        # Expect default configuration to be loaded and validated
        assert loaded_config is not None
        assert loaded_config.get("max_complexity") == DEFAULT_CONFIG["max_complexity"]
        assert loaded_config.get("max_lines") == DEFAULT_CONFIG["max_lines"]
        assert "parsed_whitelist" in loaded_config
        assert "parsed_blacklist" in loaded_config
        # Check if default lists are parsed correctly
        default_wl = DEFAULT_CONFIG.get("managed_tools", {}).get("whitelist", [])
        default_bl = DEFAULT_CONFIG.get("managed_tools", {}).get("blacklist", [])
        assert loaded_config["parsed_whitelist"] == parse_to_nested_dict(default_wl)
        assert loaded_config["parsed_blacklist"] == parse_to_nested_dict(default_bl)


def test_load_config_section_not_found(tmp_path):
    """Test behavior when the config file exists but the section is missing."""
    config_file = tmp_path / "pyproject.toml"
    # Create a file without the [tool.zeroth-law] section
    config_content = """
[tool.other-tool]
setting = true
        """
    config_file.write_text(config_content)

    # Call load_config with the explicit path
    loaded_config = load_config(project_root=None, config_path_override=config_file)

    # Expect default configuration
    assert loaded_config is not None
    assert loaded_config.get("max_complexity") == DEFAULT_CONFIG["max_complexity"]
    assert "parsed_whitelist" in loaded_config  # Check default lists were parsed
    # Check if default lists are parsed correctly
    default_wl = DEFAULT_CONFIG.get("managed_tools", {}).get("whitelist", [])
    default_bl = DEFAULT_CONFIG.get("managed_tools", {}).get("blacklist", [])
    assert loaded_config["parsed_whitelist"] == parse_to_nested_dict(default_wl)
    assert loaded_config["parsed_blacklist"] == parse_to_nested_dict(default_bl)


def test_load_config_integration(tmp_path, monkeypatch):
    """Test the overall load_config function with integration aspects."""
    # Add import here if it wasn't added at the top level correctly
    from zeroth_law.common.path_utils import ZLFProjectRootNotFoundError

    # Setup: Create a dummy pyproject.toml
    config_file = tmp_path / "pyproject.toml"
    config_content = """
[tool.zeroth-law]
max_complexity = 5
[tool.zeroth-law.managed-tools]
whitelist = ["toolA"] # Ensure managed-tools exists
    """
    config_file.write_text(config_content)

    # Mock CWD to tmp_path
    monkeypatch.chdir(tmp_path)
    # Ensure env vars are unset
    monkeypatch.delenv(_CONFIG_PATH_ENV_VAR, raising=False)
    monkeypatch.delenv(_XDG_CONFIG_HOME_ENV_VAR, raising=False)

    # Call load_config (no override, should find via upward search)
    # Here, find_project_root WILL find tmp_path, so pass it
    loaded_config = load_config(project_root=tmp_path)

    # Assertions
    assert loaded_config is not None
    assert loaded_config.get("max_complexity") == 5
    # Check default merging
    assert "exclude_dirs" in loaded_config
    assert "parsed_whitelist" in loaded_config
    assert loaded_config["parsed_whitelist"] == {"toolA": {"_explicit": True, "_all": False}}


def test_load_config_validation_failure(tmp_path):
    pass  # Add pass statement to fix indentation


# --- Tests for Config Validation --- #


def test_parse_hierarchical_list_valid():
    parsed = parse_to_nested_dict(VALID_LIST_DATA)
    assert parsed == EXPECTED_PARSED_LIST


def test_parse_hierarchical_list_empty():
    assert parse_to_nested_dict([]) == {}


def test_parse_hierarchical_list_invalid_type():
    assert parse_to_nested_dict(None) == {}
    assert parse_to_nested_dict(123) == {}


def test_check_list_conflicts_no_conflict():
    wl = parse_to_nested_dict(["toolA", "toolB:sub1"])
    bl = parse_to_nested_dict(["toolC", "toolB:sub2"])
    assert check_list_conflicts(wl, bl) == []


def test_check_list_conflicts_simple_conflict():
    wl = parse_to_nested_dict(["toolA", "toolB:sub1"])
    bl = parse_to_nested_dict(["toolA", "toolC"])
    conflicts = check_list_conflicts(wl, bl)
    assert len(conflicts) == 1
    assert conflicts[0] == ("toolA",)


def test_check_list_conflicts_sub_conflict():
    wl = parse_to_nested_dict(["toolA:sub", "toolB"])
    bl = parse_to_nested_dict(["toolC", "toolA:sub"])
    conflicts = check_list_conflicts(wl, bl)
    assert len(conflicts) == 1
    assert conflicts[0] == ("toolA", "sub")


def test_check_list_conflicts_parent_child_conflict_1():
    """Whitelist parent, blacklist child -> Conflict"""
    wl = parse_to_nested_dict(["toolA:*", "toolB"])
    bl = parse_to_nested_dict(["toolA:sub1", "toolC"])
    conflicts = check_list_conflicts(wl, bl)
    assert len(conflicts) == 1
    assert conflicts[0] == ("toolA", "sub1")


def test_check_list_conflicts_parent_child_conflict_2():
    """Blacklist parent, whitelist child -> Conflict"""
    wl = parse_to_nested_dict(["toolA:sub1", "toolB"])
    bl = parse_to_nested_dict(["toolA:*", "toolC"])
    conflicts = check_list_conflicts(wl, bl)
    assert len(conflicts) == 1
    assert conflicts[0] == ("toolA", "sub1")


def test_check_list_conflicts_multiple():
    wl = parse_to_nested_dict(["toolA", "toolB:sub", "toolC:*"])
    bl = parse_to_nested_dict(["toolD", "toolB:sub", "toolC:subsub"])
    conflicts = check_list_conflicts(wl, bl)
    assert len(conflicts) == 2
    # Order might vary depending on dict iteration
    assert set(conflicts) == {("toolB", "sub"), ("toolC", "subsub")}
