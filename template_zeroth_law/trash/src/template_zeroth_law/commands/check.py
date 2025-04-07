"""
# PURPOSE: Implements system check commands for diagnosing issues

## INTERFACES:
 - command(): Main command entry point for system checks
 - check_deps(): Check package dependencies
 - check_env(): Check environment configuration
 - check_paths(): Check critical file paths

## DEPENDENCIES:
 - click: Command-line interface creation
 - pathlib: Path manipulation
 - sys: System-level operations
"""

import os
import sys
import platform
import click
from pathlib import Path
from typing import Dict, List, Optional, Any

from template_zeroth_law.utils import get_project_root


@click.command("check")
@click.option("--deps", is_flag=True, help="Check dependencies")
@click.option("--env", is_flag=True, help="Check environment")
@click.option("--paths", is_flag=True, help="Check file paths")
def command(deps: bool = False, env: bool = False, paths: bool = False) -> None:
    """
    PURPOSE: Check system configuration and display diagnostics.
    CONTEXT: CLI command for system diagnostics
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS:
        deps (bool): Check dependencies
        env (bool): Check environment
        paths (bool): Check file paths
    POST-CONDITIONS & GUARANTEES: Diagnostic information is displayed
    RETURNS: None
    EXCEPTIONS: None
    USAGE EXAMPLES:
        $ python -m template_zeroth_law check
        $ python -m template_zeroth_law check --deps --env --paths
    """
    # If no specific check is requested, run all checks
    if not any([deps, env, paths]):
        deps = env = paths = True

    click.echo("🔍 Running system checks...")

    if deps:
        check_deps()

    if env:
        check_env()

    if paths:
        check_paths()

    click.echo("\n✅ System check complete.")


def check_deps() -> None:
    """
    PURPOSE: Check and display information about package dependencies.
    CONTEXT: Part of system diagnostics
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: Dependency information is displayed
    RETURNS: None
    EXCEPTIONS: None
    """
    click.echo("\n🔍 Dependency Information:")

    # List of important packages to check
    important_packages = [
        "pytest",
        "click",
        "black",
        "flake8",
        "mypy",
    ]

    for package in important_packages:
        try:
            # Try to import the package
            __import__(package)
            status = "✅"
        except ImportError:
            status = "❌"

        click.echo(f"  {status} {package}")

    # Display Python version
    click.echo(f"  ℹ️ Python version: {platform.python_version()}")


def check_env() -> None:
    """
    PURPOSE: Check and display information about the environment.
    CONTEXT: Part of system diagnostics
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: Environment information is displayed
    RETURNS: None
    EXCEPTIONS: None
    """
    click.echo("\n🔍 Environment Information:")

    # Display platform information
    click.echo(f"  ℹ️ Platform: {platform.platform()}")
    click.echo(f"  ℹ️ Python executable: {sys.executable}")
    click.echo(f"  ℹ️ Current directory: {os.getcwd()}")

    # Display important environment variables
    important_vars = [
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "PATH",
    ]

    for var in important_vars:
        value = os.environ.get(var, "Not set")
        if var == "PATH":
            # Shorten PATH to avoid overwhelming output
            parts = value.split(os.pathsep)
            if len(parts) > 3:
                value = f"{os.pathsep.join(parts[:3])}... ({len(parts)} entries)"
        click.echo(f"  ℹ️ {var}: {value}")


def check_paths() -> None:
    """
    PURPOSE: Check and display information about critical file paths.
    CONTEXT: Part of system diagnostics
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: Path information is displayed
    RETURNS: None
    EXCEPTIONS: None
    """
    click.echo("\n🔍 Path Information:")

    # Current working directory
    cwd = Path.cwd()
    click.echo(f"  Working directory: {cwd}")

    # Project root
    project_root = get_project_root()
    click.echo(f"  Project root: {project_root}")

    # Module directory
    module_dir = Path(__file__).parent.parent
    click.echo(f"  Module directory: {module_dir}")

    # Check for common files and directories
    common_paths = [
        ("pyproject.toml", True),
        ("README.md", True),
        ("tests", False),
        ("src", False),
    ]

    for path_name, is_file in common_paths:
        full_path = project_root / path_name
        exists = full_path.exists()
        path_type = "File" if is_file else "Directory"
        status = "✅" if exists else "❌"
        click.echo(f"  {status} {path_type}: {path_name}")


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added modular check functions
 - Added click command interface
 - Added detailed diagnostics output
 - Added type hints and docstrings

## FUTURE TODOs:
 - Add more detailed dependency checking
 - Add configuration validation
 - Add project structure validation
 - Add custom checks based on project needs
"""
