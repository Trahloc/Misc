"""
# PURPOSE: Implements the hello command for CLI.

## INTERFACES:
 - command(name: Optional[str], formal: bool): CLI command that greets a user

## DEPENDENCIES:
 - click: Command-line interface creation
 - {{ cookiecutter.project_name }}.greeter: User greeting functionality
"""
import sys
from typing import Optional
import click

from {{ cookiecutter.project_name }}.greeter import greet_user

@click.command()
@click.argument("name", required=False)
@click.option("--formal", is_flag=True, help="Use a formal greeting style.")
@click.pass_context
def command(ctx: click.Context, name: Optional[str], formal: bool):
    """Greet the specified user or the world if no name is provided."""
    logger = ctx.obj['logger']

    try:
        message = greet_user(name=name or "world", formal=formal)
        click.echo(message)
        logger.info(f"Greeted {'user' if name else 'the world'} successfully")
    except Exception as e:
        logger.error(f"Error during greeting: {str(e)}")
        sys.exit(1)

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Separated CLI concerns from business logic
 - Added proper error handling

## FUTURE TODOs:
 - Add more CLI options for greeting customization
"""
