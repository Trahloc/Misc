"""
# PURPOSE: Implements the hello command for CLI.

## INTERFACES:
 - command(name: Optional[str], formal: bool): CLI command that greets a user

## DEPENDENCIES:
 - click: Command-line interface creation
 - hfais.greeter: User greeting functionality
"""
import sys
import logging
from typing import Optional
import click

from hfais.greeter import greet_user
from hfais.cli_args import (
    add_command_decorator,
    add_option,
    add_argument,
    add_echo,
    add_click_exception
)

@add_command_decorator("hello")
@add_argument("name", required=False)
@add_option("--formal", is_flag=True, help="Use a formal greeting.")
@click.pass_context
def command(ctx: click.Context, name: Optional[str] = None, formal: bool = False):
    """Greet the specified user or the world if no name is provided."""
    if ctx.obj is None:
        ctx.obj = {}
    if 'logger' not in ctx.obj:
        ctx.obj['logger'] = logging.getLogger("hfais")
    if 'verbose' not in ctx.obj:
        ctx.obj['verbose'] = 0

    logger = ctx.obj['logger']
    try:
        message = greet_user(name=name if name is not None else "world", formal=formal)
        add_echo(message)
        return message
    except ValueError as e:
        logger.error(f"Error during greeting: {str(e)}")
        add_click_exception(str(e))
    except Exception as e:
        logger.error(f"Unexpected error during greeting: {str(e)}")
        add_click_exception(str(e))

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Separated CLI concerns from business logic
 - Added proper error handling
 - Using cli_args abstractions

## FUTURE TODOs:
 - Add more CLI options for greeting customization
"""
