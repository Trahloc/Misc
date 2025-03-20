# FILE_LOCATION: hfais/src/hfais/cli.py
"""
# PURPOSE: Main entry point for the CLI, registers and orchestrates commands.

## INTERFACES:
 - main(): CLI entry point that sets up logging and registers commands

## DEPENDENCIES:
 - click: Command-line interface creation
 - hfais.cli_args: CLI argument handling
 - hfais.commands: Command implementations
"""
import logging
import click
import requests
import json
from typing import Optional

from hfais import cli_args
from hfais.commands import hello, info
from hfais.hf_api import search_hf_models, cache_results, load_cached_results
from hfais.filters import filter_by_size, filter_by_creator
from hfais.cli_args import (
    add_cache_option,
    add_min_size_option,
    add_max_size_option,
    add_creator_option,
    add_query_argument,
    add_verbose_option,
    add_filter_results_command_name,
    add_group_decorator,
    add_command_decorator,
    add_configure_logging,
    add_echo
)

@add_group_decorator
@add_verbose_option
@click.pass_context
def main(ctx: click.Context, verbose: int = 0):
    """Main CLI entry point."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['logger'] = logging.getLogger("hfais")

    # Configure logging based on verbosity
    add_configure_logging(ctx, verbose)

# Register commands
main.add_command(hello.command)
main.add_command(info.command)

@add_command_decorator("search")
@add_cache_option
@add_query_argument
@click.pass_context
def search_command(ctx: click.Context, query: str, cache: str):
    """Search HuggingFace models and cache results."""
    logger = ctx.obj['logger']
    if not cache:
        logger.error("Cache path is required.")
        ctx.exit(1)
    try:
        results = search_hf_models(query)
        cache_results(results, cache)
        add_echo(f"Cached {len(results)} results to {cache}")
        logger.info(f"Search completed and cached {len(results)} results")
    except requests.RequestException as e:
        logger.error(f"Network error during search: {str(e)}")
        ctx.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during search: {str(e)}")
        ctx.exit(1)

@add_filter_results_command_name
@add_cache_option
@add_min_size_option
@add_max_size_option
@add_creator_option
@click.pass_context
def filter_results(ctx: click.Context, cache: str, min_size: int, max_size: int, creator: Optional[str]):
    """Filter cached results with advanced criteria."""
    logger = ctx.obj['logger']
    if not cache:
        logger.error("Cache path is required.")
        ctx.exit(1)
    try:
        results = load_cached_results(cache)
        if min_size or max_size:
            results = filter_by_size(results, min_size, max_size)
        if creator:
            results = filter_by_creator(results, creator)
        add_echo(f"Filtered results: {len(results)} models")
        logger.info(f"Filtering completed with {len(results)} results")
    except FileNotFoundError as e:
        logger.error(f"Cache file not found: {str(e)}")
        ctx.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding cache file: {str(e)}")
        ctx.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during filtering: {str(e)}")
        ctx.exit(1)

# Register new commands
main.add_command(search_command)
main.add_command(filter_results)

if __name__ == "__main__":
    main()

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Separated commands into individual modules
 - Using cli_args abstractions
 - Proper context initialization

## FUTURE TODOs:
 - Consider adding command discovery mechanism
 - Add command group management
"""