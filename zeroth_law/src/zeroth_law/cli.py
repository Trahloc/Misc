# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/cli.py
"""
# PURPOSE: Command-line interface for the Zeroth Law analyzer.

## INTERFACES:
 - main(): Runs the main command line

## DEPENDENCIES:
 - zeroth_law.analyzer
 - zeroth_law.reporting
 - zeroth_law.skeleton
 - zeroth_law.test_coverage
 - zeroth_law.utils
 - zeroth_law.exceptions
 - zeroth_law.template_converter
 - click
 - logging
"""
import logging
import sys
import os
from typing import Optional

import click

from zeroth_law.analyzer import analyze_file, analyze_directory
from zeroth_law.reporting.formatter import (
    format_compliance_report,
    format_summary_report,
)
from zeroth_law.reporting.updater import update_file_footer
from zeroth_law import skeleton
from zeroth_law.skeleton import create_skeleton
from zeroth_law.test_coverage import verify_test_coverage, CoverageError
from zeroth_law.utils.config import load_config
from zeroth_law.exceptions import ZerothLawError
from zeroth_law.template_converter import convert_to_template

logger = logging.getLogger(__name__)


@click.command()
@click.argument(
    "path",
    required=False,
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True),
)
@click.option(
    "-r", "--recursive", is_flag=True, help="Analyze directories recursively."
)
@click.option(
    "-s", "--summary", is_flag=True, help="Generate a summary report (for directories)."
)
@click.option(
    "-u", "--update", is_flag=True, help="Update file footers with compliance info."
)
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, file_okay=True, readable=True),
    help="Path to configuration file.",
)
@click.option("-v", "--verbose", count=True, help="Increase verbosity.")
@click.option(
    "--skel",
    type=str,
    help="Create a new project skeleton.",
)
@click.option(
    "--template",
    type=str,
    help="Template to use for skeleton (default: default).",
)
@click.option(
    "--list-templates",
    is_flag=True,
    help="List available project templates.",
)
@click.option(
    "--test-coverage",
    is_flag=True,
    help="Verify test coverage for Python files.",
)
@click.option(
    "--create-test-stubs",
    is_flag=True,
    help="Create test stubs for Python files without tests.",
)
@click.option(
    "--template-from",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True),
    help="Create a new template from an existing project.",
)
@click.option(
    "--template-name",
    type=str,
    help="Name for the new template.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing files when creating templates.",
)
def main(
    path: Optional[str],
    recursive: bool,
    summary: bool,
    update: bool,
    config_path: Optional[str],
    verbose: int,
    skel: Optional[str],
    template: Optional[str],
    list_templates: bool,
    test_coverage: bool,
    create_test_stubs: bool,
    template_from: Optional[str],
    template_name: Optional[str],
    overwrite: bool,
):
    """Main entry point for the Zeroth Law CLI."""
    # Set up logging
    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(message)s")

    # Load configuration
    config = load_config(config_path)

    # If create_test_stubs is specified, automatically enable test_coverage
    if create_test_stubs:
        test_coverage = True

    # Handle template listing
    if list_templates:
        templates = skeleton.list_templates()
        click.echo("Available templates:")
        for t in templates:
            click.echo(f"  - {t}")
        return

    # Handle template creation
    if template_from:
        if not template_name:
            click.echo("Error: --template-name is required with --template-from")
            sys.exit(1)
        try:
            convert_to_template(template_from, template_name, overwrite)
            click.echo(f"Created template '{template_name}' from {template_from}")
            return
        except Exception as e:
            click.echo(f"Error creating template: {e}")
            sys.exit(1)

    # Handle skeleton creation
    if skel:
        try:
            create_skeleton(skel)
            click.echo(f"Created project skeleton in {skel}")
            return
        except Exception as e:
            click.echo(f"Error creating skeleton: {e}")
            sys.exit(1)

    # Handle test coverage verification
    if test_coverage:
        try:
            verify_test_coverage(path, create_test_stubs)
            return
        except CoverageError as e:
            click.echo(f"Test coverage error: {e}")
            sys.exit(1)
        except Exception as e:
            click.echo(f"Error verifying test coverage: {e}")
            sys.exit(1)

    # Handle file/directory analysis
    try:
        if os.path.isfile(path):
            logger.info(f"Analyzing file: {path}")
            metrics = analyze_file(path)
            if update:
                update_file_footer(path, metrics)
            click.echo(format_compliance_report(metrics))
        elif os.path.isdir(path):
            logger.info(f"Analyzing directory: {path}")
            metrics = analyze_directory(
                path, recursive=recursive, summary=summary, config_path=config_path
            )
            if summary:
                click.echo("\nZEROTH LAW SUMMARY REPORT")
                click.echo("=======================\n")
                click.echo(format_summary_report(metrics))
            else:
                for file_metrics in metrics["files"]:
                    logger.info(f"Analyzing file: {file_metrics['path']}")
                    if update:
                        update_file_footer(
                            file_metrics["path"], file_metrics["results"]
                        )
                    click.echo(format_compliance_report(file_metrics["results"]))
        else:
            click.echo(f"Error: Path {path} does not exist")
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter

# ## KNOWN ERRORS:
# None
#
# ## IMPROVEMENTS:
# None
#
# ## FUTURE TODOs:
# None
#
# ## ZEROTH LAW COMPLIANCE:
# Overall Score: 90/100 - Excellent
# Penalties:
# - Function main exceeds max_function_lines (106/30): -5
# - Function main exceeds max_parameters (14/4): -5
# Analysis Timestamp: 2025-04-07T14:32:40.564680
