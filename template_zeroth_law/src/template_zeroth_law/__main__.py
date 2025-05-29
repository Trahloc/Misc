# FILE: template_zeroth_law/src/template_zeroth_law/__main__.py
"""
# PURPOSE: Command line interface entry point for template_zeroth_law.

## INTERFACES:
 - cli(): Main CLI entry point
 - hello(): Example CLI command
 - init(): Project initialization command
 - main(): Module entry point

## DEPENDENCIES:
 - click: Command-line interface creation
 - pathlib: Path manipulation
 - sys: System-level operations

## TODO: Add project-specific CLI commands
"""

import sys
from pathlib import Path
from typing import List, Optional

import click

from template_zeroth_law.exceptions import ConfigError, FileError, ZerothLawError


@click.group()
@click.version_option()
def cli() -> None:
    """
    PURPOSE: Command line interface for template_zeroth_law
    CONTEXT: Entry point function called when running as a module
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: CLI is initialized
    RETURNS: None
    EXCEPTIONS: None
    USAGE EXAMPLES:
        $ python -m template_zeroth_law
    """
    pass


@cli.command()
def hello() -> None:
    """
    PURPOSE: Simple demo command that prints a greeting
    CONTEXT: Example CLI command
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: Greeting is printed to stdout
    RETURNS: None
    EXCEPTIONS: None
    USAGE EXAMPLES:
        $ python -m template_zeroth_law hello
    """
    click.echo("Hello from Template Zeroth Law!")


@cli.command()
@click.argument("project_name", required=False)
def init(project_name: Optional[str] = None) -> None:
    """
    PURPOSE: Initialize a new project based on the template
    CONTEXT: Project creation command
    PRE-CONDITIONS & ASSUMPTIONS: Running in a directory where the user has write permissions
    PARAMS:
        project_name (Optional[str]): Name of the project to create
    POST-CONDITIONS & GUARANTEES: New project directory created with basic structure
    RETURNS: None
    EXCEPTIONS:
        FileError: If there are issues with file operations
        ConfigError: If there are issues with project configuration
    USAGE EXAMPLES:
        $ python -m template_zeroth_law init my_new_project
    """
    if not project_name:
        project_name = click.prompt("Project name", default="my_zeroth_project")

    # Validate project name
    if not project_name.isidentifier():
        raise ConfigError(
            f"Project name '{project_name}' is not a valid Python identifier.",
            project_name=project_name,
        )

    # Create project directory
    project_dir = Path(project_name)
    if project_dir.exists():
        raise FileError(
            f"Directory '{project_name}' already exists.", path=str(project_dir)
        )

    # Create minimal project structure
    project_dir.mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "tests").mkdir()
    pkg_dir = project_dir / "src" / project_name
    pkg_dir.mkdir()

    # Create empty __init__.py files
    (pkg_dir / "__init__.py").touch()
    (project_dir / "tests" / "__init__.py").touch()

    click.echo(f"Created project: {project_name}")
    click.echo("Next steps:")
    click.echo(f"  cd {project_name}")
    click.echo("  pip install -e .[dev]")
    click.echo("  pre-commit install")
    click.echo("  git init")


def main(args: Optional[List[str]] = None) -> int:
    """
    PURPOSE: Main entry point for the CLI
    CONTEXT: Called by setuptools entry point or when module is run directly
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS:
        args (Optional[List[str]]): Command line arguments
    POST-CONDITIONS & GUARANTEES: CLI command is executed
    RETURNS:
        int: Exit code (0 for success)
    EXCEPTIONS:
        SystemExit: If CLI command fails
    USAGE EXAMPLES:
        >>> main(["hello"])
        Hello from Template Zeroth Law!
        0
    """
    if args is None:
        args = sys.argv[1:]

    try:
        cli(args)
        return 0
    except ZerothLawError as e:
        click.echo(f"Error: {e}", err=True)
        return 1
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())


"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Simplified CLI to essential commands with proper error handling
## FUTURE TODOs: Add more sophisticated project setup options
"""
