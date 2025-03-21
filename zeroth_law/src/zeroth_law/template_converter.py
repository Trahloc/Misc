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
 - os
"""
import os
import re
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
    """Replace project name with cookiecutter variable in file contents."""
    # Handle cases where project name is part of a larger string
    pattern = re.compile(f"({project_name})(\\.|\\s|\"|'|/|$)")
    content = pattern.sub(r"{{ cookiecutter.project_name }}\2", content)

    # Special cases for placeholder text
    content = content.replace("project_head", "{{ cookiecutter.project_name }}")
    content = content.replace("project_module", "{{ cookiecutter.project_name }}")

    return content

def _replace_paths(path: str, project_name: str) -> str:
    """Replace project name in paths and filenames with cookiecutter variable."""
    pattern = re.compile(f"({project_name})")
    return pattern.sub("{{cookiecutter.project_name}}", path)

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

    # Skip empty or duplicate directories that would be created by the old project structure
    if any(p.name == project_name and p.parent.name == "src" for p in dest.parents):
        # If this would create a file in src/project_name when we already have src/{{cookiecutter.project_name}}
        return

    # Ensure all parent directories are created with proper naming
    for parent in dest.parents:
        if str(parent).endswith(project_name):
            new_parent = Path(str(parent).replace(project_name, "{{cookiecutter.project_name}}"))
            if not new_parent.exists():
                new_parent.mkdir(parents=True, exist_ok=True)
        elif not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

    # Special handling for ZerothLawAIFramework.py.md
    if src.name == "ZerothLawAIFramework.py.md":
        try:
            # Calculate the project root by finding the first parent that has a docs directory
            current = Path(__file__).resolve()
            while current.parent != current:  # Stop at filesystem root
                if (current / "docs" / "ZerothLawAIFramework.py.md").exists():
                    framework_doc = current / "docs" / "ZerothLawAIFramework.py.md"
                    # Create relative symlink - calculate the relative path from dest to framework_doc
                    rel_path = os.path.relpath(framework_doc, dest.parent)
                    # Remove existing file/link if it exists (needed for symlink creation)
                    if dest.exists() or dest.is_symlink():
                        dest.unlink()
                    dest.symlink_to(rel_path)
                    logger.debug("Created symlink for ZerothLawAIFramework.py.md")
                    return
                current = current.parent

            logger.warning("Main ZerothLawAIFramework.py.md not found in any parent directory with docs/, falling back to file copy")
        except (OSError, RuntimeError) as e:
            logger.warning("Failed to create symlink for ZerothLawAIFramework.py.md: %s, falling back to file copy", str(e))

    # Try to read as text first - this will naturally handle both text and binary files
    try:
        content = src.read_text(encoding='utf-8')
        # If we can read it as text, process it for template variables
        content = _replace_project_name(content, project_name)
        dest.write_text(content, encoding='utf-8')
    except UnicodeDecodeError:
        # If we can't read it as text, copy as binary
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

        # First collect all files that need to be processed
        source_files = []
        logger.debug("Source project structure:")
        for src_path in source_path.rglob("*"):
            if src_path.is_file():
                rel_path = src_path.relative_to(source_path)
                dest_path = template_project_dir / rel_path
                processed_dest = Path(_replace_paths(str(dest_path), project_name))
                # Skip files that would end up in unwanted directories
                if not any(p.name == project_name and p.parent.name == "src" for p in processed_dest.parents):
                    source_files.append((src_path, processed_dest))
                    logger.debug("  Found source file: %s -> %s", rel_path, processed_dest.relative_to(template_dir))

        # Process each file, creating only the directories we need
        for src_path, dest_path in source_files:
            # Create parent directories if they don't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            # Process the file
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