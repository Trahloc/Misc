# tests/test_project_config/test_dependency_consistency.py
import pytest
import yaml
import re
from pathlib import Path
import sys

# Assuming tests run from the workspace root or have access to it
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.resolve()
MANAGED_TOOLS_YAML = WORKSPACE_ROOT / "src" / "zeroth_law" / "managed_tools.yaml"
PYPROJECT_TOML = WORKSPACE_ROOT / "pyproject.toml"


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
    """Extracts main and dev dependency names from pyproject.toml."""
    if not toml_path.is_file():
        pytest.fail(f"pyproject.toml not found at {toml_path}")
    try:
        content = toml_path.read_text(encoding="utf-8")
        main_dependencies = set()
        dev_dependencies = set()
        dependencies = set()  # Combined set

        # --- Parse [project].dependencies --- #
        project_section_match = re.search(
            r"^\[project\](?:\s*\n)?.*?dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL | re.MULTILINE | re.IGNORECASE
        )
        if project_section_match:
            deps_str = project_section_match.group(1)
            pattern = r"^\s*['\"]?([a-zA-Z0-9._-]+)(?:\[.*?\])?(?:[<>=!~^].*)?['\"]?,?\s*$"
            for line in deps_str.splitlines():
                match = re.match(pattern, line.strip())
                if match:
                    main_dependencies.add(match.group(1))

        # --- Parse [project.optional-dependencies].dev --- #
        # Find the optional-dependencies section first
        # Corrected regex: Look for section header, capture content until next section or EOF
        optional_deps_section_match = re.search(
            # Match section header, allow spaces/newlines
            r"^\s*\[project\.optional-dependencies\]\s*\n"
            # Capture everything until next section header or end of string
            r"(.*?)"
            r"(?:\n\s*^\[|$)",
            content,
            re.DOTALL | re.MULTILINE | re.IGNORECASE,
        )
        if optional_deps_section_match:
            optional_deps_content = optional_deps_section_match.group(1)
            # Now find the dev list within that section
            # Corrected regex: Look for dev =, capture items in brackets
            dev_deps_match = re.search(
                # Match 'dev =', allow spaces/newlines, capture bracket content
                r"^\s*dev\s*=\s*\[(.*?)\]",
                optional_deps_content,
                re.DOTALL | re.MULTILINE | re.IGNORECASE,
            )
            if dev_deps_match:
                dev_deps_str = dev_deps_match.group(1)
                # Use the same pattern as for main dependencies
                pattern = r"^\s*['\"]?([a-zA-Z0-9._-]+)(?:\[.*?\])?(?:[<>=!~^].*)?['\"]?,?\s*$"
                for line in dev_deps_str.splitlines():
                    match = re.match(pattern, line.strip())
                    if match:
                        dev_dependencies.add(match.group(1))

        # --- Combine Dependencies --- #
        dependencies = main_dependencies.union(dev_dependencies)

        # --- Poetry Fallback (If needed, less likely with PEP 621 focus) --- #
        if not dependencies:  # Only try Poetry if PEP 621 parsing yielded nothing
            # Reset sets
            main_dependencies = set()
            dev_dependencies = set()

            # Poetry main dependencies
            poetry_main_match = re.search(
                r"\[tool\.poetry\.dependencies\](.*?)(\n\[|$)", content, re.DOTALL | re.IGNORECASE
            )
            if poetry_main_match:
                deps_str = poetry_main_match.group(1)
                pattern = r"^\s*([a-zA-Z0-9._-]+)\s*="
                main_dependencies = set(re.findall(pattern, deps_str, re.MULTILINE))
                python_match = re.search(r"^\s*python\s*=", deps_str, re.MULTILINE | re.IGNORECASE)
                if python_match:
                    main_dependencies.add("python")

            # Poetry dev dependencies
            poetry_dev_match = re.search(
                r"\[tool\.poetry\.group\.dev\.dependencies\](.*?)(\n\[|$)", content, re.DOTALL | re.IGNORECASE
            )
            # Alternative Poetry dev group syntax (older)
            if not poetry_dev_match:
                poetry_dev_match = re.search(
                    r"\[tool\.poetry\.dev-dependencies\](.*?)(\n\[|$)", content, re.DOTALL | re.IGNORECASE
                )

            if poetry_dev_match:
                dev_deps_str = poetry_dev_match.group(1)
                pattern = r"^\s*([a-zA-Z0-9._-]+)\s*="
                dev_dependencies = set(re.findall(pattern, dev_deps_str, re.MULTILINE))

            dependencies = main_dependencies.union(dev_dependencies)

        if not dependencies:
            print(
                f"Warning: Could not find or parse dependencies under [project.dependencies], [project.optional-dependencies.dev], or Poetry sections in {toml_path}",
                file=sys.stderr,
            )

        return dependencies

    except Exception as e:
        pytest.fail(f"Error reading or parsing {toml_path}: {e}")
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
