# FILE_LOCATION: {{cookiecutter.project_name}}/src/{{cookiecutter.project_name}}/cli.py
"""
# PURPOSE: Main entry point for the CLI, registers and orchestrates commands.

## INTERFACES:
 - main(): CLI entry point that sets up logging and registers commands

## DEPENDENCIES:
 - click: Command-line interface creation
 - {{ cookiecutter.project_name }}.commands: Command implementations
"""
import logging
from typing import Optional

import click

from {{ cookiecutter.project_name }}.commands import hello, info

@click.group()
@click.option('-v', '--verbose', count=True, help="Increase verbosity (e.g., -v for INFO, -vv for DEBUG).")
@click.version_option(version="0.1.0")
@click.pass_context
def main(ctx: click.Context, verbose: int = 0):
    """Command-line interface for the {{ cookiecutter.project_name }} package."""
    # Initialize context object to store shared data
    ctx.ensure_object(dict)
    
    # Set up logging based on verbosity
    if verbose == 0:
        log_level = logging.WARNING
    elif verbose == 1:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Store logger in context for commands to use
    ctx.obj['logger'] = logging.getLogger('{{ cookiecutter.project_name }}')
    ctx.obj['verbose'] = verbose

# Register commands
main.add_command(hello.command)
main.add_command(info.command)

if __name__ == "__main__":
    main()  # Click will handle command-line arguments automatically

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Separated commands into individual modules
 - Simplified main CLI entry point
 - Fixed handling of verbose parameter

## FUTURE TODOs:
 - Consider adding command discovery mechanism
 - Add command group management
"""