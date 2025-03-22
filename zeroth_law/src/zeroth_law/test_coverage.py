"""
# PURPOSE: Verify and enforce test coverage for Python files following the Zeroth Law.

## INTERFACES:
 - verify_test_coverage(project_path: str, create_stubs: bool = False) -> dict: Verifies test coverage and optionally creates test stubs
 - create_test_stub(source_file: str, test_file: str) -> None: Creates a test stub for a source file
 - get_project_name(project_path: str) -> str: Gets project name from pyproject.toml

## DEPENDENCIES:
 - os
 - logging
 - zeroth_law.exceptions
 - re
 - tomli (for Python < 3.11) or tomllib (for Python >= 3.11)
"""
import os
import logging
import re
import sys
from typing import Dict, List, Set, Tuple, Optional

from zeroth_law.exceptions import ZerothLawError

# Use tomllib (Python 3.11+) or tomli (Python < 3.11)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)

class CoverageError(ZerothLawError):
    """Error raised when test coverage verification fails."""

def _is_python_file(file_path: str) -> bool:
    """Check if a file is a Python source file."""
    return file_path.endswith(".py") and not file_path.endswith(".pyc")

def _find_python_files(directory: str, ignore_patterns: List[str] = None) -> Set[str]:
    """
    Find all Python files in a directory recursively.

    Args:
        directory: Directory to search
        ignore_patterns: List of regex patterns to ignore

    Returns:
        Set of Python file paths
    """
    if ignore_patterns is None:
        # Default patterns to ignore
        ignore_patterns = [
            r'__pycache__',
            r'\.git',
            r'\.venv',
            r'\.env',
            r'\.old',
            r'\.egg-info',
            r'build',
            r'dist',
            r'\.pytest_cache',
            r'cookiecutter-template',  # Ignore cookiecutter template files
            r'{{.*}}',  # Ignore files with Jinja2 template syntax
        ]

    compiled_patterns = [re.compile(pattern) for pattern in ignore_patterns]

    python_files = set()
    for root, dirs, files in os.walk(directory):
        # Skip directories that match ignore patterns
        dirs[:] = [d for d in dirs if not any(pattern.search(d) for pattern in compiled_patterns)]

        for file in files:
            if _is_python_file(file):
                file_path = os.path.join(root, file)
                if not any(pattern.search(file_path) for pattern in compiled_patterns):
                    python_files.add(file_path)

    return python_files

def get_project_name(project_path: str) -> str:
    """
    Get the project name from pyproject.toml if available.

    Args:
        project_path: Path to the project root

    Returns:
        Project name or directory name if not found in pyproject.toml
    """
    # Try to read pyproject.toml
    pyproject_path = os.path.join(project_path, "pyproject.toml")

    if os.path.exists(pyproject_path) and tomllib is not None:
        try:
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)
                project_name = pyproject_data.get("project", {}).get("name", "")
                if project_name:
                    logger.debug("Found project name in pyproject.toml: %s", project_name)
                    return project_name
        except Exception as e:
            logger.warning("Error reading pyproject.toml: %s", str(e))

    # Fall back to directory name
    dir_name = os.path.basename(project_path)
    logger.debug("Using directory name as project name: %s", dir_name)
    return dir_name

def _get_test_path(source_file: str, project_root: str) -> str:
    """
    Determine the expected test file path for a source file.

    Args:
        source_file: Path to the source file
        project_root: Path to the project root

    Returns:
        Expected path to the test file
    """
    # Get relative path from project root
    rel_path = os.path.relpath(source_file, project_root)

    # Transform source path to test path
    if 'src' in rel_path.split(os.path.sep):
        # Handle src directory structure
        parts = rel_path.split(os.path.sep)
        src_index = parts.index('src')
        module_path = os.path.sep.join(parts[src_index+1:])
        filename = os.path.basename(module_path)
        dirname = os.path.dirname(module_path)

        # Create test file path
        test_filename = f"test_{filename}"
        if dirname:
            test_path = os.path.join(project_root, 'tests', dirname, test_filename)
        else:
            test_path = os.path.join(project_root, 'tests', test_filename)
    else:
        # Simple case - just put test file in tests directory with test_ prefix
        filename = os.path.basename(rel_path)
        test_path = os.path.join(project_root, 'tests', f"test_{filename}")

    return test_path

def _get_source_dirs(project_path: str) -> List[str]:
    """
    Find source directories in the project.

    Args:
        project_path: Path to the project root

    Returns:
        List of source directories
    """
    src_dirs = []
    project_name = get_project_name(project_path)

    # Check for src/project_name structure
    src_package_path = os.path.join(project_path, "src", project_name)
    if os.path.isdir(src_package_path):
        logger.debug("Found src/%s structure", project_name)
        src_dirs.append(src_package_path)

    # Check for direct project_name structure
    direct_package_path = os.path.join(project_path, project_name)
    if os.path.isdir(direct_package_path):
        logger.debug("Found direct %s package structure", project_name)
        src_dirs.append(direct_package_path)

    # If neither of the above structures were found, look for src directory
    if not src_dirs:
        src_path = os.path.join(project_path, "src")
        if os.path.isdir(src_path):
            logger.debug("Found generic src directory structure")
            src_dirs.append(src_path)

    # If still no source dirs found, use the project root as fallback
    if not src_dirs:
        logger.debug("No specific package structure found, using project root")
        src_dirs.append(project_path)

    return src_dirs

