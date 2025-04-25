# FILE: tests/test_git_utils.py
"""Tests for Git utility functions."""

import subprocess
from pathlib import Path
import sys

import pytest

# Try importing the function, will fail until implemented
# from zeroth_law.git_utils import find_git_root

# from zeroth_law.git_utils import (
from zeroth_law.common.git_utils import (
    find_git_root,
    get_staged_files,
    identify_project_roots_from_files,
    generate_custom_hook_script,
    install_git_hook_script,
    restore_git_hooks,
    _run_git_command,
)

# Add project root to path for potential utility imports if needed
# sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


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
@pytest.mark.usefixtures("setup_git_repo")
def test_find_git_root_from_subdir(tmp_path):
    """Test finding the git root from a subdirectory."""
    subdir = tmp_path / "project" / "subdir"
    subdir.mkdir(parents=True)
    # from zeroth_law.git_utils import find_git_root
    from zeroth_law.common.git_utils import find_git_root

    found_root = find_git_root(subdir)
    assert found_root == tmp_path / "project"


@pytest.mark.usefixtures("setup_git_repo")
def test_find_git_root_from_root(tmp_path):
    """Test finding the git root from the root directory itself."""
    # from zeroth_law.git_utils import find_git_root
    from zeroth_law.common.git_utils import find_git_root

    found_root = find_git_root(tmp_path / "project")
    assert found_root == tmp_path / "project"


@pytest.mark.usefixtures("setup_git_repo")
def test_find_git_root_outside_repo(tmp_path):
    """Test finding the git root returns None when called from outside."""
    # from zeroth_law.git_utils import find_git_root
    from zeroth_law.common.git_utils import find_git_root

    found_root = find_git_root(tmp_path)
    assert found_root is None


# --- Tests for get_staged_files ---


@pytest.mark.usefixtures("setup_git_repo")
def test_get_staged_files_none_staged(tmp_path):
    """Test getting staged files when none are staged."""
    # from zeroth_law.git_utils import get_staged_files
    from zeroth_law.common.git_utils import get_staged_files

    git_root = tmp_path / "project"
    staged_files = get_staged_files(git_root)
    assert staged_files == []


@pytest.mark.usefixtures("setup_git_repo")
def test_get_staged_files_some_staged(tmp_path):
    """Test getting staged files when some files are staged."""
    git_root = tmp_path / "project"
    file1 = git_root / "file1.txt"
    file1.touch()
    subdir = git_root / "subdir"
    subdir.mkdir()
    file2 = subdir / "file2.py"
    file2.touch()

    # Stage files
    _run_git_command(["add", "file1.txt", "subdir/file2.py"], git_root)

    # from zeroth_law.git_utils import get_staged_files
    from zeroth_law.common.git_utils import get_staged_files

    staged_files = get_staged_files(git_root)

    # Assert paths are relative to git_root
    expected_paths = {
        Path("file1.txt"),
        Path("subdir/file2.py"),
    }
    assert set(staged_files) == expected_paths


# --- Tests for identify_project_roots_from_files ---


@pytest.mark.usefixtures("setup_git_repo")
def test_identify_project_roots_single_project(tmp_path):
    """Test identifying project root when staged files are in one project."""
    git_root = tmp_path / "project"
    proj1_root = git_root / "proj1"
    proj1_root.mkdir()
    (proj1_root / ".pre-commit-config.yaml").touch()
    file1 = proj1_root / "file1.txt"
    file1.touch()
    _run_git_command(["add", "proj1/file1.txt"], git_root)
    staged_files = ["proj1/file1.txt"]
    # from zeroth_law.git_utils import identify_project_roots_from_files
    from zeroth_law.common.git_utils import identify_project_roots_from_files

    roots = identify_project_roots_from_files(staged_files, git_root)
    assert roots == {proj1_root}


@pytest.mark.usefixtures("setup_git_repo")
def test_identify_project_roots_multiple_files_single_project(tmp_path):
    """Test identifying project root with multiple files in one project."""
    git_root = tmp_path / "project"
    proj1_root = git_root / "proj1"
    proj1_root.mkdir()
    (proj1_root / ".pre-commit-config.yaml").touch()
    file1 = proj1_root / "file1.txt"
    file1.touch()
    file2 = proj1_root / "subdir" / "file2.py"
    file2.parent.mkdir()
    file2.touch()
    _run_git_command(["add", "proj1/file1.txt", "proj1/subdir/file2.py"], git_root)
    staged_files = ["proj1/file1.txt", "proj1/subdir/file2.py"]
    # from zeroth_law.git_utils import identify_project_roots_from_files
    from zeroth_law.common.git_utils import identify_project_roots_from_files

    roots = identify_project_roots_from_files(staged_files, git_root)
    assert roots == {proj1_root}


