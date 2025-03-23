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
 - zeroth_law.config
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
from zeroth_law.reporting import generate_report, generate_summary_report
from zeroth_law import skeleton
from zeroth_law.skeleton import create_skeleton
from zeroth_law.test_coverage import verify_test_coverage, CoverageError
from zeroth_law.config import load_config, DEFAULT_CONFIG
from zeroth_law.exceptions import ZerothLawError
from zeroth_law.template_converter import convert_to_template


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
    "-u", "--update", is_flag=True, help="Update file footers with analysis results."
)
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to a configuration file.",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (e.g., -v for INFO, -vv for DEBUG).",
)
@click.version_option(version="0.1.0")  # Replace with actual version
@click.option(
    "--skel", metavar="DIRECTORY", help="Create a new Zeroth Law project skeleton."
)
@click.option("--template", help="Template to use with --skel (defaults to 'default')")
@click.option("--list-templates", is_flag=True, help="List available project templates")
@click.option(
    "--test-coverage", is_flag=True, help="Verify test coverage for the project."
)
@click.option(
    "--create-test-stubs",
    is_flag=True,
    help="Create test stubs for files without tests (used with --test-coverage).",
)
@click.option(
    "--template-from", help="Convert an existing project into a cookiecutter template"
)
@click.option(
    "--template-name",
    default="test_zeroth_law",
    help="Name for the template project (default: test_zeroth_law)",
)
@click.option(
    "--overwrite", is_flag=True, help="Overwrite existing template if it exists"
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
    """Command-line interface for the analyzer."""
    logger = logging.getLogger(__name__)

    # Configure logging based on verbosity
    if verbose == 0:
        logging.basicConfig(level=logging.WARNING)
    elif verbose == 1:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)

    # If create_test_stubs is specified, automatically enable test_coverage
    if create_test_stubs:
        test_coverage = True

    if list_templates:
        templates = skeleton.list_templates()
        if not templates:
            click.echo("No templates available. Use --template-from to create one.")
        else:
            click.echo("Available templates:")
            for t in templates:
                click.echo(f"  - {t}")
        return

    if skel:
        try:
            create_skeleton(skel, template)
        except FileExistsError as e:
            logger.error(str(e))
            sys.exit(1)
        except FileNotFoundError as e:
            logger.error(str(e))
            sys.exit(1)
        return

    if test_coverage:
        if not path:
            path = os.getcwd()
            logger.info("No path specified, using current directory: %s", path)

        try:
            metrics = verify_test_coverage(path, create_stubs=create_test_stubs)

            # Report the results
            click.echo(f"\nTest Coverage Report for {path}:")

            # Show detected project structure
            structure_type = metrics.get("structure_type", "unknown")
            click.echo(f"Detected package structure: {structure_type}")

            click.echo(f"Total source files: {metrics['total_source_files']}")
            click.echo(f"Total test files: {metrics['total_test_files']}")
            click.echo(f"Test coverage: {metrics['coverage_percentage']:.1f}%")

            # Report missing tests
            if metrics["missing_tests"]:
                click.echo("\nSource files missing tests:")
                for source_file in metrics["missing_tests"]:
                    click.echo(f"  - {source_file}")

                if create_test_stubs:
                    click.echo("\nTest stubs created for missing tests.")
                else:
                    click.echo(
                        "\nUse --create-test-stubs to generate test stubs for these files."
                    )

            # Report orphaned tests (tests without source files)
            if metrics.get("orphaned_tests"):
                click.echo("\nTest files without corresponding source files:")
                for test_file in metrics["orphaned_tests"]:
                    click.echo(f"  - {test_file}")

            # Exit with non-zero status if coverage is below 90%
            if metrics["coverage_percentage"] < 90:
                click.echo("\nZEROTH LAW VIOLATION: Test coverage below 90%.")
                if not create_test_stubs:
                    sys.exit(1)

            return
        except (OSError, CoverageError) as e:
            logger.error("Error verifying test coverage: %s", str(e))
            sys.exit(1)
        except KeyError as e:
            logger.error(
                "Invalid metrics format returned from verify_test_coverage: %s", str(e)
            )
            sys.exit(1)

    if template_from:
        try:
            convert_to_template(
                template_from, template_name or "test_zeroth_law", overwrite
            )
        except (FileNotFoundError, FileExistsError, ValueError) as e:
            logger.error("Failed to convert project to template: %s", str(e))
            sys.exit(1)
        return

    if not path:
        click.echo(click.get_current_context().get_help())
        sys.exit(1)

    # Load configuration
    try:
        if config_path:
            config = load_config(config_path)
        else:
            default_config_path = os.path.join(os.getcwd(), ".zeroth_law.toml")
            if os.path.isfile(default_config_path):
                config = load_config(default_config_path)
            else:
                config = DEFAULT_CONFIG
    except ZerothLawError as e:
        logger.error("Error loading config: %s", str(e))
        sys.exit(1)

    try:
        if os.path.isfile(path):
            metrics = analyze_file(path, update=update, config=config)
            click.echo(generate_report(metrics))
        elif os.path.isdir(path):
            all_metrics = analyze_directory(
                path, recursive=recursive, update=update, config=config
            )
            if summary:
                click.echo(generate_summary_report(all_metrics))
            else:
                for metrics in all_metrics:
                    click.echo(generate_report(metrics))
                    logger.debug("-" * 20)  # Separator line
        else:
            logger.error("Invalid path: %s", path)
            sys.exit(1)

    except ZerothLawError as e:
        logger.error(str(e))
        if update:
            logger.warning("File updates may be incomplete due to the error.")
        sys.exit(1)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
