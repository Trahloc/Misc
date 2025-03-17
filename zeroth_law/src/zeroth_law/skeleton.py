# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/skeleton.py (CORRECTED)
"""
# PURPOSE: Create a project skeleton following the Zeroth Law.

## INTERFACES:
 - create_skeleton(directory: str): Creates project directories and files

## DEPENDENCIES:
 - os
 - logging
 - cookiecutter.main
 - zeroth_law.config
"""
import os
import logging
from cookiecutter.main import cookiecutter
from zeroth_law.config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

def create_skeleton(directory: str):
    """Creates a skeleton directory structure following Zeroth Law using cookiecutter."""
    if os.path.exists(directory):
        raise FileExistsError(f"Directory already exists: {directory}")

    # Get the path to the cookiecutter template directory
    template_dir = os.path.join(os.path.dirname(__file__), "cookiecutter-template")

    # Create context with variables for the template
    context = {
        "project_name": directory,
        "default_config": DEFAULT_CONFIG
    }

    # Use cookiecutter to create project from template
    logger.info(f"Creating Zeroth Law skeleton in: {directory}")
    cookiecutter(
        template_dir,
        extra_context=context,
        no_input=True,
        output_dir=os.path.dirname(os.path.abspath(directory))
    )

    logger.info(f"Created Zeroth Law skeleton in: {directory}")

# The create_file_from_template function is no longer needed as cookiecutter handles this