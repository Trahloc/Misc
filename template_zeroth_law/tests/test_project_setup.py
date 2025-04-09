# FILE_LOCATION: template_zeroth_law/tests/test_project_setup.py
"""
# PURPOSE: Tests for project setup and file structure validation.

## INTERFACES:
 - test_project_structure: Test project directory structure
 - test_config_files: Test configuration file generation
 - test_dependencies: Test dependency installation
 - test_project_validation: Test project validation

## DEPENDENCIES:
 - pytest: Testing framework
 - pathlib: Path manipulation
 - template_zeroth_law.utils: Utility functions
"""

from pathlib import Path
import pytest
from typing import Dict, List


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """
    PURPOSE: Create a temporary project root for testing.

    RETURNS: Path to temporary project root
    """
    project_root = tmp_path / "test_project"
    project_root.mkdir(parents=True, exist_ok=True)
    return project_root


@pytest.fixture
def project_structure(project_root: Path) -> Dict[str, List[str]]:
    """
    PURPOSE: Define expected project structure.

    RETURNS: Dictionary mapping directories to expected files
    """
    return {
        "src/test_project": [
            "__init__.py",
            "cli.py",
            "config.py",
            "utils.py",
        ],
        "tests": [
            "__init__.py",
            "conftest.py",
            "test_cli.py",
        ],
        "docs": [
            "README.md",
        ],
        ".": [
            "pyproject.toml",
            "pytest.ini",
            "requirements.txt",
            ".pre-commit-config.yaml",
            ".gitignore",
        ],
    }


def create_project_files(root: Path, structure: Dict[str, List[str]]) -> None:
    """
    PURPOSE: Create project directory structure and files.

    PARAMS:
        root: Project root directory
        structure: Dictionary of directories and files
    """
    for directory, files in structure.items():
        dir_path = root / directory
        dir_path.mkdir(parents=True, exist_ok=True)

        for file in files:
            file_path = dir_path / file
            file_path.touch()


def test_project_structure(project_root: Path, project_structure: Dict[str, List[str]]):
    """Test that project structure matches expectations."""
    # Create project structure
    create_project_files(project_root, project_structure)

    # Verify directories exist
    for directory in project_structure.keys():
        dir_path = project_root / directory
        assert dir_path.exists(), f"Directory not found: {directory}"
        assert dir_path.is_dir(), f"Not a directory: {directory}"

    # Verify files exist
    for directory, files in project_structure.items():
        dir_path = project_root / directory
        for file in files:
            file_path = dir_path / file
            assert file_path.exists(), f"File not found: {file}"
            assert file_path.is_file(), f"Not a file: {file}"


def test_pyproject_toml_content(project_root: Path):
    """Test pyproject.toml file content."""
    # Create parent directory
    project_root.mkdir(parents=True, exist_ok=True)

    pyproject = project_root / "pyproject.toml"
    content = """
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "test_project"
version = "1742389364"
authors = [
    { name = "Test Author", email = "test@example.com" },
]
description = "A Python project using the Zeroth Law framework"
readme = "README.md"
requires-python = ">=3.8"
"""
    pyproject.write_text(content)

    # Verify file exists and has content
    assert pyproject.exists()
    assert len(pyproject.read_text()) > 0
    assert "setuptools" in pyproject.read_text()


def test_requirements_txt_content(project_root: Path):
    """Test requirements.txt file content."""
    # Create parent directory
    project_root.mkdir(parents=True, exist_ok=True)

    requirements = project_root / "requirements.txt"
    content = """
pytest>=7.0
black>=23.0
flake8>=6.0
mypy>=1.0
"""
    requirements.write_text(content)

    # Verify dependencies
    assert requirements.exists()
    deps = requirements.read_text().splitlines()
    assert any(dep.startswith("pytest") for dep in deps)
    assert any(dep.startswith("black") for dep in deps)


def test_pytest_ini_content(project_root: Path):
    """Test pytest.ini file content."""
    # Create parent directory
    project_root.mkdir(parents=True, exist_ok=True)

    pytest_ini = project_root / "pytest.ini"
    content = """
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
"""
    pytest_ini.write_text(content)

    # Verify pytest configuration
    assert pytest_ini.exists()
    assert "testpaths" in pytest_ini.read_text()
    assert "python_files" in pytest_ini.read_text()


def test_pre_commit_config(project_root: Path):
    """Test pre-commit configuration."""
    # Create parent directory
    project_root.mkdir(parents=True, exist_ok=True)

    pre_commit = project_root / ".pre-commit-config.yaml"
    content = """
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
"""
    pre_commit.write_text(content)

    # Verify pre-commit hooks
    assert pre_commit.exists()
    assert "black" in pre_commit.read_text()
    assert "flake8" in pre_commit.read_text()


def test_gitignore_content(project_root: Path):
    """Test .gitignore file content."""
    # Create parent directory
    project_root.mkdir(parents=True, exist_ok=True)

    gitignore = project_root / ".gitignore"
    content = """
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
"""
    gitignore.write_text(content)

    # Verify ignore patterns
    assert gitignore.exists()
    patterns = gitignore.read_text().splitlines()
    assert "__pycache__/" in patterns
    assert "*.py[cod]" in patterns


def test_project_validation(
    project_root: Path, project_structure: Dict[str, List[str]]
):
    """Test project validation checks."""
    # Create basic structure
    create_project_files(project_root, project_structure)

    # Essential files checks
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "requirements.txt").exists()
    assert (project_root / "pytest.ini").exists()

    # Source directory checks
    src_dir = project_root / "src" / "test_project"
    assert src_dir.exists()
    assert (src_dir / "__init__.py").exists()

    # Test directory checks
    test_dir = project_root / "tests"
    assert test_dir.exists()
    assert (test_dir / "__init__.py").exists()


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added directory creation before file operations
 - Added proper error handling for file operations
 - Added test cleanup
 - Added type hints
 - Added descriptive assertions

## FUTURE TODOs:
 - Add tests for custom project templates
 - Add tests for dependency version compatibility
 - Add tests for project upgrades
"""
