# File: tests/test_path_utils.py
"""Tests for path utility functions."""

from pathlib import Path
import sys
import pytest
import os
from unittest.mock import patch, MagicMock

# Assumes tests are run from the git root (Misc/)
# Need to access the actual project root (Misc/zeroth_law/)
# and a directory outside it.

# Determine paths relative to this test file
test_file_path = Path(__file__).resolve()
git_root = test_file_path.parent.parent  # Assumes tests/test_path_utils.py
project_root = git_root / "zeroth_law"
src_root = project_root / "src"
outside_dir = git_root.parent  # Directory containing Misc/

# Add parent directory to sys.path to allow import of config_loader
# This assumes tests are run from the project root or configured with PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
# from zeroth_law.path_utils import find_project_root  # noqa: E402
from zeroth_law.common.path_utils import find_project_root, ZLFProjectRootNotFoundError
from zeroth_law.common.git_utils import find_git_root
from zeroth_law.lib.tool_path_utils import command_sequence_to_filepath, command_sequence_to_id


def test_find_project_root_from_within_project(tmp_path):
    """Test finding the root when starting inside the project structure."""
    # Simulate project structure within tmp_path
    fake_project_root = tmp_path / "project"
    fake_src = fake_project_root / "src"
    fake_tests = fake_project_root / "tests"  # Define tests path
    fake_subdir = fake_src / "subdir"
    fake_subdir.mkdir(parents=True)
    fake_tests.mkdir()  # Create tests dir
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
    # Create required structure for find_project_root
    (fake_project_root / "src").mkdir(parents=True)
    (fake_project_root / "tests").mkdir()
    (fake_project_root / "pyproject.toml").touch()

    # We expect it NOT to find the project root when starting outside
    with pytest.raises(ZLFProjectRootNotFoundError):
        find_project_root(fake_container)

    # Test starting from a sibling directory - should also NOT find the root
    fake_sibling = tmp_path / "sibling"
    fake_sibling.mkdir()
    with pytest.raises(ZLFProjectRootNotFoundError):
        find_project_root(fake_sibling)


def test_find_project_root_no_toml(tmp_path):
    """Test that ZLFProjectRootNotFoundError is raised if no pyproject.toml is found."""
    fake_dir = tmp_path / "no_project"
    fake_subdir = fake_dir / "subdir"
    fake_subdir.mkdir(parents=True)
    (fake_dir / "src").mkdir()  # Add src/tests
    (fake_dir / "tests").mkdir()

    with pytest.raises(ZLFProjectRootNotFoundError):
        find_project_root(fake_subdir)
    with pytest.raises(ZLFProjectRootNotFoundError):
        find_project_root(fake_dir)


# We might need a test that more accurately reflects the pre-commit scenario
# where CWD is Git Root, but we might analyze a file deeper inside the project root.


def test_find_project_root_from_simulated_git_root():
    """Test finding the root using the actual project structure."""
    # Find the *actual* project root based on the test file's location
    # Assuming find_project_root works correctly on the actual structure
    expected_project_root = find_project_root(Path(__file__).parent)

    # Start search from a file within the project
    some_src_file_path = expected_project_root / "src" / "zeroth_law" / "cli.py"
    assert some_src_file_path.exists(), f"Test setup error: {some_src_file_path} does not exist."

    # Assert that find_project_root finds the calculated expected root
    assert find_project_root(some_src_file_path.parent) == expected_project_root


def test_find_project_root_from_non_git_dir(tmp_path):
    """Test finding the project root from outside a known project structure raises error."""
    # Simulate being in a directory containing the project
    fake_container = tmp_path / "container"
    fake_project_root = fake_container / "project"
    # Create required structure for find_project_root
    (fake_project_root / "src").mkdir(parents=True)
    (fake_project_root / "tests").mkdir()
    (fake_project_root / "pyproject.toml").touch()

    # We expect it NOT to find the project root when starting outside
    with pytest.raises(ZLFProjectRootNotFoundError):
        find_project_root(fake_container)

    # Test starting from a sibling directory - should also NOT find the root
    fake_sibling = tmp_path / "sibling"
    fake_sibling.mkdir()
    with pytest.raises(ZLFProjectRootNotFoundError):
        find_project_root(fake_sibling)


@pytest.fixture
def tmp_path(tmp_path):
    # Add any additional setup for the test if needed
    return tmp_path
