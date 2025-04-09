# FILE: tests/test_git_utils.py
"""Tests for Git utility functions."""

import os
import subprocess
from pathlib import Path

import pytest

# Try importing the function, will fail until implemented
# from zeroth_law.git_utils import find_git_root


# Fixture to create a dummy Git repository structure
@pytest.fixture
def dummy_git_repo(tmp_path: Path) -> Path:
    git_root = tmp_path / "repo_root"
    project_a = git_root / "project_a"
    project_b = git_root / "project_b"
    project_a_src = project_a / "src"
    root_file = git_root / "README.md"

    project_a_src.mkdir(parents=True)
    project_b.mkdir()

    # Create dummy files
    (project_a / "pyproject.toml").touch()
    (project_a_src / "main.py").touch()
    (project_b / "config.txt").touch()
    root_file.touch()

    # Initialize Git repo
    try:
        subprocess.run(["git", "init"], cwd=git_root, check=True, capture_output=True)
        # Add files (needed for rev-parse potentially)
        subprocess.run(["git", "add", "."], cwd=git_root, check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        pytest.skip(f"Git command failed, skipping git tests: {e}")

    return git_root


# Add tests for find_git_root here once implemented
# e.g., test_find_git_root_from_subdir(dummy_git_repo)
# e.g., test_find_git_root_from_root(dummy_git_repo)
# e.g., test_find_git_root_outside_repo(tmp_path)

# --- Tests for get_staged_files ---


def test_get_staged_files_none_staged(dummy_git_repo):
    """Test getting staged files when none are staged (after initial commit)."""
    from zeroth_law.git_utils import get_staged_files

    # Files were added during fixture setup, commit them
    try:
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=dummy_git_repo, check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        pytest.skip(f"Git command failed, skipping git tests: {e}")

    staged = get_staged_files(dummy_git_repo)
    assert staged == []


def test_get_staged_files_some_staged(dummy_git_repo):
    """Test getting staged files when some are modified and added."""
    from zeroth_law.git_utils import get_staged_files

    # Modify and stage some files
    file_in_a = dummy_git_repo / "project_a" / "src" / "main.py"
    file_in_b = dummy_git_repo / "project_b" / "config.txt"
    root_readme = dummy_git_repo / "README.md"

    file_in_a.write_text("modified content a")
    file_in_b.write_text("modified content b")
    root_readme.write_text("modified readme")

    try:
        subprocess.run(
            ["git", "add", str(file_in_a), str(file_in_b), str(root_readme)], cwd=dummy_git_repo, check=True, capture_output=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        pytest.skip(f"Git command failed, skipping git tests: {e}")

    staged = get_staged_files(dummy_git_repo)
    # Expect relative paths
    expected_paths = {Path("project_a/src/main.py"), Path("project_b/config.txt"), Path("README.md")}
    assert set(staged) == expected_paths


# --- Tests for identify_project_roots_from_files ---


def test_identify_project_roots_single_project(dummy_git_repo):
    """Test identifying project root when files are only in one project."""
    from zeroth_law.git_utils import identify_project_roots_from_files

    # Need project_a config file for it to be identified
    (dummy_git_repo / "project_a" / ".pre-commit-config.yaml").touch()

    staged_files = [Path("project_a/pyproject.toml"), Path("project_a/src/main.py")]
    roots = identify_project_roots_from_files(staged_files, dummy_git_repo)
    assert roots == {Path("project_a")}


def test_identify_project_roots_multi_project(dummy_git_repo):
    """Test identifying multiple project roots."""
    from zeroth_law.git_utils import identify_project_roots_from_files

    # Need config files for projects to be identified
    (dummy_git_repo / "project_a" / ".pre-commit-config.yaml").touch()
    (dummy_git_repo / "project_b" / ".pre-commit-config.yaml").touch()

    staged_files = [Path("project_a/src/main.py"), Path("project_b/config.txt")]
    roots = identify_project_roots_from_files(staged_files, dummy_git_repo)
    assert roots == {Path("project_a"), Path("project_b")}


def test_identify_project_roots_root_files_only(dummy_git_repo):
    """Test identifying project root when only root files are staged."""
    from zeroth_law.git_utils import identify_project_roots_from_files

    (dummy_git_repo / "project_a" / ".pre-commit-config.yaml").touch()

    staged_files = [Path("README.md")]
    roots = identify_project_roots_from_files(staged_files, dummy_git_repo)
    assert roots == set()


def test_identify_project_roots_no_project_config(dummy_git_repo):
    """Test identifying when staged files are in a dir without a config."""
    from zeroth_law.git_utils import identify_project_roots_from_files

    # project_b has no .pre-commit-config.yaml in this test
    staged_files = [Path("project_b/config.txt")]
    roots = identify_project_roots_from_files(staged_files, dummy_git_repo)
    assert roots == set()


# --- Tests for Hook Script Generation ---


def test_generate_custom_hook_script_content():
    """Test the content of the generated hook script."""
    # Import within test to avoid errors if git_utils is partially complete
    try:
        from zeroth_law.git_utils import generate_custom_hook_script
    except ImportError:
        pytest.skip("generate_custom_hook_script not implemented yet")

    script = generate_custom_hook_script()

    # Basic checks for key commands and logic
    assert "#!/usr/bin/env bash" in script
    assert "[Zeroth Law Hook]" in script  # Check for branding/logging
    assert "git diff --cached --name-only --diff-filter=ACM" in script
    assert "git rev-parse --show-toplevel" in script
    assert "declare -A project_roots" in script  # Check for project detection logic
    assert ".pre-commit-config.yaml" in script  # Checks for project config file
    assert 'if [ "$num_projects" -gt 1 ]; then' in script  # Multi-project check
    assert 'echo "ERROR: Commit includes files from multiple projects."' in script
    assert "exit 1" in script  # Failure exit
    assert 'elif [ "$num_projects" -eq 1 ]; then' in script  # Single project check
    assert "pre-commit run --config" in script  # Running project-specific config
    assert "xargs -0 pre-commit run" in script  # Handling file lists safely
    assert "exit $?" in script  # Exiting with pre-commit's code
    assert "else" in script  # Handling root/no-project case
    assert 'echo "No project-specific changes detected. Passing."' in script
    assert "exit 0" in script  # Passing exit


# TODO: Add tests for hook installation/restoration (file writing, permissions)
