"""Tests for the config_loader module."""

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Dict, Optional, Set, Type, Union  # - Keep Union needed by noqa C901
from unittest import mock

import pytest

# Import the actual function and defaults we are testing
from src.zeroth_law.config_loader import DEFAULT_CONFIG, TomlDecodeError, find_pyproject_toml, load_config

# Use tomllib for error checking if available
if sys.version_info >= (3, 11):
    import tomllib
else:
    tomllib = None  # Tests needing tomllib might need to be skipped or adapted


# Define our own TomlDecodeError for testing
class TomlDecodeError(Exception):
    """Custom exception for invalid TOML."""


# Test Case 1: Config File Not Found (Automatic Search)
# Mock the find function directly
@mock.patch("src.zeroth_law.config_loader.find_pyproject_toml", return_value=None)
def test_load_config_not_found_auto(mock_find: mock.Mock) -> None:
    """Verify defaults are returned if no config is found by find_pyproject_toml."""
    # Arrange - mock_find is configured by the decorator

    # Act
    loaded_config = load_config()  # No path given, triggers auto search via find

    # Assert
    assert loaded_config == DEFAULT_CONFIG.copy()
    mock_find.assert_called_once()


# Test Case 2: Config File Not Found (Explicit Path)
def test_load_config_file_not_found_explicit_path(tmp_path: Path) -> None:
    """Verify FileNotFoundError is raised if specified config path doesn't exist."""
    # Arrange
    non_existent_path = tmp_path / "non_existent_pyproject.toml"

    # Act & Assert
    with pytest.raises(FileNotFoundError, match=f"Config file not found: {non_existent_path}"):
        load_config(non_existent_path)


# Test Case 3: Load Config via find_pyproject_toml (Simulating XDG or Project Find)
@mock.patch("src.zeroth_law.config_loader.find_pyproject_toml")
@mock.patch("src.zeroth_law.config_loader._TOML_LOADER")
@mock.patch("pathlib.Path.open", new_callable=mock.mock_open)
# We don't mock Path.is_file here, assume find_pyproject_toml worked
def test_load_config_via_find(mock_open: mock.Mock, mock_toml_loader: mock.Mock, mock_find: mock.Mock) -> None:
    """Verify config is loaded correctly when found by find_pyproject_toml."""
    # Arrange
    # Simulate find_pyproject_toml returning a path
    simulated_found_path = Path("/some/found/path/pyproject.toml")
    mock_find.return_value = simulated_found_path

    mock_toml_content = {"tool": {"zeroth-law": {"max_lines": 99}}}
    mock_toml_loader.load.return_value = mock_toml_content

    expected_config = DEFAULT_CONFIG.copy()
    expected_config["max_lines"] = 99

    # Act
    loaded_config = load_config()  # No explicit path, uses mocked find

    # Assert
    assert loaded_config == expected_config
    mock_find.assert_called_once()
    mock_toml_loader.load.assert_called_once()


# Test Case 4: Config File Exists, Zeroth Law Section Missing (Explicit Path)
@mock.patch("src.zeroth_law.config_loader._TOML_LOADER")
@mock.patch("pathlib.Path.open", new_callable=mock.mock_open)
@mock.patch("pathlib.Path.is_file", return_value=True)  # Mock is_file for the provided path
def test_load_config_section_missing(mock_is_file: mock.Mock, mock_open: mock.Mock, mock_toml_loader: mock.Mock, tmp_path: Path) -> None:
    """Verify default config is returned if [tool.zeroth-law] is missing."""
    # Arrange
    mock_toml_content = {"tool": {"poetry": {"name": "zeroth-law"}}, "build-system": {"requires": ["poetry-core"]}}
    mock_toml_loader.load.return_value = mock_toml_content
    config_file_path = tmp_path / "pyproject.toml"

    # Act
    # Call the *real* load_config function
    loaded_config = load_config(config_file_path)

    # Assert
    assert loaded_config == DEFAULT_CONFIG.copy()
    mock_is_file.assert_called_once()
    mock_open.assert_called_once_with("rb")
    mock_toml_loader.load.assert_called_once()


