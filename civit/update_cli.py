#!/usr/bin/env python3
"""
Update CLI script to install the latest CLI parser with debug flag.
This will ensure the --debug flag is properly recognized.
"""
import os
import sys
import glob
import shutil
import subprocess
from pathlib import Path


def find_package_files():
    """Find the actual civit package files"""
    try:
        # Use pip to find the installed package location
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "civit"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Extract the location from pip output
        location = None
        for line in result.stdout.splitlines():
            if line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                break

        if not location:
            print("Could not find installation location in pip output")
            return None, None

        # Search for the actual module files
        package_root = Path(location)
        print(f"Package installed at: {package_root}")

        # Try different possible locations
        possible_locations = [
            package_root / "civit",
            package_root,
            package_root / "site-packages" / "civit",
        ]

        # Look for civit.py or the civit directory
        main_file = None
        for loc in possible_locations:
            # Check for civit.py (single-file module)
            if (loc / "civit.py").exists():
                main_file = loc / "civit.py"
                break
            # Check for __main__.py (package with __main__)
            if (loc / "__main__.py").exists():
                main_file = loc / "__main__.py"
                break
            # Search for any .py files that might contain the CLI code
            py_files = list(loc.glob("*.py"))
            if py_files:
                # Look for main.py or similar files
                for file in py_files:
                    if file.name in ["main.py", "__main__.py", "cli.py", "civit.py"]:
                        main_file = file
                        break
                if main_file:
                    break
                # If no standard names found, just take the first .py file
                main_file = py_files[0]
                break

        if not main_file:
            # Last resort: search for any .py file in the package
            py_files = list(package_root.glob("**/*.py"))
            if py_files:
                print(f"Found Python files: {[f.name for f in py_files]}")
                # Look for main.py or similar files first
                for file in py_files:
                    if file.name.lower() in [
                        "main.py",
                        "__main__.py",
                        "cli.py",
                        "civit.py",
                    ]:
                        main_file = file
                        break
                # If still not found, just take the first Python file
                if not main_file and py_files:
                    main_file = py_files[0]

        if main_file:
            print(f"Found main module file: {main_file}")
            return package_root, main_file
        else:
            print("Could not find the civit module files")
            return package_root, None

    except subprocess.CalledProcessError as e:
        print(f"Error finding package: {e}")
        print(f"Output: {e.output}")
        return None, None


def analyze_module_structure(package_root):
    """Analyze the module structure to determine where to put our files"""
    if not package_root:
        return None

    # Find all Python files in the package
    py_files = list(package_root.glob("**/*.py"))
    if not py_files:
        print("No Python files found in the package")
        return None

    print(f"Found {len(py_files)} Python files in the package")
    for file in py_files:
        print(f"  {file.relative_to(package_root)}")

    # Read the content of Python files to find arg parsing logic
    cli_file = None
    main_file = None

    for file in py_files:
        try:
            with open(file, "r") as f:
                content = f.read()
                if "argparse" in content:
                    print(f"Found argparse usage in: {file}")
                    cli_file = file
                if "def main(" in content or "def parse_args(" in content:
                    print(f"Found main function in: {file}")
                    main_file = file
        except Exception as e:
            print(f"Error reading {file}: {e}")

    return {"package_root": package_root, "cli_file": cli_file, "main_file": main_file}


def update_package_cli():
    """Update the CLI implementation in the installed package"""
    # Find the installed package files
    package_root, main_file = find_package_files()
    if not main_file:
        structure = analyze_module_structure(package_root)
        if structure and structure["cli_file"]:
            main_file = structure["cli_file"]
        elif structure and structure["main_file"]:
            main_file = structure["main_file"]

    if not main_file:
        print("Could not locate the main module file to update.")
        print("Try running: pip uninstall civit && pip install -e .")
        return False

    # Source files to update
    src_dir = Path(__file__).parent / "src"
    cli_py = src_dir / "cli.py"
    main_py = src_dir / "main.py"

    if not cli_py.exists() or not main_py.exists():
        print(f"Source files not found at {src_dir}")
        return False

    # Backup the main file
    backup_file = main_file.with_name(main_file.name + ".bak")
    try:
        shutil.copy2(main_file, backup_file)
        print(f"Backed up {main_file} to {backup_file}")
    except Exception as e:
        print(f"Failed to create backup: {e}")

    # Create a new combined file with our changes
    try:
        # Read the content of our new CLI implementation
        with open(cli_py, "r") as f:
            cli_content = f.read()

        with open(main_py, "r") as f:
            main_content = f.read()

        # Read the original file
        with open(main_file, "r") as f:
            original_content = f.read()

        # Create a new combined file
        combined_content = f"""# Combined file created by update_cli.py
# Original file backed up as {backup_file.name}

# New CLI parser code:
{cli_content}

# New main function code:
{main_content}

# Original code (for reference):
'''
{original_content}
'''

# Use the new main function if this file is executed directly
if __name__ == "__main__":
    import sys
    from .main import main
    sys.exit(main())
"""

        # Write the combined content to the main file
        with open(main_file, "w") as f:
            f.write(combined_content)

        print(f"Successfully updated {main_file} with new CLI parser and main function")
        return True

    except Exception as e:
        print(f"Failed to update CLI implementation: {e}")
        print("Try manually reinstalling the package with: pip install -e .")
        return False


if __name__ == "__main__":
    if update_package_cli():
        print("\nUpdate complete! Try running 'civit -d URL' now.")
        print("If it doesn't work, you may need to reinstall the package:")
        print("pip uninstall civit && pip install -e .")
    else:
        print("\nUpdate failed. Please check the errors above.")
        sys.exit(1)
