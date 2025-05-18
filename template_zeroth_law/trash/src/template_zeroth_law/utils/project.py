"""
# PURPOSE: Project utilities for working with project structure.

## INTERFACES:
 - get_project_root(): Get the project root directory

## DEPENDENCIES:
 - pathlib.Path
"""

from pathlib import Path


def get_project_root() -> Path:
    """
    PURPOSE: Determine the project root directory
    CONTEXT: Used for checking project paths
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS:
        Path: Path to the project root directory
    EXCEPTIONS: None
    """
    # Start with current directory
    current_dir = Path.cwd()

    # Look for typical project indicators
    indicators = ["pyproject.toml", "setup.py", ".git"]

    # Check current and parent directories
    check_dir = current_dir
    for _ in range(5):  # Don't go too far up
        for indicator in indicators:
            if (check_dir / indicator).exists():
                return check_dir

        # Move up to parent
        parent = check_dir.parent
        if parent == check_dir:  # Reached root
            break
        check_dir = parent

    # Fall back to current directory if no project root found
    return current_dir


"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Fixed circular import issue and implemented project root detection
## FUTURE TODOs: Add more project structure utilities
"""
