"""
# PURPOSE: Implements test coverage commands and test stub generation

## INTERFACES:
 - command_test_coverage(): Displays test coverage report
 - command_create_test_stubs(): Creates test stubs for source files without tests
 - get_project_name(): Gets project name from pyproject.toml or directory name
 - find_source_and_test_files(): Finds source and test files in the project
 - calculate_coverage(): Calculates test coverage metrics
 - display_coverage_report(): Displays test coverage report
 - create_test_stubs(): Creates test stub files for missing tests

## DEPENDENCIES:
 - click: Command-line interface creation
 - pathlib: Path manipulation
 - os: Operating system interface
 - tomllib/tomli: TOML parsing (for reading pyproject.toml)
"""

import os
import click
from pathlib import Path
from typing import Dict, List, Tuple, Set
import sys

from template_zeroth_law.utils import get_project_root

# Import tomllib or tomli for TOML parsing
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


@click.command(name="test-coverage")
@click.pass_context
def command_test_coverage(ctx: click.Context):
    """
    Display test coverage for the project.

    Shows a report of source files and their corresponding test files.
    """
    logger = ctx.obj["logger"]
    logger.info("Checking test coverage")

    # Get project info
    project_root = get_project_root()
    project_name = get_project_name(project_root)

    # Find all source and test files
    source_files, test_files = find_source_and_test_files(project_root, project_name)

    # Calculate coverage
    coverage_info = calculate_coverage(source_files, test_files, project_name)

    # Display the report
    display_coverage_report(coverage_info, project_root)


@click.command(name="create-test-stubs")
@click.pass_context
def command_create_test_stubs(ctx: click.Context):
    """
    Create test stub files for source files that don't have corresponding tests.

    First checks test coverage and then creates test stubs for missing tests.
    """
    logger = ctx.obj["logger"]
    logger.info("Creating test stubs")

    # Get project info
    project_root = get_project_root()
    project_name = get_project_name(project_root)

    # Find all source and test files
    source_files, test_files = find_source_and_test_files(project_root, project_name)

    # Calculate coverage
    coverage_info = calculate_coverage(source_files, test_files, project_name)

    # Display the report
    display_coverage_report(coverage_info, project_root)

    # Create test stubs for source files without tests
    create_test_stubs(coverage_info, project_root, project_name)


def get_project_name(project_root: Path) -> str:
    """
    Get the project name from pyproject.toml or fall back to directory name.

    Args:
        project_root: Path to the project root

    Returns:
        Project name string
    """
    pyproject_path = project_root / "pyproject.toml"

    # Try to read project name from pyproject.toml
    if pyproject_path.exists() and tomllib is not None:
        try:
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)
                project_name = pyproject_data.get("project", {}).get("name", "")
                if project_name:
                    # Check if the project has a src directory structure
                    if (project_root / "src" / project_name).exists():
                        return project_name

                    # Check for non-src standard structure
                    if (project_root / project_name).exists():
                        return project_name
        except Exception:
            # If anything goes wrong, fall back to directory name
            pass

    # If we couldn't get the name from pyproject.toml, use directory name
    return os.path.basename(project_root)


def find_source_and_test_files(
    project_root: Path, project_name: str
) -> Tuple[List[Path], List[Path]]:
    """
    Find all source and test files in the project.

    Args:
        project_root: Path to the project root
        project_name: Name of the project

    Returns:
        Tuple containing lists of source and test files
    """
    source_files = []

    # Try src layout first (PEP 517/518 style)
    source_dir = project_root / "src" / project_name
    if source_dir.exists():
        # Recursively find all Python files in the source directory
        source_files = list(source_dir.glob("**/*.py"))
    else:
        # Try standard layout (package in root directory)
        source_dir = project_root / project_name
        if source_dir.exists():
            source_files = list(source_dir.glob("**/*.py"))

    # Find test files
    test_dir = project_root / "tests"
    test_files = []
    if test_dir.exists():
        # Recursively find all Python files in the test directory
        test_files = list(test_dir.glob("**/*.py"))

    return source_files, test_files


