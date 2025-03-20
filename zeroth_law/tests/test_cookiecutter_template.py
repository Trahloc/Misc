"""
# PURPOSE: Tests for cookiecutter template generation.

## INTERFACES:
 - All test functions

## DEPENDENCIES:
 - pytest
 - pathlib
 - shutil
 - json
"""
import shutil
import json
import pytest
from pathlib import Path

from zeroth_law import skeleton
from zeroth_law.skeleton import create_skeleton, DEFAULT_CONFIG
from zeroth_law.template_converter import convert_to_template

@pytest.fixture(name="project_dir")
def project_dir_fixture(tmp_path):
    """Create a temporary directory for testing."""
    yield tmp_path
    # Cleanup after tests
    if tmp_path.exists():
        shutil.rmtree(tmp_path)

@pytest.fixture(autouse=True)
def cleanup_templates():
    """Clean up test templates after each test."""
    yield
    templates_dir = Path(__file__).parent.parent / "src" / "zeroth_law" / "templates"
    if templates_dir.exists():
        # Only remove test templates, not the default one
        test_templates = ["test_template", "custom_template"]
        for template in test_templates:
            template_path = templates_dir / template
            if template_path.exists():
                shutil.rmtree(template_path)

def test_template_generation(project_dir):
    """Test basic template generation with create_skeleton."""
    project_name = "test_project"
    project_path = project_dir / project_name

    # Create the project
    create_skeleton(str(project_path))

    # Basic structure checks
    assert project_path.exists()
    assert (project_path / "src" / project_name).exists()
    assert (project_path / "tests").exists()
    assert (project_path / "pyproject.toml").exists()
    assert (project_path / "README.md").exists()

def test_template_content(project_dir):
    """Test that generated files contain correct content."""
    project_name = "test_content_project"
    project_path = project_dir / project_name

    # Create the project
    create_skeleton(str(project_path))

    # Check main package init
    init_path = project_path / "src" / project_name / "__init__.py"
    assert init_path.exists()
    content = init_path.read_text()
    assert "PURPOSE: Exposes the public API" in content
    assert "greet_user" in content

    # Check CLI file
    cli_path = project_path / "src" / project_name / "cli.py"
    assert cli_path.exists()
    content = cli_path.read_text()
    assert "@click.group()" in content
    assert "main.add_command(hello.command)" in content

    # Check pyproject.toml
    pyproject_path = project_path / "pyproject.toml"
    assert pyproject_path.exists()
    content = pyproject_path.read_text()
    assert f'name = "{project_name}"' in content
    assert 'click' in content  # Check dependencies

def test_template_structure(project_dir):
    """Test that the generated project has the correct directory structure."""
    project_name = "test_structure_project"
    project_path = project_dir / project_name

    # Create the project
    create_skeleton(str(project_path))

    # Check directory structure
    expected_dirs = [
        "src",
        f"src/{project_name}",
        f"src/{project_name}/commands",
        "tests",
    ]

    for dir_path in expected_dirs:
        assert (project_path / dir_path).exists()
        assert (project_path / dir_path).is_dir()

    # Check essential files
    expected_files = [
        "pyproject.toml",
        "README.md",
        "requirements.txt",
        f"src/{project_name}/__init__.py",
        f"src/{project_name}/cli.py",
        f"src/{project_name}/config.py",
        f"src/{project_name}/exceptions.py",
        f"src/{project_name}/greeter.py",
        "tests/__init__.py",
        "tests/test_cli.py",
    ]

    for file_path in expected_files:
        assert (project_path / file_path).exists()
        assert (project_path / file_path).is_file()

def test_duplicate_project_creation(project_dir):
    """Test that creating a project in an existing directory raises FileExistsError."""
    project_name = "test_duplicate_project"
    project_path = project_dir / project_name

    # Create the project first time
    create_skeleton(str(project_path))

    # Try to create it again
    with pytest.raises(FileExistsError):
        create_skeleton(str(project_path))

def test_template_variables(project_dir):
    """Test that template variables are properly substituted."""
    project_name = "variable_test_project"
    project_path = project_dir / project_name

    # Create the project
    create_skeleton(str(project_path))

    # Check main file content for variable substitution
    main_path = project_path / "src" / project_name / "__main__.py"
    content = main_path.read_text()
    assert f"from {project_name}.cli import main" in content

    # Check CLI logging configuration
    cli_path = project_path / "src" / project_name / "cli.py"
    content = cli_path.read_text()
    assert f"logging.getLogger('{project_name}')" in content

    # Check README content
    readme_path = project_path / "README.md"
    content = readme_path.read_text()
    assert f"# FILE_LOCATION: {project_name}/README.md" in content  # Check file location header
    assert f"## PURPOSE: Provides a basic overview and usage instructions for the {project_name} package." in content  # Check description
    assert f"import {project_name}" in content  # Check import example

def test_config_defaults(project_dir):
    """Test that default configuration is properly included."""
    project_name = "config_test_project"
    project_path = project_dir / project_name

    # Create the project
    create_skeleton(str(project_path))

    # Check config.py for default values
    config_path = project_path / "src" / project_name / "config.py"
    content = config_path.read_text()

    # Verify default config values are present
    for key in DEFAULT_CONFIG:
        assert str(key) in content
        if isinstance(DEFAULT_CONFIG[key], (int, float)):
            assert str(DEFAULT_CONFIG[key]) in content

