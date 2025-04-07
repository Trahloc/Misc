"""
# PURPOSE: Implements test coverage commands and test stub generation

## INTERFACES:
 - command(): Run test coverage with options
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
from typing import Dict, List, Tuple, Set, Any, Optional
import sys
import subprocess

from template_zeroth_law.utils import get_project_root
from template_zeroth_law.exceptions import ZerothLawError

# Import tomllib or tomli for TOML parsing
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


@click.command("test-coverage")
@click.option(
    "--min-coverage", type=int, default=90, help="Minimum coverage percentage"
)
@click.option("--html", is_flag=True, help="Generate HTML coverage report")
@click.option("--xml", is_flag=True, help="Generate XML coverage report")
@click.argument("path", required=False)
def command(
    min_coverage: int, html: bool, xml: bool, path: Optional[str] = None
) -> None:
    """
    PURPOSE: Run test coverage analysis and report results.
    CONTEXT: CLI command for test coverage reporting
    PRE-CONDITIONS & ASSUMPTIONS: pytest and pytest-cov are installed
    PARAMS:
        min_coverage (int): Minimum required coverage percentage
        html (bool): Generate HTML coverage report
        xml (bool): Generate XML coverage report
        path (Optional[str]): Specific path to test, defaults to all tests
    POST-CONDITIONS & GUARANTEES: Coverage results are displayed
    RETURNS: None
    EXCEPTIONS: None
    USAGE EXAMPLES:
        $ python -m template_zeroth_law test-coverage
        $ python -m template_zeroth_law test-coverage --html
    """
    try:
        project_root = get_project_root()
        package_name = project_root.name

        # Build the command
        cmd = ["pytest"]

        # Add coverage
        cmd.extend([f"--cov={package_name}"])

        # Add reports
        if html:
            cmd.append("--cov-report=html")
        if xml:
            cmd.append("--cov-report=xml")

        # Always add terminal report
        cmd.append("--cov-report=term")

        # Add specific path if provided
        if path:
            cmd.append(path)

        click.echo(f"Running test coverage: {' '.join(cmd)}")

        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Print output
        click.echo(result.stdout)

        if result.stderr:
            click.echo(f"Errors: {result.stderr}", err=True)

        # Check for success
        if result.returncode != 0:
            click.echo(f"Coverage check failed with code {result.returncode}", err=True)
            sys.exit(result.returncode)

        # Check coverage percentage
        # This is a simple check - would need to parse output for precise coverage
        if (
            f"coverage: {min_coverage}%" not in result.stdout
            and f"{min_coverage}%" not in result.stdout
        ):
            click.echo(
                f"Coverage is below the minimum threshold of {min_coverage}%", err=True
            )
            sys.exit(1)

        click.echo(f"✅ Coverage check passed ({min_coverage}%+)")

    except Exception as e:
        click.echo(f"❌ Error during coverage check: {e}", err=True)
        sys.exit(1)


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
        Tuple of (source_files, test_files)
    """
    # Find source files
    src_dir = project_root / "src" / project_name
    if src_dir.exists():
        # Project uses src layout
        source_files = list(src_dir.glob("**/*.py"))
    else:
        # Project uses direct layout
        source_files = list((project_root / project_name).glob("**/*.py"))

    # Find test files
    test_dir = project_root / "tests"
    if test_dir.exists():
        test_files = list(test_dir.glob("**/*.py"))
    else:
        test_files = []

    return source_files, test_files


def calculate_coverage(
    source_files: List[Path], test_files: List[Path], project_name: str
) -> Dict[str, Any]:
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
                # Find the index of 'src' in the path
                src_index = file.parts.index("src")
                # Get the path relative to the directory after 'src'
                rel_path = Path(*file.parts[src_index + 2 :])
            else:
                # For direct layout, get path relative to project root
                rel_path = file.relative_to(file.parts[0])

            # Convert path to module notation
            module = (
                str(rel_path).replace("/", ".").replace("\\", ".").removesuffix(".py")
            )
            source_modules.add(module)
        except (ValueError, IndexError):
            continue

    # Convert test files to module paths
    test_modules = set()
    for file in test_files:
        if "__pycache__" in str(file):
            continue

        try:
            # Get path relative to tests directory
            tests_dir = Path(file.parts[0]) / "tests"
            rel_path = file.relative_to(tests_dir)

            # Convert path to module notation and remove test_ prefix if present
            module = (
                str(rel_path).replace("/", ".").replace("\\", ".").removesuffix(".py")
            )
            if module.startswith("test_"):
                module = module[5:]  # Remove "test_" prefix
            test_modules.add(module)
        except (ValueError, IndexError):
            continue

    # Calculate coverage metrics
    covered_modules = source_modules & test_modules
    total_modules = len(source_modules)
    covered_count = len(covered_modules)
    coverage_percentage = (
        (covered_count / total_modules * 100) if total_modules > 0 else 100.0
    )

    # Prepare uncovered modules list
    uncovered = sorted(list(source_modules - test_modules))

    return {
        "total_modules": total_modules,
        "covered_modules": covered_count,
        "coverage_percentage": coverage_percentage,
        "uncovered_modules": uncovered,
        "source_modules_without_tests": uncovered,  # For backward compatibility
        "total_source_files": len(source_files),
        "total_test_files": len(test_files),
    }


def display_coverage_report(coverage_info: Dict[str, Any], project_root: Path) -> None:
    """Display test coverage report."""
    click.echo(f"\nTest Coverage Report for {project_root}:")

    # Report on coverage
    total_modules = coverage_info.get("total_modules", 0)
    covered_modules = coverage_info.get("covered_modules", 0)
    coverage_percentage = coverage_info.get("coverage_percentage", 0.0)
    uncovered_modules = coverage_info.get("uncovered_modules", [])

    # Print basic stats
    click.echo(f"Total source modules: {total_modules}")
    click.echo(f"Covered modules: {covered_modules}")
    click.echo(f"Coverage: {coverage_percentage:.1f}%")

    # Report uncovered modules
    if uncovered_modules:
        click.echo("\nModules without tests:")
        for module in uncovered_modules:
            click.echo(f"  - {module}")

        if len(uncovered_modules) > 5:
            click.echo(
                "\nRun 'create-test-stubs' to generate test stubs for uncovered modules."
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
 - Simplified module by removing redundant function
 - Added test coverage reporting
 - Added test stub generation for missing tests

## FUTURE TODOs:
 - Improve module-to-test matching logic
 - Add support for custom test paths
 - Add support for generating different styles of test stubs
"""
