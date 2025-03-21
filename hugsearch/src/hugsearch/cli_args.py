# FILE_LOCATION: hugsearch/src/zeroth_law_template/cli_args.py
"""
# PURPOSE: Provide reusable command-line arguments for the hugsearch package.

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

def configure_logging(ctx: click.Context, verbose: int) -> None:
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