# File: tests/test_config_loader.py
"""Tests for refactored configuration loading functions."""

import tomllib
from pathlib import Path
from unittest import mock
import copy

import pytest
import toml

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
)
from zeroth_law.common.path_utils import ZLFProjectRootNotFoundError  # Import the exception


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
    loaded_config = load_config(config_path_override=config_file)

    # Assertions
    assert isinstance(loaded_config, dict)
    assert loaded_config["max_complexity"] == 5
    assert loaded_config["max_lines"] == 80
    assert loaded_config["max_parameters"] == DEFAULT_CONFIG["max_parameters"]

    # Check managed-tools (raw lists)
    assert "managed-tools" in loaded_config
    assert loaded_config["managed-tools"]["whitelist"] == ["toolA", "toolC:sub1"]
    assert loaded_config["managed-tools"]["blacklist"] == ["toolB:sub1"]

    # Check parsed lists (ParsedHierarchy structure)
    assert "parsed_whitelist" in loaded_config
    assert loaded_config["parsed_whitelist"] == {"toolA": {"_explicit": True}, "toolC": {"sub1": True}}
    assert "parsed_blacklist" in loaded_config
    assert loaded_config["parsed_blacklist"] == {"toolB": {"sub1": True}}

    # Check actions
    assert "actions" in loaded_config
    assert "lint" in loaded_config["actions"]
    assert loaded_config["actions"]["lint"]["command"] == "flake8"


def test_load_config_file_not_found():
    """Test behavior when the configuration file is not found."""
    # Mock find_pyproject_toml to return None
    with mock.patch("zeroth_law.common.config_loader.find_pyproject_toml", return_value=None):
        # Call load_config
        loaded_config = load_config()

    # Expect the default configuration when no file is found
    # Construct expected based on the imported DEFAULT_CONFIG
    expected_config = copy.deepcopy(DEFAULT_CONFIG)
    # Add the default parsed lists expected when managed-tools is missing
    expected_config["managed-tools"] = {"whitelist": [], "blacklist": []}
    expected_config["parsed_whitelist"] = {}
    expected_config["parsed_blacklist"] = {}
    expected_config["actions"] = {}

    assert loaded_config == expected_config


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
    loaded_config = load_config(config_path_override=config_file)

    # Expect the default configuration when the section is missing
    expected_config = copy.deepcopy(DEFAULT_CONFIG)
    # Add the default parsed lists expected when managed-tools is missing
    expected_config["managed-tools"] = {"whitelist": [], "blacklist": []}
    expected_config["parsed_whitelist"] = {}
    expected_config["parsed_blacklist"] = {}
    expected_config["actions"] = {}

    assert loaded_config == expected_config


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
    loaded_config = load_config()

    # Assertions
    assert loaded_config["max_complexity"] == 5
    assert loaded_config["managed-tools"]["whitelist"] == ["toolA"]
    assert loaded_config["parsed_whitelist"] == {"toolA": {"_explicit": True}}

    # Test case where root is not found
    monkeypatch.chdir("/")  # Change to root dir
    # Mock find_project_root to explicitly raise the error if needed for clarity
    with mock.patch("zeroth_law.common.config_loader.find_project_root", side_effect=ZLFProjectRootNotFoundError):
        # Expect default config when root/config not found
        not_found_config = load_config()
        assert not_found_config == DEFAULT_CONFIG


def test_load_config_validation_failure(tmp_path):
    pass  # Add pass statement to fix indentation


# --- Tests for Config Validation --- #
