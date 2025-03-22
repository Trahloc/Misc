# FILE_LOCATION: {{ cookiecutter.project_name }}/src/{{ cookiecutter.project_name }}/cli.py
"""
# PURPOSE: Main entry point for the CLI, registers and orchestrates commands.

## INTERFACES:
 - main(): CLI entry point that sets up logging and registers commands

## DEPENDENCIES:
 - click: Command-line interface creation
 - {{ cookiecutter.project_name }}.commands: Command implementations
 - {{ cookiecutter.project_name }}.config: Configuration management
"""
import logging
import sys
from typing import Optional  # Only import what's needed for the type annotation

import click

from {{ cookiecutter.project_name }}.commands import check, version, info
from {{ cookiecutter.project_name }}.config import get_config

@click.group()
@click.option('-v', '--verbose', count=True, help="Increase verbosity (e.g., -v for INFO, -vv for DEBUG).")
@click.option('--config', type=str, help="Path to configuration file.")
@click.pass_context
def main(ctx: click.Context, verbose: int = 0, config: Optional[str] = None) -> None:
    """Command-line interface for the {{ cookiecutter.project_name }} package."""
    # Initialize context object to store shared data
    ctx.ensure_object(dict)
    
    # Load configuration
    app_config = get_config(config)
    
    # Use config version or fallback to default
    version_str = getattr(app_config.app, 'version', "0.1.0")
    
    # Set up logging based on verbosity
    if verbose == 0:
        log_level = logging.WARNING
    elif verbose == 1:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format=app_config.logging.format,
        datefmt=app_config.logging.date_format
    )
    
    # Store logger and config in context for commands to use
    ctx.obj['logger'] = logging.getLogger('{{ cookiecutter.project_name }}')
    ctx.obj['config'] = app_config
    ctx.obj['verbose'] = verbose

# Register commands
main.add_command(version.command)
main.add_command(check.command)
main.add_command(info.command)

# When run as a script
if __name__ == "__main__":
    # Call main function with empty object
    sys.exit(main(obj={}))  # type: ignore

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added configuration file option
 - Load configuration for use in commands
 - Use configuration values for logging format
 - Updated to include only essential commands
 - Added command to display project information
 - Fixed linter errors with proper type annotations

## FUTURE TODOs:
 - Consider adding command discovery mechanism
 - Add command group management for larger projects
 - Add support for environment variable configuration
"""