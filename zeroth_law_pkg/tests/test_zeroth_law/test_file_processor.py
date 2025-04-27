# New file: tests/test_file_processor.py
"""Tests for src/zeroth_law/file_processor.py"""

import pytest
from pathlib import Path
from src.zeroth_law.file_processor import find_files_to_audit


# Helper function to create dummy files/dirs
def create_structure(base_path: Path, structure: dict):
    for name, content in structure.items():
        path = base_path / name
        if isinstance(content, dict):
            path.mkdir()
            create_structure(path, content)
        elif isinstance(content, str):
            path.write_text(content)
        # Add handling for other types if needed, e.g., None for empty dir


# --- Test Cases ---


def test_find_files_direct_py_file(tmp_path: Path):
    """Test finding a single Python file provided directly."""
    py_file = tmp_path / "module.py"
    py_file.touch()
    non_py_file = tmp_path / "data.txt"
    non_py_file.touch()

    config = {}
    paths_to_check = [py_file, non_py_file]
    result = find_files_to_audit(paths_to_check, recursive=False, config=config)

    assert result == [py_file]


def test_find_files_non_existent_path(tmp_path: Path, caplog):
    """Test providing a path that does not exist."""
    py_file = tmp_path / "module.py"
    py_file.touch()
    non_existent = tmp_path / "not_real.py"

    config = {}
    paths_to_check = [py_file, non_existent]
    result = find_files_to_audit(paths_to_check, recursive=False, config=config)

    assert result == [py_file]
    assert f"Path does not exist, skipping: {non_existent}" in caplog.text


def test_find_files_in_directory_recursive(tmp_path: Path):
    """Test finding Python files recursively in a directory."""
    structure = {
        "main.py": "",
        "subdir": {"sub.py": "", "data.txt": ""},
        "other.txt": "",
    }
    create_structure(tmp_path, structure)

    config = {}
    paths_to_check = [tmp_path]
    result = find_files_to_audit(paths_to_check, recursive=True, config=config)

    expected = sorted([tmp_path / "main.py", tmp_path / "subdir" / "sub.py"])
    assert result == expected


def test_find_files_in_directory_non_recursive(tmp_path: Path, caplog):
    """Test searching a directory non-recursively."""
    structure = {"main.py": "", "subdir": {"sub.py": ""}}
    create_structure(tmp_path, structure)

    config = {}
    paths_to_check = [tmp_path]
    result = find_files_to_audit(paths_to_check, recursive=False, config=config)

    assert result == []  # Should not find main.py as it's not recursive
    assert f"Directory found but recursive search is off, skipping: {tmp_path}" in caplog.text


def test_find_files_exclude_file_direct(tmp_path: Path):
    """Test excluding a directly provided file via config."""
    py_file = tmp_path / "module.py"
    py_file.touch()
    excluded_file = tmp_path / "exclude_me.py"
    excluded_file.touch()

    config = {"exclude_files": ["exclude_me.py"]}
    paths_to_check = [py_file, excluded_file]
    result = find_files_to_audit(paths_to_check, recursive=False, config=config)

    assert result == [py_file]


def test_find_files_exclude_file_recursive(tmp_path: Path):
    """Test excluding files found recursively via config."""
    structure = {
        "main.py": "",
        "subdir": {"sub.py": "", "exclude_me.py": ""},
        "exclude_me.py": "",  # Exclude at top level too
    }
    create_structure(tmp_path, structure)

    config = {"exclude_files": ["exclude_me.py"]}
    paths_to_check = [tmp_path]
    result = find_files_to_audit(paths_to_check, recursive=True, config=config)

    expected = sorted([tmp_path / "main.py", tmp_path / "subdir" / "sub.py"])
    assert result == expected


def test_find_files_exclude_dir_recursive(tmp_path: Path):
    """Test excluding directories found recursively via config."""
    structure = {
        "main.py": "",
        "src": {"app.py": ""},
        "tests": {"test_app.py": ""},  # Excluded dir
        "docs": {"conf.py": ""},  # Excluded dir
    }
    create_structure(tmp_path, structure)

    config = {"exclude_dirs": ["tests", "docs"]}
    paths_to_check = [tmp_path]
    result = find_files_to_audit(paths_to_check, recursive=True, config=config)

    expected = sorted([tmp_path / "main.py", tmp_path / "src" / "app.py"])
    assert result == expected


def test_find_files_deduplication_and_sort(tmp_path: Path):
    """Test that results are deduplicated and sorted."""
    structure = {
        "c.py": "",
        "a.py": "",
        "subdir": {
            "b.py": "",
            "a.py": "",  # Duplicate name in subdir
        },
    }
    create_structure(tmp_path, structure)

    config = {}
    # Provide paths multiple times and out of order
    paths_to_check = [
        tmp_path / "subdir",
        tmp_path / "c.py",
        tmp_path,
        tmp_path / "a.py",
        tmp_path / "subdir" / "a.py",
    ]
    result = find_files_to_audit(paths_to_check, recursive=True, config=config)

    expected = sorted(
        [
            tmp_path / "a.py",
            tmp_path / "subdir" / "a.py",  # Note: Path object itself is unique
            tmp_path / "subdir" / "b.py",
            tmp_path / "c.py",
        ]
    )
    assert result == expected
