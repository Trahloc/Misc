"""Path-related utility functions."""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def find_project_root(start_path: Path) -> Path | None:
    """Searches upwards from start_path for the project root directory (containing pyproject.toml).

    Args:
        start_path: The directory to start searching from.

    Returns:
        The Path to the project root directory if found, otherwise None.

    """
    current_path = start_path.resolve()
    while True:
        log.debug(f"Checking for pyproject.toml in: {current_path}")
        if (current_path / "pyproject.toml").is_file():
            log.info(f"Found project root at: {current_path}")
            return current_path

        parent = current_path.parent
        if parent == current_path:
            # Reached the filesystem root
            log.warning(f"Could not find project root (pyproject.toml) starting from {start_path}")
            return None
        current_path = parent