# Test Case 5: Load Specific Values from Config (Explicit Path)
@mock.patch("src.zeroth_law.config_loader._TOML_LOADER")
@mock.patch("pathlib.Path.open", new_callable=mock.mock_open)
@mock.patch("pathlib.Path.is_file", return_value=True)
def test_load_specific_values(mock_is_file: mock.Mock, mock_open: mock.Mock, mock_toml_loader: mock.Mock, tmp_path: Path) -> None:
    """Verify specific values from [tool.zeroth-law] override defaults."""
    # Arrange
    mock_toml_content = {
        "tool": {
            "poetry": {"name": "zeroth-law"},
            "zeroth-law": {
                "max_complexity": 15,
                "max_lines": 150,
                "exclude_dirs": [".git", "__pycache__", "custom_exclude"],
                "ignore_rules": ["HEADER_MISSING_FILE_LINE"],
            },
        },
        "build-system": {"requires": ["poetry-core"]},
    }
    mock_toml_loader.load.return_value = mock_toml_content

    expected_loaded_config = DEFAULT_CONFIG.copy()
    expected_loaded_config.update(
        {
            "max_complexity": 15,
            "max_lines": 150,
            "exclude_dirs": [".git", "__pycache__", "custom_exclude"],
            "ignore_rules": ["HEADER_MISSING_FILE_LINE"],
        }
    )

    config_file_path = tmp_path / "pyproject.toml"

    # Act
    # Call the *real* load_config function
    loaded_config = load_config(config_file_path)

    # Assert
    assert loaded_config == expected_loaded_config
    mock_is_file.assert_called_once()
    mock_open.assert_called_once_with("rb")
    mock_toml_loader.load.assert_called_once()


# Test Case 6: Invalid TOML (Explicit Path)
@pytest.mark.skipif(tomllib is None, reason="tomllib not available (requires Python 3.11+)")
@mock.patch("pathlib.Path.open", new_callable=mock.mock_open)
@mock.patch("pathlib.Path.is_file", return_value=True)
def test_load_config_invalid_toml(mock_is_file: mock.Mock, mock_open: mock.Mock, tmp_path: Path) -> None:
    """Verify RuntimeError is raised for invalid TOML content."""
    # Arrange
    # Configure the mock for _TOML_LOADER.load to raise the custom error
    with (
        mock.patch("src.zeroth_law.config_loader._TOML_LOADER.load", side_effect=TomlDecodeError("Invalid TOML")),
        mock.patch("src.zeroth_law.config_loader._TOMLLIB", None),
        mock.patch("src.zeroth_law.config_loader._TOMLI", None),
    ):
        config_file_path = tmp_path / "pyproject.toml"
        # Act & Assert
        # With _TOMLLIB and _TOMLI patched to None, the exception will be caught in the general handler
        # and re-raised as RuntimeError
        with pytest.raises(RuntimeError, match="Unexpected error loading/parsing config file"):
            load_config(config_file_path)


# Test Case 7: Invalid Type for Config Value (Explicit Path)
@mock.patch("src.zeroth_law.config_loader._TOML_LOADER")
@mock.patch("pathlib.Path.open", new_callable=mock.mock_open)
@mock.patch("pathlib.Path.is_file", return_value=True)
def test_load_config_invalid_type(mock_is_file: mock.Mock, mock_open: mock.Mock, mock_toml_loader: mock.Mock, tmp_path: Path) -> None:
    """Verify config reverts to default if a value has the wrong type."""
    # Arrange
    mock_toml_content = {
        "tool": {
            "zeroth-law": {
                "max_complexity": "not-an-int",  # Invalid type
                "max_lines": 150,
            }
        }
    }
    mock_toml_loader.load.return_value = mock_toml_content

    expected_config = DEFAULT_CONFIG.copy()
    expected_config["max_lines"] = 150  # This override should still apply
    # max_complexity should be reverted to default (10)

    config_file_path = tmp_path / "pyproject.toml"

    # Act
    loaded_config = load_config(config_file_path)

    # Assert
    assert loaded_config == expected_config
    mock_is_file.assert_called_once()
    mock_open.assert_called_once_with("rb")
    mock_toml_loader.load.assert_called_once()


