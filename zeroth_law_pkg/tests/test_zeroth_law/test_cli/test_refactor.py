# FILE: tests/test_cli_refactor.py
"""Tests for refactored CLI functions."""

import pytest  # Import pytest for fixtures
from pathlib import Path
from unittest.mock import MagicMock  # Keep MagicMock for analyzer tests
# Remove patch as we aim to eliminate internal patching here
# from unittest.mock import MagicMock, patch

from src.zeroth_law.cli import analyze_files, find_files_to_audit

# Import the *real* find_python_files to potentially test its behavior if needed,
# although the primary target is testing find_files_to_audit's integration.
from src.zeroth_law.file_finder import find_python_files


# --- Tests for find_files_to_audit ---


def test_find_files_to_audit_files_only(tmp_path):
    """Test finding files when only files are provided in paths_to_check."""
    # Arrange
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    file1.touch()
    file2.touch()
    paths = [file1, file2]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = False  # Not relevant when only files are passed

    # Act
    result = find_files_to_audit(paths, recursive, config)

    # Assert
    assert set(result) == set(paths)  # Use set for order-insensitive comparison
    assert len(result) == 2


def test_find_files_to_audit_with_directory(tmp_path):
    """Test finding files when a directory is provided."""
    # Arrange
    dummy_dir = tmp_path / "dummy"
    dummy_dir.mkdir()
    file1 = dummy_dir / "file1.py"
    file2 = dummy_dir / "file2.py"
    non_py_file = dummy_dir / "readme.md"
    file1.touch()
    file2.touch()
    non_py_file.touch()

    paths = [dummy_dir]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = True

    # Act: Call the real function
    result = find_files_to_audit(paths, recursive, config)

    # Assert: Check against the actual files found
    expected_files = {file1, file2}
    assert set(result) == expected_files
    assert len(result) == 2


def test_find_files_to_audit_mixed_paths(tmp_path):
    """Test finding files when both files and directories are provided."""
    # Arrange
    dummy_file1 = tmp_path / "file1.py"
    dummy_dir = tmp_path / "dummy"
    dummy_dir.mkdir()
    file2 = dummy_dir / "file2.py"
    file3 = dummy_dir / "file3.py"
    # Files/dirs to be excluded
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    venv_file = venv_dir / "ignored.py"
    venv_file.touch()
    setup_file = tmp_path / "setup.py"
    setup_file.touch()

    dummy_file1.touch()
    file2.touch()
    file3.touch()

    paths = [dummy_file1, dummy_dir, setup_file]  # Pass excluded file too
    # Use relative string paths for exclusion config as that's common
    config = {"exclude_dirs": ["venv"], "exclude_files": ["setup.py"]}
    recursive = True

    # Act
    result = find_files_to_audit(paths, recursive, config)

    # Assert
    # Expected: file1.py (explicit), dummy/file2.py, dummy/file3.py
    # Excluded: setup.py (explicitly passed but excluded by config),
    #           venv/ignored.py (in excluded dir)
    expected_files = {dummy_file1, file2, file3}
    assert set(result) == expected_files
    assert len(result) == 3


def test_find_files_to_audit_with_nonexistent_path(tmp_path):
    """Test finding files when a path doesn't exist (should be ignored)."""
    # Arrange
    existent_file = tmp_path / "file1.py"
    existent_file.touch()
    non_existent_path = tmp_path / "not_real.py"
    paths = [existent_file, non_existent_path]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = False

    # Act
    result = find_files_to_audit(paths, recursive, config)

    # Assert
    assert result == [existent_file]  # Only the existing file should be returned
    assert len(result) == 1


def test_find_files_to_audit_deduplicates(tmp_path):
    """Test that find_files_to_audit deduplicates files from overlapping paths."""
    # Arrange
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    common_dir = tmp_path / "common"
    dir1.mkdir()
    dir2.mkdir()
    common_dir.mkdir()

    file1_in_dir1 = dir1 / "file1.py"
    file2_in_dir2 = dir2 / "file2.py"
    common_file = common_dir / "file.py"
    # Explicitly pass the common file as well
    explicit_common_file = common_dir / "file.py"

    file1_in_dir1.touch()
    file2_in_dir2.touch()
    common_file.touch()

    paths = [dir1, dir2, explicit_common_file, common_dir]  # Overlapping paths
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = True

    # Act
    result = find_files_to_audit(paths, recursive, config)

    # Assert
    expected_files = {file1_in_dir1, file2_in_dir2, common_file}
    assert set(result) == expected_files  # Use set for order-insensitivity
    assert len(result) == 3  # Should have 3 unique files