def test_template_command_structure(project_dir):
    """Test that the commands directory is properly structured."""
    project_name = "command_test_project"
    project_path = project_dir / project_name

    # Create the project
    create_skeleton(str(project_path))

    # Check commands directory structure
    commands_dir = project_path / "src" / project_name / "commands"
    assert commands_dir.exists()
    assert commands_dir.is_dir()

    # Check command files
    expected_commands = ["hello.py", "info.py", "__init__.py"]
    for command in expected_commands:
        command_file = commands_dir / command
        assert command_file.exists()
        assert command_file.is_file()

        # Check content of command files
        content = command_file.read_text()
        if command == "hello.py":
            assert "def command(" in content
            # Check for click command decorator (either form is acceptable)
            assert any(decorator in content for decorator in ["@click.command()", "@click.command(name="])
        elif command == "info.py":
            assert "def command(" in content
            # Check for click command decorator (either form is acceptable)
            assert any(decorator in content for decorator in ["@click.command()", "@click.command(name="])
        elif command == "__init__.py":
            assert "from . import hello" in content
            assert "from . import info" in content

def test_development_tools_setup(project_dir):
    """Test that development tools are properly configured."""
    project_name = "dev_tools_test_project"
    project_path = project_dir / project_name

    # Create the project
    create_skeleton(str(project_path))

    # Check dev tool configurations
    assert (project_path / ".pre-commit-config.yaml").exists()
    assert (project_path / ".pylintrc").exists()
    assert (project_path / "requirements.txt").exists()

    # Check requirements.txt content
    requirements = (project_path / "requirements.txt").read_text()
    assert "pytest" in requirements
    assert "black" in requirements
    assert "flake8" in requirements
    assert "mypy" in requirements

def test_template_conversion(project_dir):
    """Test converting a project into a cookiecutter template."""
    # First create a test project
    project_name = "source_project"
    project_path = project_dir / project_name
    create_skeleton(str(project_path))

    # Now convert it to a template
    template_name = "test_template"
    convert_to_template(str(project_path), template_name)

    # Check template structure - templates are created in src/zeroth_law/templates
    templates_dir = Path(__file__).parent.parent / "src" / "zeroth_law" / "templates"
    template_dir = templates_dir / template_name
    assert template_dir.exists()
    assert (template_dir / "cookiecutter.json").exists()
    assert (template_dir / "{{cookiecutter.project_name}}").exists()

    # Check cookiecutter.json content
    with open(template_dir / "cookiecutter.json", encoding='utf-8') as f:
        config = json.load(f)
        assert "project_name" in config
        assert "project_short_description" in config
        assert "author_name" in config
        assert "author_email" in config
        assert "_copy_without_render" in config

    # Check template variables in files
    cli_path = template_dir / "{{cookiecutter.project_name}}" / "src" / "{{cookiecutter.project_name}}" / "cli.py"
    assert cli_path.exists()
    content = cli_path.read_text()
    assert "{{ cookiecutter.project_name }}" in content
    assert project_name not in content  # Original project name should be replaced

def test_template_conversion_nonexistent_source(project_dir):
    """Test that converting a non-existent project raises an error."""
    with pytest.raises(FileNotFoundError):
        convert_to_template(str(project_dir / "nonexistent"), "test_template")

def test_template_conversion_existing_target(project_dir):
    """Test that converting to an existing template directory raises an error."""
    # Create source project
    project_name = "source_project2"
    project_path = project_dir / project_name
    create_skeleton(str(project_path))

    # Create target directory to cause conflict
    template_name = "existing_template"
    template_dir = project_dir / template_name
    template_dir.mkdir()

    # Attempt conversion should fail
    with pytest.raises(FileExistsError):
        convert_to_template(str(project_path), template_name)

def test_template_selection(project_dir):
    """Test template selection and listing functionality."""
    # First create a custom template
    source_path = project_dir / "source_project"
    create_skeleton(str(source_path))  # Create a base project
    convert_to_template(str(source_path), "custom_template")

    # List templates should show our new template
    templates = skeleton.list_templates()
    assert "default" in templates  # The original template
    assert "custom_template" in templates  # Our new template

    # Create a project using the custom template
    project_path = project_dir / "from_custom"
    create_skeleton(str(project_path), "custom_template")

    # Verify it was created correctly
    assert project_path.exists()
    assert (project_path / "src").exists()
    assert (project_path / "tests").exists()

    # Try using a non-existent template
    with pytest.raises(FileNotFoundError) as exc_info:
        create_skeleton(str(project_dir / "should_fail"), "nonexistent")
    assert "Template 'nonexistent' not found" in str(exc_info.value)

def test_template_overwrite(project_dir):
    """Test that template overwrite works correctly."""
    # First create a custom template
    source_path = project_dir / "source_project"
    create_skeleton(str(source_path))  # Create a base project
    convert_to_template(str(source_path), "custom_template")

    # Create another project to test overwriting
    other_path = project_dir / "other_project"
    create_skeleton(str(other_path))

    # Without overwrite flag, should fail
    with pytest.raises(FileExistsError):
        convert_to_template(str(other_path), "custom_template")

    # With overwrite flag, should succeed
    convert_to_template(str(other_path), "custom_template", overwrite=True)

    # Template should exist and contain updated content - templates are created in src/zeroth_law/templates
    templates_dir = Path(__file__).parent.parent / "src" / "zeroth_law" / "templates"
    template_dir = templates_dir / "custom_template"
    cli_path = template_dir / "{{cookiecutter.project_name}}" / "src" / "{{cookiecutter.project_name}}" / "cli.py"
    assert cli_path.exists()
    content = cli_path.read_text()
    assert "{{ cookiecutter.project_name }}" in content
    assert "source_project" not in content  # Old project name should be gone
    assert "other_project" not in content   # New project name should be templated