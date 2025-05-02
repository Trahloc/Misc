"""Helper function for Stage 7: Stopping the Podman baseline runner."""

import structlog

# --- Import project modules --- #
# Relative path needs adjustment (add one more dot)
from ....lib.tooling.podman_utils import _run_podman_command

log = structlog.get_logger()


def _stop_podman_runner(container_name: str) -> None:
    """STAGE 7: Stops and removes the podman container."""
    log.info(f"STAGE 7: Stopping and removing Podman container: {container_name}")
    try:
        # Use --ignore to avoid errors if container is already gone
        _run_podman_command(["stop", "--ignore", container_name], check=False)
        _run_podman_command(["rm", "--ignore", container_name], check=False)
        log.info(f"Podman container {container_name} stopped and removed.")
    except Exception as e:
        # Log error but don't prevent script exit
        log.error(f"Error stopping/removing Podman container {container_name}: {e}")