# --- Tests for analyze_files ---
# (These tests already use a mock analyzer, which is acceptable as it represents
# the external analysis logic, not an internal implementation detail being mocked)
# Keep these tests as they are.


def test_analyze_files_no_files():
    """Test analyzing files when no files are provided."""
    # Arrange
    files = []
    config = {
        "max_complexity": 10,
        "max_parameters": 5,
        "max_statements": 50,
        "max_lines": 100,
        "ignore_rules": [],
    }
    mock_analyzer = MagicMock(return_value={})

    # Act
    result, stats = analyze_files(files, config, mock_analyzer)

    # Assert
    assert result == {}
    assert stats["files_analyzed"] == 0
    assert stats["files_with_violations"] == 0
    assert stats["compliant_files"] == 0
    assert not mock_analyzer.called


def test_analyze_files_all_compliant():
    """Test analyzing files when all files are compliant."""
    # Arrange
    files = [Path("file1.py"), Path("file2.py")]
    config = {
        "max_complexity": 10,
        "max_parameters": 5,
        "max_statements": 50,
        "max_lines": 100,
        "ignore_rules": [],
    }
    mock_analyzer = MagicMock(return_value={})  # Empty dict = no violations

    # Act
    result, stats = analyze_files(files, config, mock_analyzer)

    # Assert
    assert result == {}  # No violations
    assert mock_analyzer.call_count == 2
    assert stats["files_analyzed"] == 2
    assert stats["files_with_violations"] == 0
    assert stats["compliant_files"] == 2


def test_analyze_files_with_violations():
    """Test analyzing files when some files have violations."""
    # Arrange
    files = [Path("file1.py"), Path("file2.py")]
    config = {
        "max_complexity": 10,
        "max_parameters": 5,
        "max_statements": 50,
        "max_lines": 100,
        "ignore_rules": [],
    }

    # First file has violations, second is compliant
    def mock_analyzer_side_effect(file_path, **kwargs):
        if file_path == Path("file1.py"):
            return {"complexity": [("function1", 10, 15)]}
        return {}

    mock_analyzer = MagicMock(side_effect=mock_analyzer_side_effect)

    # Act
    result, stats = analyze_files(files, config, mock_analyzer)

    # Assert
    assert len(result) == 1  # One file has violations
    assert Path("file1.py") in result
    assert result[Path("file1.py")] == {"complexity": [("function1", 10, 15)]}
    assert mock_analyzer.call_count == 2
    assert stats["files_analyzed"] == 2
    assert stats["files_with_violations"] == 1
    assert stats["compliant_files"] == 1


def test_analyze_files_with_errors():
    """Test analyzing files when errors occur during analysis."""
    # Arrange
    files = [Path("file1.py"), Path("file2.py"), Path("file3.py")]
    config = {
        "max_complexity": 10,
        "max_parameters": 5,
        "max_statements": 50,
        "max_lines": 100,
        "ignore_rules": [],
    }

    # Define different error scenarios
    def mock_analyzer_side_effect(file_path, **kwargs):
        if file_path == Path("file1.py"):
            return {"complexity": [("function1", 10, 15)]}  # Violations
        if file_path == Path("file2.py"):
            raise FileNotFoundError("File not found")  # File not found error
        raise SyntaxError("Invalid syntax")  # Syntax error

    mock_analyzer = MagicMock(side_effect=mock_analyzer_side_effect)

    # Act
    result, stats = analyze_files(files, config, mock_analyzer)

    # Assert
    assert len(result) == 3  # All files should have entries (violations or errors)
    assert result[Path("file1.py")] == {"complexity": [("function1", 10, 15)]}
    assert result[Path("file2.py")] == {"error": ["File not found during analysis"]}
    assert "SyntaxError" in result[Path("file3.py")]["error"][0]
    assert mock_analyzer.call_count == 3
    assert stats["files_analyzed"] == 3
    assert stats["files_with_violations"] == 3
    assert stats["compliant_files"] == 0
