"""Tests for file finding functionality."""

from pathlib import Path

from zeroth_law.file_finder import find_python_files


def test_find_python_files_simple(tmp_path: Path) -> None:
    """Verify finding Python files in a simple structure, excluding non-py files."""
    # Arrange
    # Create dummy files and directories
    (tmp_path / "module1.py").touch()
    (tmp_path / "script.py").touch()
    (tmp_path / "data.txt").touch()
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "module2.py").touch()
    (tmp_path / "subdir" / "config.ini").touch()
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib").mkdir()
    (tmp_path / ".venv" / "lib" / "some_dep.py").touch()

    expected_files = {
        tmp_path / "module1.py",
        tmp_path / "script.py",
        tmp_path / "subdir" / "module2.py",
    }

    # Act
    found_files = find_python_files(tmp_path)

    # Assert
    # Compare as sets for order independence
    assert set(found_files) == expected_files


# Next steps: Add tests for excluding specific patterns, empty dirs, non-existent path
