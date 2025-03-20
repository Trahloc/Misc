# FILE_LOCATION: hfais/src/hfais/cli_args.py
"""
# PURPOSE: Provide reusable command-line arguments for the hfais package.

## INTERFACES:
 - add_args(command): Add standard arguments to a Click command
 - configure_logging(ctx: click.Context, verbose: int) -> None: Configures logging based on verbosity level.

## DEPENDENCIES:
 - click: Command-line interface creation library
 - logging: Standard logging functionality
"""
import logging
import click
from typing import Any

def add_args(command: click.Command) -> None:
    """
    PURPOSE: Add standard arguments to a Click command.

    PARAMS:
        command: The Click command to add arguments to

    RETURNS: None
    """
    command.params.append(click.Option(
        ["-v", "--verbose"],
        count=True,
        help="Increase verbosity (e.g., -v for INFO, -vv for DEBUG)."
    ))

def add_configure_logging(ctx: click.Context, verbose: int) -> None:
    """
    PURPOSE: Configure logging based on verbosity level.

    PARAMS:
        ctx: Click context object
        verbose: Verbosity level (0=WARNING, 1=INFO, 2+=DEBUG)

    RETURNS: None
    """
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
    logging.debug(f"Logging configured at level: {logging.getLevelName(log_level)}")

def add_cache_option(command):
    """
    PURPOSE: Add a --cache option to a Click command.

    PARAMS:
        command: The Click command to which the cache option will be added.

    RETURNS:
        The modified Click command.
    """
    return click.option(
        "--cache",
        default="cache.json",
        help="Path to cache the search results."
    )(command)

def add_min_size_option(command):
    """
    PURPOSE: Add a --min-size option to a Click command.

    PARAMS:
        command: The Click command to which the min-size option will be added.

    RETURNS:
        The modified Click command.
    """
    return click.option(
        "--min-size",
        type=int,
        default=0,
        help="Minimum model size in billions of parameters."
    )(command)

def add_max_size_option(command):
    """
    PURPOSE: Add a --max-size option to a Click command.

    PARAMS:
        command: The Click command to which the max-size option will be added.

    RETURNS:
        The modified Click command.
    """
    return click.option(
        "--max-size",
        type=int,
        default=1000,
        help="Maximum model size in billions of parameters."
    )(command)

def add_creator_option(command):
    """
    PURPOSE: Add a --creator option to a Click command.

    PARAMS:
        command: The Click command to which the creator option will be added.

    RETURNS:
        The modified Click command.
    """
    return click.option(
        "--creator",
        default=None,
        help="Filter by creator name."
    )(command)

def add_query_argument(command):
    """
    PURPOSE: Add a query argument to a Click command.

    PARAMS:
        command: The Click command to which the query argument will be added.

    RETURNS:
        The modified Click command.
    """
    return click.argument(
        "query"
    )(command)

def add_verbose_option(command):
    """
    PURPOSE: Add a --verbose option to a Click command.

    PARAMS:
        command: The Click command to which the verbose option will be added.

    RETURNS:
        The modified Click command.
    """
    return click.option(
        "-v", "--verbose",
        count=True,
        help="Increase verbosity (e.g., -v for INFO, -vv for DEBUG)."
    )(command)

def add_filter_results_command_name(command):
    """
    PURPOSE: Add a custom name for the filter-results command.

    PARAMS:
        command: The Click command to which the custom name will be added.

    RETURNS:
        The modified Click command.
    """
    return click.command(name="filter-results")(command)

def add_hello_command(command):
    """
    PURPOSE: Add the hello command decorator.
    PARAMS:
        command: The function to decorate as a hello command.
    RETURNS:
        The decorated command.
    """
    return click.command(name="hello")(command)

def add_info_command(command):
    """
    PURPOSE: Add the info command decorator.
    PARAMS:
        command: The function to decorate as an info command.
    RETURNS:
        The decorated command.
    """
    return click.command(name="info")(command)

def add_group_decorator(command):
    """
    PURPOSE: Add the @click.group decorator.

    PARAMS:
        command: The function to decorate as a group command.

    RETURNS:
        The decorated command.
    """
    return click.group()(command)

def add_echo_decorator(command):
    """
    PURPOSE: Add the @click.echo decorator.

    PARAMS:
        command: The function to decorate with echo functionality.

    RETURNS:
        The decorated command.
    """
    def add_wrapped_command(*args, **kwargs):
        result = command(*args, **kwargs)
        click.echo(result)
        return result

    return add_wrapped_command

def add_command_decorator(command_name):
    """
    PURPOSE: Add a @click.command decorator with a custom name.

    PARAMS:
        command_name: The name of the command.

    RETURNS:
        A decorator function for the command.
    """
    def add_decorator(command):
        return click.command(name=command_name)(command)
    return add_decorator

def add_argument(argument_name, required=False):
    """
    PURPOSE: Add a @click.argument decorator with a custom name.

    PARAMS:
        argument_name: The name of the argument.
        required: Whether the argument is required (default: False).

    RETURNS:
        A decorator function for the argument.
    """
    def add_argument_decorator(command):
        return click.argument(argument_name, required=required)(command)
    return add_argument_decorator

def add_option(option_name, **kwargs):
    """
    PURPOSE: Add a @click.option decorator with a custom name and parameters.

    PARAMS:
        option_name: The name of the option.
        kwargs: Additional parameters for the option.

    RETURNS:
        A decorator function for the option.
    """
    def add_option_decorator(command):
        return click.option(option_name, **kwargs)(command)
    return add_option_decorator

def add_echo(message: str) -> None:
    """
    PURPOSE: Abstraction for click.echo.

    PARAMS:
        message: The message to echo to the console.

    RETURNS: None
    """
    click.echo(message)

def add_click_exception(message: str) -> None:
    """
    PURPOSE: Raise a Click exception with the given message.

    PARAMS:
        message: The error message to display.

    RETURNS: None
    """
    raise click.ClickException(message)