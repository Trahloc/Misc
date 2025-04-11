#!/usr/bin/env python
"""Pre-commit hook script to prevent committing files from multiple projects.

Checks if staged files belong to more than one top-level directory
(immediate subdirectories of the Git root) that contains a pyproject.toml.
"""

import os
import sys
from pathlib import Path


def get_project_dir(filepath: Path, git_root: Path) -> str | None:
    """Identifies the top-level project directory for a given file path.

    A project directory is defined as an immediate subdirectory of the git_root
    that contains a pyproject.toml file.

    Args:
        filepath: The path to the staged file (relative to git_root).
        git_root: The absolute path to the Git repository root.

    Returns:
        The name of the top-level project directory, or None if the file
        is not in a recognized project directory.

    """
    try:
        # Get the first component of the relative path
        top_dir_name = filepath.parts[0]
        # Check if it's a directory directly under git_root
        potential_project_path = git_root / top_dir_name
        if potential_project_path.is_dir() and (potential_project_path / "pyproject.toml").is_file():
            return top_dir_name
    except IndexError:
        # Path is likely at the root or invalid
        pass
    return None


def main():
    staged_files = [Path(f) for f in sys.argv[1:]]
    git_root = Path(os.getcwd())  # pre-commit runs hooks from git root

    project_dirs = set()
    for file_path in staged_files:
        project_name = get_project_dir(file_path, git_root)
        if project_name:
            project_dirs.add(project_name)

    if len(project_dirs) > 1:
        print("ERROR: Commit includes files from multiple projects:", file=sys.stderr)
        for proj in sorted(project_dirs):
            print(f"  - {proj}", file=sys.stderr)
        print("Please commit files for each project separately.", file=sys.stderr)
        sys.exit(1)

    # print(f"Commit includes files from {len(project_dirs)} project(s): {project_dirs or 'None'}")
    sys.exit(0)


if __name__ == "__main__":
    main()
