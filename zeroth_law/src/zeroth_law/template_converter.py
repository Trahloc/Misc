"""
# PURPOSE: Convert an existing project into a cookiecutter template

## INTERFACES:
 - convert_to_template(source_dir: str, template_name: str): Converts a project into a cookiecutter template

## DEPENDENCIES:
 - shutil
 - logging
 - json
 - pathlib
 - datetime
"""
import shutil
import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

def _create_cookiecutter_json(template_dir: Path, project_name: str) -> None:
    """Create the cookiecutter.json configuration file."""
    config = {
        "project_name": project_name,
        "project_short_description": "A Python project using the Zeroth Law framework",
        "author_name": "Your Name",
        "author_email": "your.email@example.com",
        "_copy_without_render": [
            "*.template"
        ]
    }

    with open(template_dir / "cookiecutter.json", "w", encoding='utf-8') as f:
        json.dump(config, f, indent=2)

def _replace_project_name(content: str, project_name: str) -> str:
    """Replace the project name with cookiecutter variable."""
    # First replace any direct project name references
    content = content.replace(f'"{project_name}"', '"{{ cookiecutter.project_name }}"')
    content = content.replace(f"'{project_name}'", "'{{ cookiecutter.project_name }}'")

    # Replace common patterns in imports and module references
    content = content.replace(f"from {project_name}", "from {{ cookiecutter.project_name }}")
    content = content.replace(f"import {project_name}", "import {{ cookiecutter.project_name }}")
    content = content.replace(f"from . import {project_name}", "from . import {{ cookiecutter.project_name }}")

    # Replace in docstrings and comments
    content = content.replace(f"for the {project_name}", "for the {{ cookiecutter.project_name }}")
    content = content.replace(f"the {project_name} package", "the {{ cookiecutter.project_name }} package")
    content = content.replace(f"the {project_name} module", "the {{ cookiecutter.project_name }} module")

    # Replace in file headers and paths
    content = content.replace(f"# FILE_LOCATION: {project_name}/", "# FILE_LOCATION: {{ cookiecutter.project_name }}/")
    content = content.replace(f"## PURPOSE: Provides a basic overview and usage instructions for the {project_name} package",
                            "## PURPOSE: Provides a basic overview and usage instructions for the {{ cookiecutter.project_name }} package")

    # Replace in configuration and logging
    content = content.replace(f"name = \"{project_name}\"", "name = \"{{ cookiecutter.project_name }}\"")
    content = content.replace(f"logging.getLogger('{project_name}')", "logging.getLogger('{{ cookiecutter.project_name }}')")
    content = content.replace(f"{project_name}/src/{project_name}", "{{ cookiecutter.project_name }}/src/{{ cookiecutter.project_name }}")
    content = content.replace(f"{project_name}.commands", "{{ cookiecutter.project_name }}.commands")

    return content

def _replace_paths(path: str, project_name: str) -> str:
    """Replace project name in paths with cookiecutter variable."""
    parts = path.split('/')
    for i, part in enumerate(parts):
        if part == project_name:
            parts[i] = "{{cookiecutter.project_name}}"
    return '/'.join(parts)

def _process_file(src: Path, dest: Path, project_name: str) -> None:
    """Process a single file, replacing project-specific values with template variables."""
    if not src.is_file():
        return

    # Skip certain files and directories
    skip_patterns = {'.git', '.pytest_cache', '__pycache__', '*.pyc', '*.egg-info'}
    if any(pattern in str(src) for pattern in skip_patterns):
        return

    # Get the relative path with cookiecutter variable for both the file and its parent directories
    dest = Path(_replace_paths(str(dest), project_name))

    # Ensure all parent directories are created with proper naming
    for parent in dest.parents:
        if str(parent).endswith(project_name):
            new_parent = Path(str(parent).replace(project_name, "{{cookiecutter.project_name}}"))
            if not new_parent.exists():
                new_parent.mkdir(parents=True, exist_ok=True)
        elif not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

    # Copy the file content
    if src.suffix in {'.py', '.md', '.txt', '.toml', '.yaml', '.yml', '.ini'}:
        # Process text files
        content = src.read_text(encoding='utf-8')
        # Replace project name with template variable
        content = _replace_project_name(content, project_name)
        dest.write_text(content, encoding='utf-8')
    else:
        # Binary copy for other files
        shutil.copy2(src, dest)

def convert_to_template(source_dir: str, template_name: str = "test_zeroth_law", overwrite: bool = False) -> None:
    """
    Convert an existing project into a cookiecutter template.

    Args:
        source_dir: Path to the source project directory
        template_name: Name for the template project (default: test_zeroth_law)
        overwrite: Whether to overwrite an existing template (default: False)

    Raises:
        FileNotFoundError: If source directory doesn't exist
        FileExistsError: If template directory already exists and overwrite=False
        ValueError: If template creation fails
    """
    source_path = Path(source_dir).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    # Get the project name from the source directory
    project_name = source_path.name
    logger.debug("Converting project %s to template %s", project_name, template_name)

    # Create template directory
    templates_dir = Path(__file__).parent / "templates"
    if not templates_dir.exists():
        templates_dir.mkdir()

    template_dir = templates_dir / template_name
    logger.debug("Template directory will be: %s", template_dir)

    if template_dir.exists():
        if not overwrite:
            raise FileExistsError(f"Template directory already exists: {template_name}")
        # Backup existing template before removal
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{template_dir}.{timestamp}"
        logger.debug("Backing up existing template directory to: %s", backup_path)
        shutil.move(template_dir, backup_path)

    try:
        # Create the template structure
        template_project_dir = template_dir / "{{cookiecutter.project_name}}"
        template_project_dir.mkdir(parents=True)
        logger.debug("Created template project directory: %s", template_project_dir)

        # Create cookiecutter.json
        _create_cookiecutter_json(template_dir, project_name)

        # Copy and process all files
        logger.debug("Source project structure:")
        for src_path in source_path.rglob("*"):
            if src_path.is_file():
                logger.debug("  Found source file: %s", src_path.relative_to(source_path))

        for src_path in source_path.rglob("*"):
            # Calculate relative path from source root
            rel_path = src_path.relative_to(source_path)
            dest_path = template_project_dir / rel_path

            if src_path.is_dir():
                logger.debug("Creating directory: %s", dest_path)
                dest_path.mkdir(parents=True, exist_ok=True)
            elif src_path.is_file():
                logger.debug("Processing file: %s -> %s", src_path, dest_path)
                _process_file(src_path, dest_path, project_name)

        logger.info("Successfully created template in %s", template_dir)
        logger.debug("Final template structure:")
        for path in template_project_dir.rglob("*"):
            if path.is_file():
                logger.debug("  %s", path.relative_to(template_dir))

    except Exception as e:
        # Clean up if anything goes wrong
        if template_dir.exists():
            shutil.rmtree(template_dir)
        raise ValueError(f"Failed to create template: {str(e)}") from e