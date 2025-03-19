# FILE_LOCATION: {{cookiecutter.project_name}}/src/{{cookiecutter.project_name}}/cli.py
"""
# PURPOSE: Main entry point for the CLI, registers and orchestrates commands.

## INTERFACES:
 - main(): CLI entry point that sets up logging and registers commands

## DEPENDENCIES:
 - click: Command-line interface creation
 - {{ cookiecutter.project_name }}.cli_args: CLI argument handling
 - {{ cookiecutter.project_name }}.commands: Command implementations
"""
import logging
from typing import Optional

import click

from {{ cookiecutter.project_name }} import cli_args
from {{ cookiecutter.project_name }}.commands import hello, info

@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def main(ctx: click.Context, verbose: int):
    """Command-line interface for the {{ cookiecutter.project_name }} package."""
    cli_args.add_args(ctx.command)
    cli_args.configure_logging(ctx, ctx.params.get("verbose", 0))
    ctx.ensure_object(dict)
    ctx.obj['logger'] = logging.getLogger('{{ cookiecutter.project_name }}')

# Register commands
main.add_command(hello.command)
main.add_command(info.command)

if __name__ == "__main__":
    main()

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Separated commands into individual modules
 - Simplified main CLI entry point

## FUTURE TODOs:
 - Consider adding command discovery mechanism
 - Add command group management
"""