@pytest.mark.usefixtures("setup_git_repo")
def test_identify_project_roots_multiple_projects(tmp_path):
    """Test identifying multiple project roots."""
    git_root = tmp_path / "project"
    proj1_root = git_root / "proj1"
    proj1_root.mkdir()
    (proj1_root / ".pre-commit-config.yaml").touch()
    file1 = proj1_root / "file1.txt"
    file1.touch()

    proj2_root = git_root / "proj2"
    proj2_root.mkdir()
    (proj2_root / ".pre-commit-config.yaml").touch()
    file2 = proj2_root / "file2.py"
    file2.touch()

    _run_git_command(["add", "proj1/file1.txt", "proj2/file2.py"], git_root)
    staged_files = ["proj1/file1.txt", "proj2/file2.py"]
    # from zeroth_law.git_utils import identify_project_roots_from_files
    from zeroth_law.common.git_utils import identify_project_roots_from_files

    roots = identify_project_roots_from_files(staged_files, git_root)
    assert roots == {proj1_root, proj2_root}


@pytest.mark.usefixtures("setup_git_repo")
def test_identify_project_roots_no_config(tmp_path):
    """Test identifying projects when no .pre-commit-config.yaml is present."""
    git_root = tmp_path / "project"
    proj1_root = git_root / "proj1"
    proj1_root.mkdir()
    # NO .pre-commit-config.yaml
    file1 = proj1_root / "file1.txt"
    file1.touch()
    _run_git_command(["add", "proj1/file1.txt"], git_root)
    staged_files = ["proj1/file1.txt"]
    # from zeroth_law.git_utils import identify_project_roots_from_files
    from zeroth_law.common.git_utils import identify_project_roots_from_files

    roots = identify_project_roots_from_files(staged_files, git_root)
    assert roots == set()


# --- Tests for Hook Script Generation ---


def test_generate_custom_hook_script():
    """Test the content of the generated hook script."""
    # from zeroth_law.git_utils import generate_custom_hook_script
    from zeroth_law.common.git_utils import generate_custom_hook_script

    script_content = generate_custom_hook_script()
    assert "#!/usr/bin/env bash" in script_content
    assert "set -eo pipefail" in script_content
    assert "git diff --name-only --cached --diff-filter=ACMRTUXB" in script_content
    assert "pre-commit run --config" in script_content
    assert "unique_project_roots=()" in script_content
    assert "Multiple projects detected in commit" in script_content  # Check error message


# TODO: Add tests for hook installation/restoration (file writing, permissions)


@pytest.mark.usefixtures("setup_git_repo")
def test_install_git_hook_script(tmp_path):
    """Test installing the hook script."""
    git_root = tmp_path / "project"
    hooks_dir = git_root / ".git" / "hooks"
    hook_file = hooks_dir / "pre-commit"

    # from zeroth_law.git_utils import install_git_hook_script
    from zeroth_law.common.git_utils import install_git_hook_script

    install_git_hook_script(git_root)

    assert hook_file.is_file()
    assert os.access(hook_file, os.X_OK)  # Check executable permission
    content = hook_file.read_text()
    assert "pre-commit run --config" in content  # Basic content check


@pytest.mark.usefixtures("setup_git_repo")
def test_install_git_hook_script_already_exists(tmp_path):
    """Test installing the hook script when one already exists (should overwrite)."""
    git_root = tmp_path / "project"
    hooks_dir = git_root / ".git" / "hooks"
    hook_file = hooks_dir / "pre-commit"

    # Create dummy existing hook
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file.write_text("#!/bin/sh\necho 'Old hook'\nexit 1")
    hook_file.chmod(0o755)

    # from zeroth_law.git_utils import install_git_hook_script
    from zeroth_law.common.git_utils import install_git_hook_script

    install_git_hook_script(git_root)

    assert hook_file.is_file()
    assert os.access(hook_file, os.X_OK)
    content = hook_file.read_text()
    assert "Old hook" not in content  # Should be overwritten
    assert "pre-commit run --config" in content


@pytest.mark.usefixtures("setup_git_repo")
def test_restore_git_hooks(tmp_path):
    """Test restoring hooks using pre-commit install."""
    git_root = tmp_path / "project"
    hooks_dir = git_root / ".git" / "hooks"
    hook_file = hooks_dir / "pre-commit"

    # Install our custom hook first
    install_git_hook_script(git_root)
    custom_content = hook_file.read_text()

    # Create a minimal .pre-commit-config.yaml for pre-commit to install something
    (git_root / ".pre-commit-config.yaml").write_text(
        "repos:\n- repo: local\n  hooks:\n  - id: dummy\n    name: Dummy\n    entry: echo 'Dummy hook'\n    language: system"
    )

    # Restore hooks
    # from zeroth_law.git_utils import restore_git_hooks
    from zeroth_law.common.git_utils import restore_git_hooks

    restore_git_hooks(git_root)

    assert hook_file.is_file()
    restored_content = hook_file.read_text()
    assert restored_content != custom_content  # Content should change
    assert "Generated by pre-commit" in restored_content  # Check for pre-commit marker
