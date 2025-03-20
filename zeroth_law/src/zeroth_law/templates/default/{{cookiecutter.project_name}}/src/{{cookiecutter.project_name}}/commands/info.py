"""
# PURPOSE: Implements the info command to display project information

## INTERFACES:
 - command(details: bool, json: bool): Displays project information

## DEPENDENCIES:
 - click: Command-line interface creation
 - zeroth_law_template.config: Configuration management
"""
import sys
import click
import json as json_lib
from datetime import datetime

from {{ cookiecutter.project_name }}.config import get_config

@click.command(name="info")
@click.option("--details", is_flag=True, help="Display detailed information about the project.")
@click.option("--json", is_flag=True, help="Output information in JSON format.")
@click.pass_context
def command(ctx: click.Context, details: bool, json: bool):
    """Display information about this project."""
    logger = ctx.obj['logger']

    try:
        # Get information from config
        config = get_config()
        
        # Basic project info
        project_info = {
            "name": config.app.name,
            "version": config.app.version,
            "description": config.app.description,
        }
        
        # Add detailed info if requested
        if details:
            project_info.update({
                "logging": {
                    "level": config.logging.level,
                    "format": config.logging.format,
                },
                "paths": {
                    "data_dir": config.paths.data_dir,
                    "output_dir": config.paths.output_dir,
                    "cache_dir": config.paths.cache_dir,
                },
                "timestamp": datetime.now().isoformat(),
            })
            
            # Add any custom sections from config 
            # (these would be project-specific in a real project)
            if hasattr(config, 'project'):
                project_info["project"] = config.project.to_dict()
        
        # Output in JSON format if requested
        if json:
            click.echo(json_lib.dumps(project_info, indent=2))
        else:
            # Text output
            click.echo(f"Project: {project_info['name']} v{project_info['version']}")
            click.echo(f"Description: {project_info['description']}")
            
            if details:
                click.echo("\nLogging Configuration:")
                click.echo(f"  • Level: {project_info['logging']['level']}")
                
                click.echo("\nPaths:")
                for name, path in project_info['paths'].items():
                    click.echo(f"  • {name}: {path}")
                
                # Display any additional project-specific info
                if "project" in project_info:
                    click.echo("\nProject-specific information:")
                    for key, value in project_info["project"].items():
                        click.echo(f"  • {key}: {value}")
                
                click.echo(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        logger.info(f"Info command executed (details={details})")
    except Exception as e:
        error_msg = f"Error displaying project info: {str(e)}"
        click.echo(error_msg, err=True)
        logger.error(error_msg)
        ctx.exit(1)

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Now loads information from the configuration file
 - Added JSON output option
 - Displays more comprehensive project information
 - Added timestamp for detailed information

## FUTURE TODOs:
 - Add support for displaying environment variables affecting configuration
 - Add system information (similar to the version command)
"""
