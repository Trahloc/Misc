"""Tests for path utility functions."""

import os
from pathlib import Path

import pytest

# Assumes tests are run from the git root (Misc/)
# Need to access the actual project root (Misc/zeroth_law/)
# and a directory outside it.

# Determine paths relative to this test file
test_file_path = Path(__file__).resolve()
git_root = test_file_path.parent.parent  # Assumes tests/test_path_utils.py
project_root = git_root / "zeroth_law"
src_root = project_root / "src"
outside_dir = git_root.parent  # Directory containing Misc/

# Add src to path if necessary (though maybe not needed if testing utils directly)
# import sys
# sys.path.insert(0, str(src_root))

from zeroth_law.path_utils import find_project_root


def test_find_project_root_from_within_project(tmp_path):
    """Test finding the root when starting inside the project structure."""
    # Simulate project structure within tmp_path
    fake_project_root = tmp_path / "project"
    fake_src = fake_project_root / "src"
    fake_subdir = fake_src / "subdir"
    fake_subdir.mkdir(parents=True)
    (fake_project_root / "pyproject.toml").touch()

    # Test starting from various points inside
    assert find_project_root(fake_subdir) == fake_project_root
    assert find_project_root(fake_src) == fake_project_root
    assert find_project_root(fake_project_root) == fake_project_root


def test_find_project_root_from_outside_project(tmp_path):
    """Test finding the root when starting outside the project structure."""
    # Simulate being in a directory containing the project
    fake_container = tmp_path / "container"
    fake_project_root = fake_container / "project"
    fake_project_root.mkdir(parents=True)
    (fake_project_root / "pyproject.toml").touch()

    # This scenario mimics the pre-commit run: start search from container
    # We expect it NOT to find the project root because it's inside container,
    # unless the function is called on a path *within* the project.
    # Let's clarify the function's purpose: it finds the root containing start_path or its ancestors.
    # So starting outside won't find it unless start_path IS the root.

    # Test starting from the container dir - should NOT find the root *inside*
    assert find_project_root(fake_container) is None

    # Test starting from a sibling directory - should NOT find the root
    fake_sibling = tmp_path / "sibling"
    fake_sibling.mkdir()
    assert find_project_root(fake_sibling) is None


def test_find_project_root_no_toml(tmp_path):
    """Test that None is returned if no pyproject.toml is found."""
    fake_dir = tmp_path / "no_project"
    fake_subdir = fake_dir / "subdir"
    fake_subdir.mkdir(parents=True)

    assert find_project_root(fake_subdir) is None
    assert find_project_root(fake_dir) is None


# We might need a test that more accurately reflects the pre-commit scenario
# where CWD is Git Root, but we might analyze a file deeper inside the project root.


def test_find_project_root_from_simulated_git_root():
    """Test finding the root using the actual project structure."""
    # Assuming tests run from Git Root (Misc/)
    actual_project_root = project_root.resolve()

    # Start search from a file within the project
    some_src_file_path = src_root / "zeroth_law" / "cli.py"
    assert find_project_root(some_src_file_path.parent) == actual_project_root

    # Start search from the src directory
    assert find_project_root(src_root) == actual_project_root

    # Start search from the project root itself
    assert find_project_root(project_root) == actual_project_root

    # Start search from the Git root (which doesn't contain pyproject.toml)
    assert find_project_root(git_root) is None
