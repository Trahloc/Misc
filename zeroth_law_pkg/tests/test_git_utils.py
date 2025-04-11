# FILE: tests/test_git_utils.py
"""Tests for Git utility functions."""

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


# Tests for find_git_root
def test_find_git_root_from_subdir(dummy_git_repo):
    """Test finding Git root when called from a subdirectory."""
    from zeroth_law.git_utils import find_git_root

    # Test from subdirectory
    subdir = dummy_git_repo / "project_a" / "src"
    git_root = find_git_root(subdir)

    assert git_root == dummy_git_repo, f"Expected {dummy_git_repo}, got {git_root}"


def test_find_git_root_from_root(dummy_git_repo):
    """Test finding Git root when called from the root directory."""
    from zeroth_law.git_utils import find_git_root

    # Test from Git root directly
    git_root = find_git_root(dummy_git_repo)

    assert git_root == dummy_git_repo, f"Expected {dummy_git_repo}, got {git_root}"


def test_find_git_root_outside_repo(tmp_path):
    """Test finding Git root when called from outside a Git repository."""
    from zeroth_law.git_utils import find_git_root

    # Should raise an error when not in a Git repo
    with pytest.raises(ValueError, match="Not a Git repository"):
        find_git_root(tmp_path)


# --- Tests for get_staged_files ---


def test_get_staged_files_none_staged(dummy_git_repo):
    """Test getting staged files when none are staged (after initial commit)."""
    from zeroth_law.git_utils import get_staged_files

    # Files were added during fixture setup, commit them
    try:
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=dummy_git_repo,
            check=True,
            capture_output=True,
        )
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
    pyproject = dummy_git_repo / "project_a" / "pyproject.toml"

    file_in_a.write_text("modified content a")
    file_in_b.write_text("modified content b")
    root_readme.write_text("modified readme")
    pyproject.write_text('[tool.poetry]\nname = "test"')

    try:
        subprocess.run(
            [
                "git",
                "add",
                str(file_in_a),
                str(file_in_b),
                str(root_readme),
                str(pyproject),
            ],
            cwd=dummy_git_repo,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        pytest.skip(f"Git command failed, skipping git tests: {e}")

    staged = get_staged_files(dummy_git_repo)
    # Expect relative paths including pyproject.toml
    expected_paths = {
        Path("project_a/src/main.py"),
        Path("project_b/config.txt"),
        Path("README.md"),
        Path("project_a/pyproject.toml"),
    }
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
    assert 'echo "Error: Not a Git repository."' in script  # Check for error message
    assert "exit 1" in script  # Failure exit
    assert 'elif [ "$num_projects" -eq 1 ]; then' in script  # Single project check
    assert "pre-commit run --config" in script  # Running project-specific config
    assert "xargs -0 pre-commit run" in script  # Handling file lists safely
    assert "exit $?" in script  # Exiting with pre-commit's code
    assert "else" in script  # Handling root/no-project case
    assert "[Zeroth Law Hook] No project-specific changes detected. Passing." in script
    assert "exit 0" in script  # Passing exit


# TODO: Add tests for hook installation/restoration (file writing, permissions)


def test_install_hook_creates_file(dummy_git_repo, tmp_path):
    """Test that installing the hook creates the pre-commit file with correct permissions."""
    try:
        from zeroth_law.git_utils import install_git_hook_script
    except ImportError:
        pytest.skip("install_git_hook_script not implemented yet")

    # Create a mock .git/hooks directory
    hooks_dir = dummy_git_repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Install the hook
    hook_path = install_git_hook_script(dummy_git_repo)

    # Verify the hook file exists
    assert hook_path.exists(), f"Hook file {hook_path} was not created"

    # Verify it has executable permissions
    import stat

    permissions = hook_path.stat().st_mode
    assert permissions & stat.S_IXUSR, "Hook file is not executable for user"
    assert permissions & stat.S_IXGRP, "Hook file is not executable for group"

    # Verify file content
    hook_content = hook_path.read_text()
    assert "#!/usr/bin/env bash" in hook_content
    assert "[Zeroth Law Hook]" in hook_content


def test_install_hook_overwrites_existing(dummy_git_repo):
    """Test that installing the hook overwrites an existing pre-commit file."""
    try:
        from zeroth_law.git_utils import install_git_hook_script
    except ImportError:
        pytest.skip("install_git_hook_script not implemented yet")

    # Create a mock .git/hooks directory and a pre-existing hook
    hooks_dir = dummy_git_repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho 'Original hook'")

    # Save original modification time
    original_mtime = hook_path.stat().st_mtime

    # Wait a moment to ensure the modification time would be different
    import time

    time.sleep(0.1)

    # Install the hook (should overwrite)
    new_hook_path = install_git_hook_script(dummy_git_repo)

    # Verify the path is the same
    assert new_hook_path == hook_path

    # Verify the file has been modified
    assert hook_path.stat().st_mtime > original_mtime

    # Verify content has changed
    new_content = hook_path.read_text()
    assert "Original hook" not in new_content
    assert "[Zeroth Law Hook]" in new_content


def test_restore_hook_calls_precommit(mocker, dummy_git_repo):
    """Test that restoring hooks calls pre-commit install."""
    try:
        from zeroth_law.git_utils import restore_git_hooks
    except ImportError:
        pytest.skip("restore_git_hooks not implemented yet")

    # Mock subprocess.run to avoid actually calling pre-commit
    mock_run = mocker.patch(
        "subprocess.run",
        return_value=mocker.Mock(stdout="pre-commit installed", returncode=0),
    )

    # Call restore function
    restore_git_hooks(dummy_git_repo)

    # Verify subprocess.run was called with correct args
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args

    # Check that the command includes pre-commit install
    assert args[0][0] == "pre-commit"
    assert args[0][1] == "install"

    # Check it was called with the right working directory
    assert kwargs["cwd"] == dummy_git_repo
