# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/templates/cli_args.py.template
"""
# PURPOSE: Provide reusable command-line arguments for the {{ cookiecutter.project_name }} package.

## INTERFACES:
 - add_args(click_group): adds the arguments

## DEPENDENCIES:
 - click
 - logging
"""
import logging
import click
from typing import Union

def add_logging_args(group: click.Group) -> None:
    """Adds logging-related arguments (quiet, verbose, debug) to a click group."""
    group.add_option("-q", "--quiet", "verbosity", flag_value=logging.ERROR, help="Suppress all output except errors.")
    group.add_option("-v", "--verbose", "verbosity", flag_value=logging.INFO, help="Enable verbose output (INFO level).")
    group.add_option("-vv", "--debug", "verbosity", flag_value=logging.DEBUG, help="Enable debug output (DEBUG level).")

def add_version_arg(cmd: click.Command, version: str = "0.0.1") -> None:
    """Adds a --version option to the click Command."""
    cmd.params.append(click.Option(['--version'], is_flag=True, expose_value=False, is_eager=True, help="Show the version and exit.", callback=click.version_option(version=version)))

def configure_logging(ctx: click.Context, verbose:int) -> None:
    """Configures the logging level based on command-line arguments."""

    if verbose == 1:
        log_level = logging.INFO
    elif verbose > 1:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING  # Default log level
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

def add_args(cmd: click.Command):
    """Add all arguments"""
    # verbosity_group = click.Group("Verbosity") # Removed unused group
    # add_logging_args(verbosity_group) # Removed unused group
    # cmd.add_group(verbosity_group) # Removed unused group

    add_version_arg(cmd) #Add version