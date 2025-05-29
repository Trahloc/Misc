"""
# PURPOSE: CLI argument handling for Zeroth Law Framework.

## INTERFACES:
 - add_args: Add common arguments to commands
 - configure_logging: Configure logging based on verbosity
 - setup_cli_context: Set up CLI context

## DEPENDENCIES:
 - click: Command-line interface utilities
 - logging: Python logging facilities
"""

import logging
from typing import Any, Callable, TypeVar, cast

import click

# Type variable for function decoration
F = TypeVar("F", bound=Callable[..., Any])


def add_args(command: F) -> F:
    """Add common arguments to Click commands."""
    # Add verbose option
    command = cast(
        F,
        click.option(
            "-v",
            "--verbose",
            count=True,
            help="Increase verbosity (can be used multiple times).",
            default=0,
        )(command),
    )

    return command


def configure_logging(ctx: click.Context, verbose: int) -> None:
    """Configure logging based on verbosity level."""
    from template_zeroth_law.config import get_config
    from template_zeroth_law.logging import configure_logging as setup_logging

    # Get config from context or load default
    config = ctx.obj.get("config") if ctx.obj else None
    if config is None:
        config = get_config(ctx.params.get("config"))
        if ctx.obj is None:
            ctx.obj = {}
        ctx.obj["config"] = config

    # Set log level based on verbosity
    if verbose <= 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    # Configure logging using our custom configuration
    logger = setup_logging(
        level=level,
        log_format=getattr(
            config.logging,
            "format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        ),
        date_format=getattr(config.logging, "date_format", "%Y-%m-%d %H:%M:%S"),
    )

    # Store in context
    ctx.obj["logger"] = logger
    ctx.obj["verbose"] = verbose


def setup_cli_context(ctx: click.Context) -> None:
    """Set up CLI context for commands."""
    if ctx.obj is None:
        ctx.obj = {}
    verbose = ctx.params.get("verbose", 0)
    configure_logging(ctx, verbose)
    # Store config in context if not already present
    if "config" not in ctx.obj:
        from .config import get_config

        config_path = ctx.params.get("config")
        ctx.obj["config"] = get_config(config_path)


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Fixed verbose argument handling
 - Added proper handler cleanup
 - Added proper context initialization
 - Added proper type hints

## FUTURE TODOs:
 - Add support for log file output
 - Add support for custom log formats
 - Add support for environment-based configuration
"""
