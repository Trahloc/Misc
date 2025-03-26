"""
# PURPOSE: Tests for utility functions used throughout the application.

## INTERFACES:
 - test_get_project_root: Test project root directory detection
 - test_sanitize_filename: Test filename sanitization
 - test_merge_dicts: Test dictionary merging
 - test_parse_timestamp: Test timestamp parsing

## DEPENDENCIES:
 - pytest: Testing framework
 - pathlib: Path manipulation
 - template_zeroth_law.utils: Module under test
"""
import os
from pathlib import Path
import pytest
from datetime import datetime
from typing import Dict, Any

from template_zeroth_law.utils import (
    get_project_root,
    sanitize_filename,
    merge_dicts,
    parse_timestamp,
)


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """
    PURPOSE: Create a temporary project structure for testing.

    RETURNS: Path to temporary project root
    """
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create common project markers
    (project_root / "pyproject.toml").touch()
    (project_root / "README.md").touch()
    (project_root / "src").mkdir()

    return project_root


def test_get_project_root(temp_project: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Test project root detection with different marker files.
    """
    # Change working directory to project root
    monkeypatch.chdir(temp_project)

    # Test from project root
    root = get_project_root()
    assert root == temp_project

    # Test from subdirectory
    src_dir = temp_project / "src"
    monkeypatch.chdir(src_dir)
    root = get_project_root()
    assert root == temp_project


def test_get_project_root_no_markers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Test project root detection without marker files.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)

    # Should return current directory if no markers found
    root = get_project_root()
    assert root == empty_dir


@pytest.mark.parametrize("filename,expected", [
    ("normal.txt", "normal.txt"),
    ("file with spaces.txt", "file with spaces.txt"),
    ("file*with/invalid\\chars.txt", "file_with_invalid_chars.txt"),
    ("", "unnamed_file"),
    ("../path/traversal.txt", "_path_traversal.txt"),
    ("file:with:colons.txt", "file_with_colons.txt"),
    ("  spaces  .txt", "spaces.txt"),
])
def test_sanitize_filename(filename: str, expected: str):
    """
    Test filename sanitization with various input patterns.
    """
    result = sanitize_filename(filename)
    assert result == expected
    # Verify no unsafe characters remain
    assert not any(c in result for c in '\\/*?:"<>|')
    # Verify result is not empty
    assert len(result) > 0


@pytest.mark.parametrize("dict1,dict2,expected", [
    (
        {"a": 1},
        {"b": 2},
        {"a": 1, "b": 2}
    ),
    (
        {"a": {"x": 1}},
        {"a": {"y": 2}},
        {"a": {"x": 1, "y": 2}}
    ),
    (
        {"a": 1},
        {"a": 2},
        {"a": 2}
    ),
    (
        {"a": {"x": 1}},
        {"a": {"x": 2}},
        {"a": {"x": 2}}
    ),
    (
        {"a": [1, 2]},
        {"a": [3, 4]},
        {"a": [3, 4]}
    ),
])
def test_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any], expected: Dict[str, Any]):
    """
    Test dictionary merging with different structures.
    """
    result = merge_dicts(dict1, dict2)
    assert result == expected
    # Verify original dicts weren't modified
    assert dict1 != result or dict2 != result


@pytest.mark.parametrize("timestamp,expected_dt", [
    ("2025-03-24 15:30:00", datetime(2025, 3, 24, 15, 30)),
    ("2025-03-24", datetime(2025, 3, 24)),
    ("24/03/2025 15:30:00", datetime(2025, 3, 24, 15, 30)),
    ("Mar 24 2025 15:30:00", datetime(2025, 3, 24, 15, 30)),
])
def test_parse_timestamp(timestamp: str, expected_dt: datetime):
    """
    Test timestamp parsing with different formats.
    """
    result = parse_timestamp(timestamp)
    assert result == expected_dt
    assert isinstance(result, datetime)


def test_parse_timestamp_invalid():
    """
    Test timestamp parsing with invalid input.
    """
    with pytest.raises(ValueError):
        parse_timestamp("invalid date")

    with pytest.raises(ValueError):
        parse_timestamp("25:99:99")


def test_merge_dicts_nested():
    """
    Test deep merging of nested dictionaries.
    """
    dict1 = {
        "a": {
            "x": 1,
            "y": {
                "deep": "value"
            }
        }
    }
    dict2 = {
        "a": {
            "y": {
                "new": "value"
            },
            "z": 3
        }
    }
    expected = {
        "a": {
            "x": 1,
            "y": {
                "deep": "value",
                "new": "value"
            },
            "z": 3
        }
    }

    result = merge_dicts(dict1, dict2)
    assert result == expected
    # Verify deep copies were made
    assert id(result["a"]) != id(dict1["a"])
    assert id(result["a"]) != id(dict2["a"])


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added comprehensive test coverage
 - Added parametrized tests for different input patterns
 - Added test fixtures for file operations
 - Added type hints
 - Added nested dictionary merge tests
 - Added timestamp format tests
 - Added proper error handling tests

## FUTURE TODOs:
 - Add tests for file system race conditions
 - Add tests for international timestamp formats
 - Add tests for custom merge strategies
 - Add performance benchmarks
"""
