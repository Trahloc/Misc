"""Tests related to the integrity and structure of __init__.py files."""

import importlib
import pkgutil
from pathlib import Path

import pytest

import zeroth_law  # Import the main package

# Define the source root relative to this test file's location might need adjustment
# Assuming tests/test_project_integrity/test_init_files.py
# and src/zeroth_law/ is the structure
SRC_ROOT = Path(__file__).parent.parent.parent / "src"


def find_packages(path: Path):
    """Finds all packages (directories with __init__.py) under a given path."""
    packages = []
    for finder, name, ispkg in pkgutil.walk_packages([str(path)]):
        if ispkg:
            # Convert path separators to dots for module name
            # Ensure finder.path is Path object before division
            finder_path = Path(finder.path) if hasattr(finder, "path") else Path(".")  # Use current dir if no path
            full_path = finder_path / name
            try:
                # Construct module name relative to src root
                relative_path = full_path.relative_to(SRC_ROOT)
                module_name = str(relative_path).replace("/", ".")
                # Prepend the top-level package name if necessary
                # This logic might need refinement based on exact structure
                if not module_name.startswith("zeroth_law"):
                    # Attempt to infer the base package from the SRC_ROOT structure
                    base_package = SRC_ROOT.parent.name  # Heuristic
                    if name != base_package:  # Avoid double package name
                        module_name = f"{base_package}.{name}"

                packages.append(module_name)
            except ValueError:
                # Handle cases where the path might not be under SRC_ROOT as expected
                # This might indicate an issue with path calculation or structure
                print(f"Warning: Could not determine relative path for {full_path}")
                pass  # Or log appropriately

    # Manually add the top-level package itself if it has an __init__.py
    if (path / "__init__.py").exists():
        # Get the package name from the directory name
        top_level_package_name = path.name
        # Find the actual top-level package (e.g., 'zeroth_law') based on the imported module
        if hasattr(zeroth_law, "__name__"):
            top_level_package_name = zeroth_law.__name__
        if top_level_package_name not in packages:
            packages.append(top_level_package_name)

    # Filter out potential duplicates or invalid names
    # Example: if src is adjacent to tests, SRC_ROOT.parent.name might be 'Misc'
    # Need to ensure we are getting python package names relative to src/
    # Let's refine based on the actual src structure. Assume src/zeroth_law/ is the base.
    zerolaw_src_root = SRC_ROOT / "zeroth_law"
    packages = []
    for finder, name, ispkg in pkgutil.walk_packages([str(zerolaw_src_root)], prefix="zeroth_law."):
        if ispkg:
            packages.append(name)

    # Add the top-level zeroth_law package itself
    if "zeroth_law" not in packages:
        packages.insert(0, "zeroth_law")  # Add top level

    return packages


# Discover packages dynamically
# Adjust the path to your actual source code root containing the 'zeroth_law' package
discovered_packages = find_packages(SRC_ROOT)


@pytest.mark.parametrize("package_name", discovered_packages)
def test_package_is_importable(package_name: str):
    """Test that all discovered packages can be imported."""
    try:
        importlib.import_module(package_name)
    except ImportError as e:
        pytest.fail(f"Failed to import package {package_name}: {e}")


def test_placeholder_for_init_checks():
    """Placeholder test for future __init__.py specific checks."""
    # Add checks here, e.g., verifying __all__ lists,
    # checking for specific initialization patterns, etc.
    assert True
