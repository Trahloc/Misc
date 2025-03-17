# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/cli.py
"""
# PURPOSE: Command-line interface for the Zeroth Law analyzer.

## INTERFACES:
 - main(): Runs the main command line

## DEPENDENCIES:
 - zeroth_law.analyzer
 - zeroth_law.reporting
 - zeroth_law.skeleton
 - zeroth_law.config
 - zeroth_law.exceptions
 - click
 - logging
"""
import logging
import sys
import os
from typing import Optional

import click

from zeroth_law.analyzer import analyze_file, analyze_directory
from zeroth_law.reporting import generate_report, generate_summary_report
from zeroth_law.skeleton import create_skeleton
from zeroth_law.config import load_config, DEFAULT_CONFIG
from zeroth_law.exceptions import ZerothLawError

@click.command()
@click.argument("path", required=False, type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True))
@click.option("-r", "--recursive", is_flag=True, help="Analyze directories recursively.")
@click.option("-s", "--summary", is_flag=True, help="Generate a summary report (for directories).")
@click.option("-u", "--update", is_flag=True, help="Update file footers with analysis results.")
@click.option("-c", "--config", "config_path", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to a configuration file.")
@click.option("-v", "--verbose", count=True, help="Increase verbosity (e.g., -v for INFO, -vv for DEBUG).")
@click.version_option(version="0.1.0")  # Replace with actual version
@click.option("--skel", metavar="DIRECTORY", help="Create a new Zeroth Law project skeleton.")
def main(path: Optional[str], recursive: bool, summary: bool, update: bool, config_path: Optional[str], verbose: int, skel: Optional[str]):
    """Command-line interface for the analyzer."""

    if verbose == 1:
        log_level = logging.INFO
    elif verbose > 1:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING  # Default log level

    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)


    if skel:
        try:
            create_skeleton(skel)
        except FileExistsError as e:
            logger.error(e)
            sys.exit(1)
        return

    if not path:
        click.echo(click.get_current_context().get_help())
        sys.exit(1)

    # Load configuration
    try:
        config = load_config(config_path) if config_path else DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)

    try:
        if os.path.isfile(path):
            metrics = analyze_file(path, update=update, config=config)
            if not verbose:  # Don't print if quiet (verbosity > 0)
                click.echo(generate_report(metrics))

        elif os.path.isdir(path):
            all_metrics = analyze_directory(path, recursive=recursive, update=update, config=config)
            if summary:
                if not verbose: # Don't print if quiet
                    click.echo(generate_summary_report(all_metrics))
            else:
                for metrics in all_metrics:
                    if not verbose:
                        click.echo(generate_report(metrics))
                    logger.debug("-" * 20)  # Separator line
        else:
            logger.error(f"Invalid path: {path}")
            sys.exit(1)

    except ZerothLawError as e:
        logger.error(str(e))
        if update:
            logger.warning("File updates may be incomplete due to the error.")
        sys.exit(1)

if __name__ == "__main__":
    main()