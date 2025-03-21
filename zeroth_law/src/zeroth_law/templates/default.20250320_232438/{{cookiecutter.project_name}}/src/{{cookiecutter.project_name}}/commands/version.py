# FILE_LOCATION: {{ cookiecutter.project_name }}/src/{{ cookiecutter.project_name }}/commands/version.py
"""
# PURPOSE: Implements the version command for CLI.

## INTERFACES:
 - command(verbose: bool): CLI command that displays version information

## DEPENDENCIES:
 - click: Command-line interface creation
 - importlib.metadata: Package version information (Python 3.8+)
 - zeroth_law_template.config: Configuration management
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

from {{ cookiecutter.project_name }}.config import get_config

@click.command(name="version")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed version information.")
@click.option("--json", is_flag=True, help="Output version information in JSON format.")
@click.pass_context
def command(ctx: click.Context, verbose: bool, json: bool):
    """Display version information about the application."""
    logger = ctx.obj['logger']
    
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
            
            if verbose:
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
        else:
            # Text output
            click.echo(f"{app_name} v{version}")
            
            if verbose:
                click.echo(f"\nDescription: {description}")
                click.echo(f"Python: {sys.version.split()[0]}")
                click.echo(f"Platform: {platform.platform()}")
                
                click.echo("\nDependencies:")
                for dep in ["click", "pytest", "pylint"]:
                    click.echo(f"  • {dep}: {get_package_version(dep)}")
                
                click.echo(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        logger.info(f"Version command executed (verbose={verbose})")
    except Exception as e:
        error_msg = f"Error retrieving version information: {str(e)}"
        click.echo(error_msg, err=True)
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