# --- Helper Mock Path Class --- #
class MockPath:
    """Minimal mock for pathlib.Path focusing on find_pyproject_toml needs."""

    def __init__(self: "MockPath", path_str: str | Path, existing_paths: set[str] | None = None) -> None:
        """Initialize MockPath."""
        # Ensure path_str is always a string
        self.path_str: str = str(path_str)
        self._existing_paths: set[str] = existing_paths if existing_paths is not None else set()
        # print(f"[MockPath.__init__] Path: {self.path_str}, Exists?: {self.is_file()}")

    def __truediv__(self: "MockPath", other: str | Path) -> "MockPath":
        """Simulate the / operator for joining paths."""
        # Simulate the / operator, ensuring string joining
        new_path_str = str(Path(self.path_str) / str(other))
        # print(f"[MockPath.__truediv__] {self.path_str} / {other} -> {new_path_str}")
        return MockPath(new_path_str, self._existing_paths)

    def is_file(self: "MockPath") -> bool:
        """Check if this path string exists in the predefined set."""
        return self.path_str in self._existing_paths

    def __fspath__(self: "MockPath") -> str:
        """Return the path string for os.fspath compatibility."""
        return self.path_str

    # Add __str__ and __repr__ for better debugging if needed
    def __str__(self: "MockPath") -> str:
        """Return the path string."""
        return self.path_str

    def __repr__(self: "MockPath") -> str:
        """Return a representation string."""
        return f"MockPath('{self.path_str}')"

    def __eq__(self: "MockPath", other: object) -> bool:
        """Compare MockPath instances based on their path string."""
        # Compare path strings for equality
        return isinstance(other, MockPath) and self.path_str == other.path_str

    def __hash__(self: "MockPath") -> int:
        """Return hash based on the path string."""
        return hash(self.path_str)

    @property
    def parent(self: "MockPath") -> "MockPath":
        """Return the parent directory as a MockPath."""
        # Use real Path for parent calculation, return MockPath
        parent_path_str = str(Path(self.path_str).parent)
        return MockPath(parent_path_str, self._existing_paths)

    @property
    def parents(self: "MockPath") -> Iterator["MockPath"]:
        """Yield parent directories as MockPath instances."""
        # Use real Path for parents calculation, yield MockPath
        path_obj = Path(self.path_str)
        for p in path_obj.parents:
            yield MockPath(str(p), self._existing_paths)

    # Add dummy cwd classmethod if needed by tests patching Path class
    @classmethod
    def cwd(cls: type["MockPath"]) -> "MockPath":
        """Dummy cwd method, relies on mock configuration."""
        # This shouldn't be called directly if mock_path.cwd is configured
        raise NotImplementedError("MockPath.cwd should be configured in the test")


# --- Tests for find_pyproject_toml --- #


@mock.patch("src.zeroth_law.config_loader.Path")
@mock.patch("src.zeroth_law.config_loader.xdg.xdg_config_home")
def test_find_pyproject_toml_in_xdg(mock_xdg_home: mock.Mock, mock_path: mock.Mock) -> None:
    """Verify find_pyproject_toml returns the XDG path if it exists."""
    # Arrange
    fake_xdg_dir_str = "/fake/xdg/config"
    xdg_config_path_str = "/fake/xdg/config/zeroth_law/pyproject.toml"

    # Set of paths that should return True for is_file()
    existing = {xdg_config_path_str}

    # Configure the mock Path class
    mock_path.side_effect = lambda p: MockPath(p, existing_paths=existing)

    # Mock xdg_config_home to return a MockPath instance
    mock_xdg_home.return_value = MockPath(fake_xdg_dir_str, existing_paths=existing)

    # Act
    found_path = find_pyproject_toml()

    # Assert
    assert found_path is not None
    # Compare the returned MockPath with an expected MockPath
    assert found_path == MockPath(xdg_config_path_str, existing)
    mock_xdg_home.assert_called_once()


