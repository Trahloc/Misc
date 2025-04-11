# File: tests/test_config_loader.py
"""Tests for refactored configuration loading functions."""

from pathlib import Path
from unittest import mock

import pytest

from zeroth_law.config_defaults import DEFAULT_CONFIG
from zeroth_law.config_loader import (
    _CONFIG_PATH_ENV_VAR,
    TomlDecodeError,
    extract_config_section,
    find_pyproject_toml,
    load_config,
    merge_with_defaults,
    parse_toml_file,
)


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
        "zeroth_law.config_loader._TOML_LOADER.load",
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
    class MockTOMLDecodeError(Exception):
        pass

    # Mock the dependencies
    with mock.patch("zeroth_law.config_loader._TOMLI") as mock_tomli:
        mock_tomli.TOMLDecodeError = MockTOMLDecodeError
        # TOMLLIB should be None to ensure the tomli error is checked
        with mock.patch("zeroth_law.config_loader._TOMLLIB", None):
            # Make the load function raise the decode error
            with mock.patch(
                "zeroth_law.config_loader._TOML_LOADER.load",
                side_effect=MockTOMLDecodeError("Invalid TOML"),
            ):
                with pytest.raises(TomlDecodeError):
                    parse_toml_file(config_file)


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
    merged = merge_with_defaults(custom_config)

    # Check custom values were kept
    assert merged["max_complexity"] == 5
    assert merged["max_lines"] == 80

    # Check default values were included
    for key in DEFAULT_CONFIG:
        if key not in custom_config:
            assert merged[key] == DEFAULT_CONFIG[key]


def test_merge_with_defaults_validation_error():
    """Test handling validation errors during merging."""
    # Sample invalid config (non-integer complexity)
    invalid_config = {"max_complexity": "not an int"}

    # Merge with defaults (should not raise, but log a warning)
    with mock.patch("zeroth_law.config_loader.validate_config") as mock_validate:
        # Setup mock to raise exception with errors method
        class MockValidationError(Exception):
            def errors(self):
                return [{"loc": ("max_complexity",), "msg": "Not an integer"}]

        mock_validate.side_effect = MockValidationError("Validation error")
        merged = merge_with_defaults(invalid_config)

        # Should use default for the invalid field
        assert merged["max_complexity"] == DEFAULT_CONFIG["max_complexity"]


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
    """Test loading configuration from a valid file."""
    # Create a valid config file
    config_file = tmp_path / "pyproject.toml"
    with open(config_file, "wb") as f:
        f.write(
            b"""
[tool.zeroth-law]
max_complexity = 5
max_lines = 80
        """
        )

    # Load the config
    config = load_config(config_file)

    # Check custom values were loaded
    assert config["max_complexity"] == 5
    assert config["max_lines"] == 80

    # Check default values were included
    for key in DEFAULT_CONFIG:
        if key not in ["max_complexity", "max_lines"]:
            assert config[key] == DEFAULT_CONFIG[key]


def test_load_config_file_not_found():
    """Test loading config when file is not found."""
    # Load with nonexistent file path
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path")

    # Load with auto-detection (should use defaults)
    with mock.patch("zeroth_law.config_loader.find_pyproject_toml", return_value=None):
        config = load_config()
        assert config == DEFAULT_CONFIG


def test_load_config_section_not_found(tmp_path):
    """Test loading config when section is missing."""
    # Create a config file without zeroth-law section
    config_file = tmp_path / "pyproject.toml"
    with open(config_file, "wb") as f:
        f.write(
            b"""
[tool.other-tool]
some_option = "value"
        """
        )

    # Load the config
    config = load_config(config_file)

    # Should use defaults
    assert config == DEFAULT_CONFIG


def test_load_config_integration(tmp_path, monkeypatch):
    """Integration test for the entire config loading process."""
    # Create a valid config file
    config_file = tmp_path / "pyproject.toml"
    with open(config_file, "wb") as f:
        f.write(
            b"""
[tool.zeroth-law]
max_complexity = 5
max_lines = 80
max_parameters = 3
        """
        )

    # Set environment variable to point to the config file
    monkeypatch.setenv(_CONFIG_PATH_ENV_VAR, str(config_file))

    # Load the config without explicit path (should find via env var)
    config = load_config()

    # Check custom values were loaded
    assert config["max_complexity"] == 5
    assert config["max_lines"] == 80
    assert config["max_parameters"] == 3

    # Check default values were included
    for key in DEFAULT_CONFIG:
        if key not in ["max_complexity", "max_lines", "max_parameters"]:
            assert config[key] == DEFAULT_CONFIG[key]
