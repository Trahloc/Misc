"""Helper function to generate a deterministic container name."""

import hashlib
from pathlib import Path


def _get_container_name(project_root: Path) -> str:
    """Generate a deterministic container name for the project."""
    project_hash = hashlib.sha1(str(project_root).encode()).hexdigest()[:12]
    return f"zlt-baseline-runner-{project_hash}"
