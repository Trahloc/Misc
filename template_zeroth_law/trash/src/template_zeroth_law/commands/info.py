"""
# PURPOSE: Implements project information command for displaying configuration details

## INTERFACES:
 - command(): Display project information
 - get_config(): Get configuration from file or default values

## DEPENDENCIES:
 - click: Command-line interface creation
 - pathlib: Path manipulation
 - template_zeroth_law.utils: Utility functions
"""

import sys
import click
import platform
from pathlib import Path
from typing import Dict, Any, Optional
import json

from template_zeroth_law.utils import get_project_root, merge_dicts

DEFAULT_CONFIG = {
    "app": {
        "name": "template_zeroth_law",
        "version": "0.1.0",
        "description": "A universal Python project template following the Zeroth Law AI Framework",
        "debug": False,
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "log_file": None,
    },
    "paths": {
        "data_dir": "data",
        "output_dir": "output",
        "cache_dir": ".cache",
        "temp_dir": "tmp",
        "config_dir": "config",
    },
    "project": {
        "author": "",
        "repository": "",
    },
}


def get_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get configuration from file or default values.

    Args:
        config_path: Path to configuration file. If None, tries to find it automatically.

    Returns:
        Dictionary with configuration
    """
    project_root = get_project_root()

    # If no config path provided, look for standard config files
    if config_path is None:
        # Try to find config file in standard locations
        config_locations = [
            project_root / "template_zeroth_law.json",
            project_root / "config" / "template_zeroth_law.json",
            project_root / ".template_zeroth_law" / "config.json",
        ]

        for path in config_locations:
            if path.exists():
                config_path = path
                break

    config = DEFAULT_CONFIG.copy()

    # Load config from file if it exists
    if config_path and config_path.exists():
        try:
            with open(config_path, "r") as f:
                file_config = json.load(f)
                config = merge_dicts(config, file_config)
        except (json.JSONDecodeError, IOError) as e:
            click.echo(f"Error loading configuration from {config_path}: {e}", err=True)

    return config


@click.command("info")
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
@click.option("--details", is_flag=True, help="Show detailed information")
@click.pass_context
def command(ctx, config: Optional[str] = None, details: bool = False) -> None:
    """
    PURPOSE: Display project information from configuration.
    CONTEXT: CLI command for project info display
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS:
        config (str): Optional path to configuration file
        details (bool): Show detailed information
    POST-CONDITIONS & GUARANTEES: Project information is displayed
    RETURNS: None
    EXCEPTIONS: None
    USAGE EXAMPLES:
        $ python -m template_zeroth_law info
        $ python -m template_zeroth_law info --config=my_config.json
        $ python -m template_zeroth_law info --details
    """
    logger = ctx.obj.get("logger") if ctx.obj else None

    if logger:
        logger.info("Displaying project information")

    # Get configuration
    config_path = Path(config) if config else None
    try:
        config_data = get_config(config_path)
    except Exception as e:
        click.echo(f"Error getting configuration: {e}", err=True)
        sys.exit(1)

    # Display project information
    click.echo("\n🔍 Project Information:")

    # App info
    app_info = config_data.get("app", {})
    click.echo("\n📦 Application:")
    click.echo(f"  Name: {app_info.get('name', 'Unknown')}")
    click.echo(f"  Version: {app_info.get('version', 'Unknown')}")
    click.echo(f"  Description: {app_info.get('description', 'No description')}")

    # Debug info (only shown with --details)
    if details:
        click.echo(f"  Debug mode: {app_info.get('debug', False)}")

    # Project info
    project_info = config_data.get("project", {})
    click.echo("\n🧩 Project Details:")
    click.echo(f"  Author: {project_info.get('author', 'Unknown')}")
    click.echo(f"  Repository: {project_info.get('repository', 'Not specified')}")

    # Paths
    paths_info = config_data.get("paths", {})
    click.echo("\n📁 Paths:")
    for key, value in paths_info.items():
        click.echo(f"  {key}: {value}")

    # System info
    click.echo("\n💻 System:")
    click.echo(f"  Python: {platform.python_version()}")
    click.echo(f"  Platform: {platform.system()} {platform.release()}")

    # Additional system info with details flag
    if details:
        click.echo(f"  Python implementation: {platform.python_implementation()}")
        click.echo(f"  CPU architecture: {platform.machine()}")
        click.echo(f"  Full platform info: {platform.platform()}")

        # Logging settings
        logging_info = config_data.get("logging", {})
        click.echo("\n📝 Logging:")
        click.echo(f"  Level: {logging_info.get('level', 'INFO')}")
        click.echo(f"  Format: {logging_info.get('format', 'Default format')}")
        click.echo(f"  Log file: {logging_info.get('log_file', 'None (console only)')}")

    click.echo("\n✅ Info command complete.")


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added get_config utility function
 - Added detailed project info display
 - Added configuration file support
 - Added system information
 - Added --details flag for more comprehensive information

## FUTURE TODOs:
 - Add support for more configuration formats (TOML, YAML)
 - Add more detailed system information
 - Add dependency information
"""
