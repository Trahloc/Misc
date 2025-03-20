"""
# PURPOSE: Implements the info command to display project information

## INTERFACES:
 - command(details: bool): Displays project information

## DEPENDENCIES:
 - click: Command-line interface creation
"""
import logging
import click
from hfais.cli_args import (
    add_command_decorator,
    add_option,
    add_echo,
    add_click_exception
)

@add_command_decorator("info")
@add_option("--details", is_flag=True, help="Show detailed project information.")
@click.pass_context
def command(ctx: click.Context, details: bool = False):
    """Display information about this project."""
    if ctx.obj is None:
        ctx.obj = {}
    if 'logger' not in ctx.obj:
        ctx.obj['logger'] = logging.getLogger("hfais")
    if 'verbose' not in ctx.obj:
        ctx.obj['verbose'] = 0

    logger = ctx.obj['logger']

    try:
        project_info = {
            "name": "hfais",
            "version": "0.1.0",
            "description": "A project created with the Zeroth Law AI Framework"
        }

        messages = []
        messages.append(f"Project: {project_info['name']} v{project_info['version']}")

        if details or ctx.obj['verbose'] > 0:
            messages.append(f"Description: {project_info['description']}")
            messages.append("Created using the Zeroth Law AI Framework")
            logger.debug("Displayed detailed project information")

        output = "\n".join(messages)
        add_echo(output)
        logger.info("Project info command completed")
        return output
    except Exception as e:
        logger.error(f"Error displaying project info: {str(e)}")
        add_click_exception(str(e))

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added proper error handling
 - Using cli_args abstractions
 - Added --details flag
 - Isolated project information display logic

## FUTURE TODOs:
 - Add more project metadata
 - Consider loading info from configuration file
"""