@mock.patch("src.zeroth_law.config_loader.Path")
@mock.patch("src.zeroth_law.config_loader.xdg.xdg_config_home")
def test_find_pyproject_toml_in_cwd(mock_xdg_home: mock.Mock, mock_path: mock.Mock) -> None:
    """Verify find_pyproject_toml returns CWD path if not in XDG."""
    # Arrange
    fake_xdg_dir_str = "/fake/xdg/config"
    fake_cwd_str = "/fake/project/dir"
    cwd_config_path_str = "/fake/project/dir/pyproject.toml"

    existing = {cwd_config_path_str}

    # Configure the mock Path class
    mock_path.side_effect = lambda p: MockPath(p, existing_paths=existing)
    # Configure the cwd() method on the mock Path class
    mock_path.cwd.return_value = MockPath(fake_cwd_str, existing_paths=existing)

    # Mock xdg_config_home to return MockPath
    mock_xdg_home.return_value = MockPath(fake_xdg_dir_str, existing_paths=existing)

    # Act
    found_path = find_pyproject_toml()

    # Assert
    assert found_path == MockPath(cwd_config_path_str, existing)
    mock_xdg_home.assert_called_once()
    mock_path.cwd.assert_called_once()  # Check if cwd was called on the mocked Path


@mock.patch("src.zeroth_law.config_loader.Path")
@mock.patch("src.zeroth_law.config_loader.xdg.xdg_config_home")
def test_find_pyproject_toml_in_parent(mock_xdg_home: mock.Mock, mock_path: mock.Mock) -> None:
    """Verify find_pyproject_toml finds config in parent directory."""
    # Arrange
    fake_xdg_dir_str = "/fake/xdg/config"
    fake_cwd_str = "/fake/project/subdir"  # Start search from subdir
    parent_config_path_str = "/fake/project/pyproject.toml"

    existing = {parent_config_path_str}

    # Configure mock Path
    mock_path.side_effect = lambda p: MockPath(p, existing_paths=existing)
    mock_path.cwd.return_value = MockPath(fake_cwd_str, existing_paths=existing)

    # Mock xdg_config_home
    mock_xdg_home.return_value = MockPath(fake_xdg_dir_str, existing_paths=existing)

    # Act
    found_path = find_pyproject_toml()

    # Assert
    assert found_path == MockPath(parent_config_path_str, existing)
    mock_xdg_home.assert_called_once()
    mock_path.cwd.assert_called_once()


@mock.patch("src.zeroth_law.config_loader.Path")
@mock.patch("src.zeroth_law.config_loader.xdg.xdg_config_home")
def test_find_pyproject_toml_not_found(mock_xdg_home: mock.Mock, mock_path: mock.Mock) -> None:
    """Verify find_pyproject_toml returns None if no config is found."""
    # Arrange
    fake_xdg_dir_str = "/fake/xdg/config"
    fake_cwd_str = "/fake/project/dir"
    existing: set[str] = set()
    mock_path.side_effect = lambda p: MockPath(p, existing_paths=existing)
    mock_path.cwd.return_value = MockPath(fake_cwd_str, existing_paths=existing)
    mock_xdg_home.return_value = MockPath(fake_xdg_dir_str, existing_paths=existing)
    # Act
    found_path = find_pyproject_toml()
    # Assert
    assert found_path is None
    mock_xdg_home.assert_called_once()
    mock_path.cwd.assert_called_once()


@mock.patch("src.zeroth_law.config_loader.Path")
@mock.patch("src.zeroth_law.config_loader.xdg.xdg_config_home")
def test_find_pyproject_toml_with_start_path(mock_xdg_home: mock.Mock, mock_path: mock.Mock) -> None:
    """Verify find_pyproject_toml starts search from specified path."""
    # Arrange
    fake_xdg_dir_str = "/fake/xdg/config"
    start_dir_str = "/explicit/start/dir"
    start_dir_config_path_str = "/explicit/start/dir/pyproject.toml"
    existing: set[str] = {start_dir_config_path_str}
    mock_path.side_effect = lambda p: MockPath(p, existing_paths=existing)
    mock_xdg_home.return_value = MockPath(fake_xdg_dir_str, existing_paths=existing)
    # Use Path object for type compatibility
    start_path_arg = Path(start_dir_str)
    # Act
    found_path = find_pyproject_toml(start_path=start_path_arg)
    # Assert
    assert found_path == MockPath(start_dir_config_path_str, existing)
    mock_xdg_home.assert_called_once()


# <<< ZEROTH LAW FOOTER >>>
# Copyright 2024 YOUR ORGANIZATION
# File: tests/test_config_loader.py
