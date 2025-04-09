# FILE_LOCATION: hugsearch/src/hugsearch/commands/version.py
"""
# PURPOSE: Implements the version command for CLI.

## INTERFACES:
 - command(verbose: bool): CLI command that displays version information

## DEPENDENCIES:
 - click: Command-line interface creation
 - importlib.metadata: Package version information (Python 3.8+)
 - hugsearch.config: Configuration management
"""

import sys
import platform
from datetime import datetime
import click

# Use importlib.metadata for Python 3.8+ or pkg_resources as fallback
if sys.version_info >= (3, 8):
    from importlib import metadata as importlib_metadata

    def get_package_version(package_name):
        """Get package version using importlib.metadata."""
        try:
            return importlib_metadata.version(package_name)
        except importlib_metadata.PackageNotFoundError:
            return "unknown"
else:
    import pkg_resources

    def get_package_version(package_name):
        """Get package version using pkg_resources."""
        try:
            return pkg_resources.get_distribution(package_name).version
        except pkg_resources.DistributionNotFound:
            return "unknown"


from hugsearch.config import get_config


@click.command(name="version")
@click.option("--json", is_flag=True, help="Output version information in JSON format.")
@click.pass_context
def command(ctx: click.Context, json: bool):
    """Display version information about the application."""
    logger = ctx.obj["logger"]
    # Get verbosity from parent context
    verbose = 0
    if ctx.parent:
        verbose = ctx.parent.params.get("verbose", 0)

    try:
        # Get basic version info from config
        config = get_config()
        app_name = config.app.name
        version = config.app.version
        description = config.app.description

        # Basic version info
        if json:
            import json as json_lib

            output = {
                "name": app_name,
                "version": version,
                "description": description,
            }

            if verbose > 0:
                # Add system info
                output["system"] = {
                    "python_version": sys.version.split()[0],
                    "platform": platform.platform(),
                    "system": f"{platform.system()} {platform.release()}",
                }

                # Add dependency info
                deps = {}
                for dep in ["click", "pytest", "pylint"]:
                    deps[dep] = get_package_version(dep)
                output["dependencies"] = deps

                # Add timestamp
                output["timestamp"] = datetime.now().isoformat()

            click.echo(json_lib.dumps(output, indent=2))
            if verbose > 1:
                click.echo("[DEBUG] JSON output generated successfully")
        else:
            # Text output
            msg = f"{app_name} v{version}"
            if verbose > 0:
                click.echo(f"[INFO] {msg}")
            else:
                click.echo(msg)
            logger.info(msg)

            if verbose > 0:
                msg = f"Description: {description}"
                click.echo(f"[INFO] {msg}")
                logger.info(msg)

                msg = f"Python: {sys.version.split()[0]}"
                click.echo(f"[INFO] {msg}")
                logger.info(msg)

                msg = f"Platform: {platform.platform()}"
                click.echo(f"[INFO] {msg}")
                logger.info(msg)

                click.echo("\nDependencies:")
                for dep in ["click", "pytest", "pylint"]:
                    ver = get_package_version(dep)
                    msg = f"  • {dep}: {ver}"
                    click.echo(f"[INFO] {msg}")
                    logger.info(msg)
                    if verbose > 1:
                        click.echo(f"[DEBUG] Resolved {dep} version to {ver}")

                msg = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                click.echo(f"[INFO] {msg}")
                logger.info(msg)

        # Log command execution
        logger.info(f"Version command executed (verbose={verbose})")
        if verbose > 1:
            click.echo("[DEBUG] Version command completed successfully")
    except Exception as e:
        error_msg = f"Error retrieving version information: {str(e)}"
        click.echo(f"[ERROR] {error_msg}", err=True)
        logger.error(error_msg)
        ctx.exit(1)


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added detailed version information
 - Added optional JSON output
 - Added dependency version reporting
 - Used modern importlib.metadata when available

## FUTURE TODOs:
 - Add Git commit information when in a Git repository
 - Add build date information
 - Add license information
"""
