"""
# PURPOSE: Implements the info command to display project information

## INTERFACES:
 - command(details: bool): Displays project information

## DEPENDENCIES:
 - click: Command-line interface creation
"""
import click

@click.command()
@click.option("--details", is_flag=True, help="Display detailed information about the project.")
@click.pass_context
def command(ctx: click.Context, details: bool):
    """Display information about this project."""
    logger = ctx.obj['logger']

    try:
        project_info = {
            "name": "{{ cookiecutter.project_name }}",
            "version": "0.1.0",
            "description": "A project created with the Zeroth Law AI Framework"
        }

        click.echo(f"Project: {project_info['name']} v{project_info['version']}")

        if details:
            click.echo(f"Description: {project_info['description']}")
            click.echo("Created using the Zeroth Law AI Framework")
            logger.debug("Displayed detailed project information")

        logger.info("Project info command completed")
    except Exception as e:
        logger.error(f"Error displaying project info: {str(e)}")
        ctx.exit(1)

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added proper error handling
 - Added documentation sections
 - Isolated project information display logic

## FUTURE TODOs:
 - Add more project metadata
 - Consider loading info from configuration file
"""