def calculate_coverage(
    source_files: List[Path], test_files: List[Path], project_name: str
) -> Dict:
    """
    Calculate test coverage for the project.

    Args:
        source_files: List of source files
        test_files: List of test files
        project_name: Name of the project

    Returns:
        Dictionary containing coverage information
    """
    # Convert source files to module paths
    source_modules = set()
    for file in source_files:
        if "__pycache__" in str(file):
            continue

        # Get proper module path depending on project structure (src or direct)
        try:
            # Try src layout first
            if "src" in file.parts:
                rel_path = file.relative_to(file.parts[0] / "src")
            else:
                # Try package in root directory
                rel_path = file.relative_to(file.parts[0])

            # Remove .py extension and convert to module path
            module_path = str(rel_path).replace("/", ".")[:-3]
            source_modules.add(module_path)
        except ValueError:
            # Skip files that don't match expected structure
            continue

    # Convert test files to module paths
    test_modules = set()
    test_files_without_source = []

    for file in test_files:
        if "__pycache__" in str(file) or "conftest.py" in str(file):
            test_files_without_source.append(file)
            continue

        # Get relative path
        try:
            rel_path = str(file.relative_to(file.parts[0]))
        except ValueError:
            test_files_without_source.append(file)
            continue

        # Check if it's a test for a source module
        is_source_test = False
        for src_module in source_modules:
            # Convert src_module to test module format
            src_parts = src_module.split(".")
            if len(src_parts) > 1:  # Ignore the project name itself
                test_module = f"tests.{'.'.join(src_parts[1:])}"
                test_file = f"test_{src_parts[-1]}"

                if test_file in rel_path and rel_path.replace("/", ".")[:-3].startswith(
                    test_module.replace(f".{src_parts[-1]}", "")
                ):
                    test_modules.add(src_module)
                    is_source_test = True
                    break

        if not is_source_test:
            test_files_without_source.append(file)

    # Calculate coverage percentage
    total_source_modules = len(source_modules)
    covered_modules = len(test_modules)
    coverage_percentage = (
        100.0
        if total_source_modules == 0
        else (covered_modules / total_source_modules) * 100
    )

    # Identify source files without tests
    source_modules_without_tests = source_modules - test_modules

    return {
        "total_source_files": total_source_modules,
        "total_test_files": len(test_files),
        "coverage_percentage": coverage_percentage,
        "source_modules_without_tests": source_modules_without_tests,
        "test_files_without_source": test_files_without_source,
    }


def display_coverage_report(coverage_info: Dict, project_root: Path) -> None:
    """
    Display test coverage report.

    Args:
        coverage_info: Dictionary containing coverage information
        project_root: Path to the project root
    """
    # Print the report
    click.echo(f"\nTest Coverage Report for {project_root}:")

    # Check if structure was detected correctly
    src_structure_detected = (project_root / "src").exists()
    project_name = os.path.basename(project_root)

    if src_structure_detected:
        click.echo(f"Detected package structure: src/{project_name}")
    else:
        click.echo(f"Detected package structure: {project_name}")

    click.echo(f"Total source files: {coverage_info['total_source_files']}")
    click.echo(f"Total test files: {coverage_info['total_test_files']}")
    click.echo(f"Test coverage: {coverage_info['coverage_percentage']:.1f}%")

    if coverage_info["test_files_without_source"]:
        click.echo("\nTest files without corresponding source files:")
        for file in coverage_info["test_files_without_source"]:
            click.echo(f"  - {file.relative_to(project_root)}")

    if coverage_info["source_modules_without_tests"]:
        # Count modules without tests
        modules_without_tests = len(coverage_info["source_modules_without_tests"])
        if modules_without_tests > 0:
            click.echo(f"\nSource modules without tests: {modules_without_tests}")
            if modules_without_tests <= 5:  # Only list if there are few missing tests
                for module in coverage_info["source_modules_without_tests"]:
                    click.echo(f"  - {module}")
            else:
                click.echo(
                    "Run 'zeroth-law create-test-stubs' to generate test stubs for missing tests."
                )


def create_test_stubs(
    coverage_info: Dict, project_root: Path, project_name: str
) -> None:
    """
    Create test stub files for source files without tests.

    Args:
        coverage_info: Dictionary containing coverage information
        project_root: Path to the project root
        project_name: Name of the project
    """
    # Get source modules without tests
    source_modules_without_tests = coverage_info["source_modules_without_tests"]

    # Create tests directory if it doesn't exist
    tests_dir = project_root / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Create test stubs
    for module in source_modules_without_tests:
        # Parse module path
        parts = module.split(".")
        if len(parts) <= 1:
            continue  # Skip the project module itself

        # Get relative path within source
        # If it's a src structure, parts[0] is project_name and we need parts[1:]
        # If it's not a src structure, we still use parts[1:] to skip the root
        rel_path = "/".join(parts[1:])

        # Create test directory if it doesn't exist
        test_dir = project_root / "tests" / "/".join(parts[1:-1])
        test_dir.mkdir(parents=True, exist_ok=True)

        # Create test file
        test_file = test_dir / f"test_{parts[-1]}.py"

        if not test_file.exists():
            click.echo(f"Creating test stub for {module}")

            # Create test stub file
            with open(test_file, "w") as f:
                f.write(
                    f'''"""
# PURPOSE: Tests for {module}.

## INTERFACES:
 - All test functions

## DEPENDENCIES:
 - pytest
 - {module}
"""
import pytest

# Import the module to test
from {module} import *

def test_{parts[-1]}_exists():
    """
    ZEROTH LAW VIOLATION: This is a placeholder test.
    
    This file was auto-generated by the Zeroth Law test coverage tool.
    Replace this with actual tests for the {parts[-1]} module.
    
    According to Zeroth Law section 6.1:
    - Test Coverage: >90% business logic coverage
    - Each feature should have a corresponding pytest for testing
    """
    # TODO: Replace with actual tests
    assert True, "Replace this with actual tests for the {parts[-1]} module"
'''
                )
        else:
            click.echo(
                f"Test file already exists: {test_file.relative_to(project_root)}"
            )


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added test coverage reporting
 - Added test stub generation for missing tests

## FUTURE TODOs:
 - Improve module-to-test matching logic
 - Add support for custom test paths
 - Add support for generating different styles of test stubs
"""
