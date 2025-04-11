# FILE: tests/test_cli_refactor.py
"""Tests for refactored CLI functions."""

from pathlib import Path
from unittest.mock import MagicMock, patch


from src.zeroth_law.cli import analyze_files, find_files_to_audit


def test_find_files_to_audit_files_only():
    """Test finding files when only files are provided in paths_to_check."""
    # Arrange
    paths = [Path("file1.py"), Path("file2.py")]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = False

    # Act
    result = find_files_to_audit(paths, recursive, config)

    # Assert
    assert result == paths
    assert len(result) == 2
    assert Path("file1.py") in result
    assert Path("file2.py") in result


def test_find_files_to_audit_with_directory():
    """Test finding files when a directory is provided."""
    # Arrange
    dummy_dir = Path("dummy")
    paths = [dummy_dir]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = True

    # Mock find_python_files to return a list of files
    mock_files = [Path("dummy/file1.py"), Path("dummy/file2.py")]

    with patch("src.zeroth_law.cli.find_python_files", return_value=mock_files) as mock_find:
        # Act
        result = find_files_to_audit(paths, recursive, config)

        # Assert
        mock_find.assert_called_once_with(
            dummy_dir,
            exclude_dirs=set(),
            exclude_files=set(),
        )
        assert result == mock_files
        assert len(result) == 2


def test_find_files_to_audit_mixed_paths():
    """Test finding files when both files and directories are provided."""
    # Arrange
    dummy_file = Path("file1.py")
    dummy_dir = Path("dummy")
    paths = [dummy_file, dummy_dir]
    config = {"exclude_dirs": ["venv"], "exclude_files": ["setup.py"]}
    recursive = True

    # Mock find_python_files to return a list of files
    mock_files = [Path("dummy/file2.py"), Path("dummy/file3.py")]

    with patch("src.zeroth_law.cli.find_python_files", return_value=mock_files) as mock_find:
        # Act
        result = find_files_to_audit(paths, recursive, config)

        # Assert
        mock_find.assert_called_once_with(
            dummy_dir,
            exclude_dirs={"venv"},
            exclude_files={"setup.py"},
        )
        # Result should contain both the explicit file and the found files
        assert sorted(result) == sorted([dummy_file] + mock_files)
        assert len(result) == 3


def test_find_files_to_audit_with_error():
    """Test finding files when an error occurs during directory search."""
    # Arrange
    dummy_dir = Path("dummy")
    paths = [dummy_dir]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = True

    # Mock find_python_files to raise an exception
    with patch("src.zeroth_law.cli.find_python_files", side_effect=Exception("Test error")) as mock_find:
        # Act
        result = find_files_to_audit(paths, recursive, config)

        # Assert
        mock_find.assert_called_once()
        assert result == []  # Should return empty list on error


def test_find_files_to_audit_deduplicates():
    """Test that find_files_to_audit deduplicates files from overlapping paths."""
    # Arrange
    dummy_dir1 = Path("dir1")
    dummy_dir2 = Path("dir2")
    paths = [dummy_dir1, dummy_dir2]
    config = {"exclude_dirs": [], "exclude_files": []}
    recursive = True

    # Mock find_python_files to return overlapping files
    dir1_files = [Path("dir1/file1.py"), Path("common/file.py")]
    dir2_files = [Path("dir2/file2.py"), Path("common/file.py")]  # Duplicate file

    def mock_find_side_effect(path, **kwargs):
        if path == dummy_dir1:
            return dir1_files
        return dir2_files

    with patch("src.zeroth_law.cli.find_python_files", side_effect=mock_find_side_effect) as mock_find:
        # Act
        result = find_files_to_audit(paths, recursive, config)

        # Assert
        assert mock_find.call_count == 2
        assert len(result) == 3  # Should have 3 unique files
        assert Path("dir1/file1.py") in result
        assert Path("dir2/file2.py") in result
        assert Path("common/file.py") in result


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
