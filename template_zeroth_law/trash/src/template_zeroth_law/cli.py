# FILE_LOCATION: template_zeroth_law/src/template_zeroth_law/cli.py
"""
# PURPOSE: Main entry point for the CLI, registers and orchestrates commands.

## INTERFACES:
 - main(): CLI entry point that sets up logging and registers commands

## DEPENDENCIES:
 - click: Command-line interface creation
 - template_zeroth_law.commands: Command implementations
 - template_zeroth_law.config: Configuration management
"""

import logging
import sys
from typing import \
    Optional  # Only import what's needed for the type annotation

import click

from template_zeroth_law.commands import check, info, test_coverage, version
from template_zeroth_law.config import get_config


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (e.g., -v for INFO, -vv for DEBUG).",
)
@click.option("--config", type=str, help="Path to configuration file.")
@click.pass_context
def main(ctx: click.Context, verbose: int = 0, config: Optional[str] = None) -> None:
    """Command-line interface for the template_zeroth_law package."""
    # Input validation
    assert (
        isinstance(verbose, int) and verbose >= 0
    ), f"Verbosity must be non-negative integer, got {verbose}"
    assert config is None or isinstance(
        config, str
    ), f"Config must be string or None, got {type(config)}"

    # Initialize context object to store shared data
    ctx.ensure_object(dict)

    # Load configuration
    app_config = get_config(config)
    assert hasattr(app_config, "logging"), "Configuration must contain logging settings"

    # Use config version or fallback to default
    getattr(app_config.app, "version", "0.1.0")

    # Set up logging based on verbosity
    log_level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}.get(
        verbose, logging.DEBUG
    )  # Default to DEBUG for verbose > 2

    logging.basicConfig(
        level=log_level,
        format=app_config.logging.format,
        datefmt=app_config.logging.date_format,
    )

    # Store logger and config in context for commands to use
    logger = logging.getLogger("template_zeroth_law")
    assert logger is not None, "Failed to create logger"

    ctx.obj["logger"] = logger
    ctx.obj["config"] = app_config
    ctx.obj["verbose"] = verbose

    # Validate context setup
    assert all(
        key in ctx.obj for key in ["logger", "config", "verbose"]
    ), "Context missing required keys"


# Register commands
main.add_command(version.command)
main.add_command(check.command)
main.add_command(info.command)
main.add_command(test_coverage.command_test_coverage)
main.add_command(test_coverage.command_create_test_stubs)

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
 - Added test coverage and test stub generation commands

## FUTURE TODOs:
 - Consider adding command discovery mechanism
 - Add command group management for larger projects
 - Add support for environment variable configuration
"""
