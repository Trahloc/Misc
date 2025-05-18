# tests/test_project_config/test_dependency_consistency.py
import pytest
import yaml
import re
from pathlib import Path
import sys
import tomllib  # Import tomllib

# Assuming tests run from the workspace root or have access to it
# Calculate project root relative to the new location
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"
# Correct path to managed_tools.yaml within the src directory
MANAGED_TOOLS_YAML = PROJECT_ROOT / "src" / "zeroth_law" / "managed_tools.yaml"


def load_managed_tools_from_yaml(yaml_path: Path) -> set[str]:
    """Loads the list of managed tool names from the YAML config."""
    if not yaml_path.is_file():
        pytest.fail(f"Managed tools file not found at {yaml_path}")
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        managed = data.get("managed_tools", [])
        if not isinstance(managed, list):
            pytest.fail(f"Error: 'managed_tools' key in {yaml_path} is not a list.")
        # Clean up names (remove comments, whitespace) just in case
        cleaned_names = {str(tool).split("#")[0].strip() for tool in managed if str(tool).split("#")[0].strip()}
        return cleaned_names
    except yaml.YAMLError as e:
        pytest.fail(f"Error parsing YAML file {yaml_path}: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error loading {yaml_path}: {e}")
    return set()  # Should not be reached due to pytest.fail


def get_main_and_dev_dependencies_from_toml(toml_path: Path) -> set[str]:
    """Extracts main and dev dependency names from pyproject.toml using tomllib."""
    if not toml_path.is_file():
        pytest.fail(f"pyproject.toml not found at {toml_path}")
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)

        dependencies = set()

        # Extract main dependencies
        main_deps_list = data.get("project", {}).get("dependencies", [])
        if isinstance(main_deps_list, list):
            # Regex to extract base package name
            pattern = r"^\s*([a-zA-Z0-9._-]+)"
            for dep_str in main_deps_list:
                match = re.match(pattern, dep_str.strip())  # Match against stripped string
                if match:
                    dependencies.add(match.group(1))
        else:
            print(
                f"Warning: [project].dependencies in {toml_path} is not a list.",
                file=sys.stderr,
            )

        # Extract dev dependencies
        dev_deps_list = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
        if isinstance(dev_deps_list, list):
            # Use the same simpler pattern
            pattern = r"^\s*([a-zA-Z0-9._-]+)"
            for dep_str in dev_deps_list:
                match = re.match(pattern, dep_str.strip())  # Match against stripped string
                if match:
                    dependencies.add(match.group(1))
        else:
            print(
                f"Warning: [project.optional-dependencies].dev in {toml_path} is not a list.",
                file=sys.stderr,
            )

        if not dependencies:
            print(
                f"Warning: No dependencies found under [project.dependencies] or [project.optional-dependencies.dev] in {toml_path}",
                file=sys.stderr,
            )

        return dependencies

    except tomllib.TOMLDecodeError as e:
        pytest.fail(f"Error parsing TOML file {toml_path}: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error reading or parsing {toml_path}: {e}")
    return set()


def test_managed_tools_are_main_dependencies():
    """
    Verify that all tools listed in managed_tools.yaml are actual project
    dependencies declared in pyproject.toml (main or dev group).
    """
    managed_tools = load_managed_tools_from_yaml(MANAGED_TOOLS_YAML)
    project_dependencies = get_main_and_dev_dependencies_from_toml(PYPROJECT_TOML)

    if not managed_tools:
        pytest.skip("No managed tools found to check.")

    # Normalize package names by replacing underscores with hyphens
    normalized_project_deps = {dep.lower().replace("_", "-") for dep in project_dependencies}

    # --- Add mapping for executables provided by other packages --- #
    # Key: executable name (from managed_tools.yaml), Value: package name (in pyproject.toml)
    executable_to_package_map = {
        "bandit-baseline": "bandit",
        "bandit-config-generator": "bandit",
        "isort-identify-imports": "isort",
        "pyproject-build": "build",
        # Add more mappings here if other tools provide multiple executables
    }
    # --- End Mapping --- #

    missing_deps = set()
    for tool in managed_tools:
        normalized_tool = tool.lower().replace("_", "-")

        # Skip self, python, and known entry points
        if normalized_tool in ["zeroth-law", "python", "zlt"]:
            continue

        # Check if the tool maps to a known package or exists directly
        required_package = executable_to_package_map.get(normalized_tool, normalized_tool)

        if required_package not in normalized_project_deps:
            missing_deps.add(tool)  # Report original tool name from yaml

    if missing_deps:
        missing_list = "\n - ".join(sorted(list(missing_deps)))
        fail_message = (
            f"The following tools listed in {MANAGED_TOOLS_YAML.name} require packages missing from "
            f"the main or dev project dependencies in {PYPROJECT_TOML.name} ([project].dependencies or [project.optional-dependencies].dev):\n"
            f" - {missing_list}\n"
            f"Please ensure the corresponding packages are added to the project's dependencies."
        )
        pytest.fail(fail_message)
