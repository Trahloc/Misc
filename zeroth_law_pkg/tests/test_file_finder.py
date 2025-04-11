# File: tests/test_file_finder.py
"""Tests for the file_finder module."""

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


# Test Case 3: Exclude Specific Files
def test_exclude_files(tmp_path: Path) -> None:
    """Verify that specific filenames/patterns can be excluded."""
    # Arrange
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / "src" / "utils.py").touch()
    (tmp_path / "src" / "temp_flymake.py").touch()  # Matches default exclude
    (tmp_path / "src" / "legacy_code.py").touch()  # Custom exclude
    (tmp_path / "src" / "sub").mkdir()
    (tmp_path / "src" / "sub" / "another.py").touch()
    (tmp_path / "src" / "sub" / "skip_me.py").touch()  # Custom exclude pattern

    custom_exclude_files = {"legacy_code.py", "skip_*.py"}

    # Act - Use custom file excludes (defaults for dirs)
    found_files = find_python_files(tmp_path / "src", exclude_files=custom_exclude_files)

    # Assert
    found_paths = {p.relative_to(tmp_path / "src") for p in found_files}
    expected_paths = {
        Path("main.py"),
        Path("utils.py"),
        Path("sub/another.py"),
    }
    # Check that expected files are found
    assert found_paths == expected_paths
    # Explicitly check that excluded files are NOT found
    assert Path("src/temp_flymake.py") not in found_files  # Default exclude
    assert Path("src/legacy_code.py") not in found_files  # Custom exclude
    assert Path("src/sub/skip_me.py") not in found_files  # Custom exclude pattern


def test_exclude_dirs(tmp_path: Path) -> None:
    """Verify that specific directory names are excluded."""
    # Arrange
    (tmp_path / "main.py").touch()
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "intermediate.py").touch()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "core.py").touch()
    (tmp_path / "src" / "ignored").mkdir()
    (tmp_path / "src" / "ignored" / "skip_this.py").touch()
    (tmp_path / ".tox").mkdir()
    (tmp_path / ".tox" / "env.py").touch()

    custom_exclude_dirs = {"ignored"}

    # Act
    found_files = find_python_files(tmp_path, exclude_dirs=custom_exclude_dirs)

    # Assert
    found_paths = {p.relative_to(tmp_path) for p in found_files}
    expected_paths = {
        Path("main.py"),
        Path("src/core.py"),
    }
    assert found_paths == expected_paths
    # Explicitly check excluded files are NOT found
    assert tmp_path / "build" / "intermediate.py" not in found_files  # Default exclude
    assert tmp_path / "src" / "ignored" / "skip_this.py" not in found_files  # Custom exclude
    assert tmp_path / ".tox" / "env.py" not in found_files  # Default exclude


def test_combined_exclusions(tmp_path: Path) -> None:
    """Verify combined directory and file exclusions work together."""
    # Arrange
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / "src" / "config_temp.py").touch()  # File exclude
    (tmp_path / "src" / "data").mkdir()  # Dir exclude
    (tmp_path / "src" / "data" / "process.py").touch()
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "utils.py").touch()

    exclude_dirs = {"data"}
    exclude_files = {"config*.py"}

    # Act
    found_files = find_python_files(tmp_path, exclude_dirs=exclude_dirs, exclude_files=exclude_files)

    # Assert
    found_paths = {p.relative_to(tmp_path) for p in found_files}
    expected_paths = {
        Path("src/main.py"),
        Path("lib/utils.py"),
    }
    assert found_paths == expected_paths


def test_empty_dir(tmp_path: Path) -> None:
    """Test running on an empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    found_files = find_python_files(empty_dir)
    assert found_files == []


def test_no_py_files(tmp_path: Path) -> None:
    """Test running on a directory with no Python files."""
    no_py_dir = tmp_path / "no_py"
    no_py_dir.mkdir()
    (no_py_dir / "readme.txt").touch()
    (no_py_dir / "subdir").mkdir()
    (no_py_dir / "subdir" / "config").touch()
    found_files = find_python_files(no_py_dir)
    assert found_files == []


def test_resolved_paths(tmp_path: Path) -> None:
    """Verify that returned paths are resolved absolute paths."""
    (tmp_path / "a.py").touch()
    found_files = find_python_files(tmp_path)
    assert len(found_files) == 1
    found_path = found_files[0]
    assert found_path.is_absolute()
    # Check if it's fully resolved (no .. or . components)
    assert ".." not in found_path.parts
    assert "." not in found_path.parts
    assert found_path == (tmp_path / "a.py").resolve()


# Test Case 4: Non-Existent Start Path
# ... (rest of file) ...

# TODO: Add more tests for exclude_files patterns and edge cases

# <<< ZEROTH LAW FOOTER >>>