def create_test_stub(source_file: str, test_file: str) -> None:
    """
    Create a test stub file for a given source file.

    Args:
        source_file: Path to the source file
        test_file: Path to create the test file

    Raises:
        FileExistsError: If the test file already exists
    """
    if os.path.exists(test_file):
        raise FileExistsError(f"Test file already exists: {test_file}")

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(test_file), exist_ok=True)

    # Get module name and function name for imports
    module_name = os.path.basename(source_file).replace('.py', '')
    if 'src' in source_file.split(os.path.sep):
        # Extract the full module path
        parts = source_file.split(os.path.sep)
        src_index = parts.index('src')
        module_parts = parts[src_index+1:-1]  # Get parts between src and filename
        if module_parts:
            full_module = '.'.join(module_parts + [module_name])
        else:
            full_module = module_name
    else:
        full_module = module_name

    # Create test stub content
    content = f'''"""
# PURPOSE: Tests for {full_module}.

## INTERFACES:
 - All test functions

## DEPENDENCIES:
 - pytest
 - {full_module}
"""
import pytest

# Import the module to test
from {full_module} import *

def test_{module_name}_exists():
    """
    ZEROTH LAW VIOLATION: This is a placeholder test.

    This file was auto-generated by the Zeroth Law test coverage tool.
    Replace this with actual tests for the {module_name} module.

    According to Zeroth Law section 6.1:
    - Test Coverage: >90% business logic coverage
    - Each feature should have a corresponding pytest for testing
    """
    # TODO: Replace with actual tests
    assert True, "Replace this with actual tests for the {module_name} module"
'''

    # Write the test stub file
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info("Created test stub: %s", test_file)

def verify_test_coverage(project_path: str, create_stubs: bool = False) -> Dict:
    """
    Verify test coverage for a project and optionally create test stubs.

    Args:
        project_path: Path to the project root
        create_stubs: Whether to create test stubs for missing tests

    Returns:
        Dictionary with coverage metrics:
            total_source_files: Number of source files
            total_test_files: Number of test files
            missing_tests: List of source files without tests
            orphaned_tests: List of test files without source files
            coverage_percentage: Percentage of source files with tests
            project_name: Name of the project
            structure_type: Type of project structure detected

    Raises:
        CoverageError: If test coverage verification fails
    """
    project_path = os.path.abspath(project_path)
    logger.debug("Verifying test coverage for %s", project_path)

    # Get project name from pyproject.toml or directory name
    project_name = get_project_name(project_path)

    # Find source files
    src_dirs = _get_source_dirs(project_path)

    # Determine structure type
    structure_type = "unknown"
    if any("src" in d and project_name in d for d in src_dirs):
        structure_type = f"src/{project_name}"
    elif any(project_name in d and "src" not in d for d in src_dirs):
        structure_type = project_name
    elif any("src" in d for d in src_dirs):
        structure_type = "src"
    else:
        structure_type = "flat"

    # Collect all Python files
    source_files = set()
    for src_dir in src_dirs:
        source_files.update(_find_python_files(src_dir))

    # Find test files
    tests_dir = os.path.join(project_path, 'tests')
    if os.path.exists(tests_dir):
        test_files = _find_python_files(tests_dir)
    else:
        test_files = set()
        if create_stubs:
            # Create tests directory if it doesn't exist
            os.makedirs(tests_dir, exist_ok=True)

    # Check test coverage
    missing_tests = []
    found_tests = set()  # Track which test files correspond to source files

    for source_file in source_files:
        # Skip __init__.py files and test files
        if os.path.basename(source_file) == '__init__.py' or source_file in test_files:
            continue

        # Get expected test file path
        test_file = _get_test_path(source_file, project_path)

        # Check if test file exists
        if os.path.exists(test_file):
            found_tests.add(test_file)
        else:
            missing_tests.append((source_file, test_file))

    # Find orphaned tests (test files without corresponding source files)
    orphaned_tests = []
    for test_file in test_files:
        if test_file not in found_tests and os.path.basename(test_file) != '__init__.py':
            # Get the expected source file path
            source_module = test_file.replace(tests_dir, '').lstrip(os.path.sep)
            if source_module.startswith('test_'):
                source_module = source_module[5:]  # Remove 'test_' prefix
            for src_dir in src_dirs:
                potential_source = os.path.join(src_dir, source_module)
                if not os.path.exists(potential_source):
                    rel_path = os.path.relpath(test_file, project_path)
                    orphaned_tests.append(rel_path)

    # Create test stubs if requested
    if create_stubs and missing_tests:
        logger.info("Creating test stubs for %d files", len(missing_tests))
        for source_file, test_file in missing_tests:
            try:
                create_test_stub(source_file, test_file)
            except (OSError, FileExistsError) as e:
                logger.error("Failed to create test stub for %s: %s", source_file, e)

    # Compile metrics
    metrics = {
        'total_source_files': len(source_files),
        'total_test_files': len(test_files),
        'missing_tests': [os.path.relpath(source, project_path) for source, _ in missing_tests],
        'orphaned_tests': orphaned_tests,
        'coverage_percentage': (len(source_files) - len(missing_tests)) / len(source_files) * 100 if source_files else 0,
        'project_name': project_name,
        'structure_type': structure_type
    }

    logger.debug("Test coverage metrics: %s", metrics)
    return metrics

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added orphaned test detection
- Fixed logging format
- Improved error handling
- Added file encoding

## FUTURE TODOs:
 - Add support for customizing test file naming pattern
 - Add integration with pre-commit hooks
 - Add support for ignoring specific files or directories
"""