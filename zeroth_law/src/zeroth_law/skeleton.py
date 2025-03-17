# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/skeleton.py (CORRECTED)
"""
# PURPOSE: Create a project skeleton following the Zeroth Law.

## INTERFACES:
 - create_skeleton(directory: str): Creates project directories and files

## DEPENDENCIES:
 - os
 - logging
 - zeroth_law.config
"""
import os
import logging

from zeroth_law.config import DEFAULT_CONFIG # Import correctly

logger = logging.getLogger(__name__)

def create_skeleton(directory: str):
    """Creates a skeleton directory structure following Zeroth Law."""
    if os.path.exists(directory):
        raise FileExistsError(f"Directory already exists: {directory}")

    os.makedirs(directory)
    os.makedirs(os.path.join(directory, "src", directory)) #For package
    os.makedirs(os.path.join(directory, "tests")) #For tests

    # Create __init__.py
    create_file_from_template(directory, "__init__.py")
    # Create an example .py file
    create_file_from_template(directory, "example_module.py")
    # Create __main__.py
    create_file_from_template(directory, "__main__.py")
  # Create cli.py
    create_file_from_template(directory, "cli.py")
    # Create cli_args.py
    create_file_from_template(directory, "cli_args.py")
    # Create exceptions.py
    create_file_from_template(directory, "exceptions.py")
    # Create pyproject.toml
    create_file_from_template(directory, "pyproject.toml", os.path.join(directory, "pyproject.toml"))
    # Create a README.md file
    create_file_from_template(directory, "README.md", os.path.join(directory, "README.md"))
     # Create test __init__.py
    create_file_from_template(directory, "tests/__init__.py", os.path.join(directory,"tests", "__init__.py"))
     # Create an example test file.
    create_file_from_template(directory, "tests/test_example_module.py", os.path.join(directory,"tests", "test_example_module.py"))
      # Create .pre-commit-config.yaml file
    create_file_from_template(directory, ".pre-commit-config.yaml", os.path.join(directory, ".pre-commit-config.yaml"))
    # Create config.py file
    create_file_from_template(directory, "config.py")


    logger.info(f"Created Zeroth Law skeleton in: {directory}")

def create_file_from_template(directory: str, template_name: str, destination_path: str = None):
    """
    Creates a file in the skeleton directory based on a template.

    Args:
        directory: name of the package
        template_name: The name of the template file (without the .template extension)
        destination_path: Where to put the file.
    """
    template_path = os.path.join(
        os.path.dirname(__file__), "templates", template_name + ".template"
    )
    if destination_path is None: #Default, put it in the src
        destination_path = os.path.join(directory, "src", directory, template_name)

    # Load template
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    #Substitute
    formatted_content = template_content.format(directory=directory, default_config=DEFAULT_CONFIG) # Pass default config

    #Create file
    with open(destination_path, "w", encoding="utf-8") as f:
        f.write(formatted_content)