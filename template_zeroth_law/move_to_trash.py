#!/usr/bin/env python3
"""
# PURPOSE: Move unnecessary files to the trash folder for auditing.

## INTERFACES: N/A (Script)
## DEPENDENCIES: None
## TODO: None
"""

import os
import shutil
from pathlib import Path
import sys

# Root of the project
PROJECT_ROOT = Path(__file__).parent
TRASH_DIR = PROJECT_ROOT / "trash"

# Ensure trash directory exists
TRASH_DIR.mkdir(exist_ok=True)

# Files we've simplified/replaced and their derivatives should be moved
FILES_TO_KEEP = [
    # Core files we've already simplified
    "src/template_zeroth_law/__init__.py",
    "src/template_zeroth_law/__main__.py",
    "src/template_zeroth_law/exceptions.py",
    "src/template_zeroth_law/config.py",
    "tests/test_exceptions.py",
    "tests/test_config.py",
    # Other essential files
    "pyproject.toml",
    ".pre-commit-config.yaml",
    "README.md",
    "todo.md",
    "docs/ZerothLawAIFramework.py.md",
    "move_to_trash.py",  # This script
]

# Directories to keep
DIRS_TO_KEEP = [
    "src",
    "src/template_zeroth_law",
    "tests",
    "docs",
    "trash",
]


def should_keep(path):
    """Determine if a file/directory should be kept."""
    rel_path = str(path.relative_to(PROJECT_ROOT))

    # Keep directories we explicitly want to keep
    if path.is_dir() and rel_path in DIRS_TO_KEEP:
        return True

    # Keep core files we want to keep
    if rel_path in FILES_TO_KEEP:
        return True

    # Keep __init__.py and __pycache__ directories
    if path.is_dir() and path.name == "__pycache__":
        return True

    # Keep common project files
    if path.name in [".git", ".gitignore", "LICENSE", "setup.py"]:
        return True

    # Keep our refined files
    if rel_path.startswith("tests/") and path.suffix == ".py":
        # Keep test files
        return True

    return False


def move_to_trash(path):
    """Move a file or directory to the trash folder."""
    rel_path = path.relative_to(PROJECT_ROOT)
    dest = TRASH_DIR / rel_path

    # Create parent directories if needed
    if not dest.parent.exists():
        dest.parent.mkdir(parents=True)

    try:
        # Move the file/directory
        if path.is_file():
            shutil.copy2(path, dest)
            os.unlink(path)
            print(f"Moved file: {rel_path}")
        elif path.is_dir() and not path.name.startswith("."):
            # Only process non-hidden directories
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(path, dest)
            shutil.rmtree(path)
            print(f"Moved directory: {rel_path}")
    except Exception as e:
        print(f"Error moving {rel_path}: {e}")


def process_directory(directory):
    """Process a directory and move unnecessary files to trash."""
    # Get all files and directories, sorted to process files first
    items = sorted(directory.glob("*"), key=lambda p: p.is_dir())

    for item in items:
        if item.is_file() and not should_keep(item):
            move_to_trash(item)

    # Now process subdirectories (non-recursive to maintain control)
    for item in sorted(directory.glob("*")):
        if item.is_dir() and item != TRASH_DIR and not item.name.startswith("."):
            if not should_keep(item):
                # If the whole directory should go to trash
                move_to_trash(item)
            else:
                # Otherwise process its contents
                process_directory(item)


def main():
    """Main function to process the project directory."""
    print("Starting cleanup process...")
    print(f"Trash directory: {TRASH_DIR}")

    # Ask for confirmation
    response = input("This will move files to the trash folder. Continue? (y/n): ")
    if response.lower() != "y":
        print("Operation cancelled.")
        return

    # Process the project root
    process_directory(PROJECT_ROOT)

    print("\nCleanup complete. Files moved to trash folder.")
    print("Review the trash folder and delete it if content is not needed.")


if __name__ == "__main__":
    main()

"""
## KNOWN ERRORS: None
## IMPROVEMENTS: None
## FUTURE TODOs: None
"""
