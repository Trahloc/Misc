# FILE: tmux_manager/src/tmux_manager/server_management.py
"""
# PURPOSE: Manages tmux server lifecycle, ensuring it's running properly.

## INTERFACES: ensure_tmux_server_is_running() -> bool: Ensures tmux server is running, returns success status

## DEPENDENCIES:
  - subprocess: For executing tmux commands
  - pathlib: For socket path management
  - logging: For structured logging
  - os: For user ID and environment operations

## TODO:
  - Add configuration for custom socket paths
  - Implement server health checks
"""

import subprocess
import os
import time
import logging
import shutil
from pathlib import Path


def ensure_tmux_server_is_running(debug_level: int = 0) -> bool:
    """
    PURPOSE: Ensures the tmux server is running using progressively more forceful methods.

    PARAMS:
    debug_level: int - Controls verbosity (0=normal, 1=verbose, 2+=very verbose)

    RETURNS:
    bool: True if server is running (or was successfully started), False otherwise
    """
    logger = logging.getLogger("tmux_manager.server")

    # Check if tmux is installed
    if not shutil.which("tmux"):
        logger.error("Tmux executable not found in PATH")
        return False

    # Check if server is already running
    if _is_tmux_server_running():
        if debug_level >= 1:
            logger.debug("Server is already running")
        return True

    # Check for stale socket
    socket_path = Path(f"/tmp/tmux-{os.getuid()}/default")
    if socket_path.exists():
        if debug_level >= 1:
            logger.debug(
                f"Socket exists at {socket_path} but server not responding, removing stale socket"
            )
        try:
            socket_path.unlink()
        except OSError as e:
            logger.error(f"Failed to remove stale socket: {e}")

    logger.info("No tmux server running. Starting server...")

    # Try systemd first if available
    if _is_systemd_service_available("tmux.service"):
        success = _start_tmux_via_systemd()
        if success:
            return True
    else:
        logger.info("No systemd service found for tmux. Using direct methods...")

    # Try direct server start
    success = _start_tmux_directly()
    if success:
        return True

    # Last resort: create temporary session
    success = _start_with_temporary_session()
    if success:
        return True

    logger.error("Failed to start tmux server by any method")
    return False


def _is_tmux_server_running() -> bool:
    """
    PURPOSE: Checks if the tmux server is currently running.

    RETURNS:
    bool: True if server is running, False otherwise
    """
    try:
        subprocess.run(
            ["tmux", "list-sessions"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return True
    except:
        return False


def _is_systemd_service_available(service_name: str) -> bool:
    """
    PURPOSE: Checks if the specified systemd service unit is available.

    PARAMS:
    service_name: str - Name of the systemd service

    RETURNS:
    bool: True if service exists, False otherwise
    """
    try:
        result = subprocess.run(
            ["systemctl", "--user", "list-unit-files", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result.returncode == 0
    except:
        return False


def _start_tmux_via_systemd() -> bool:
    """
    PURPOSE: Attempts to start tmux server using systemd service.

    RETURNS:
    bool: True if server was started successfully, False otherwise
    """
    logger = logging.getLogger("tmux_manager.server")

    logger.info("Starting tmux via systemd service...")
    try:
        subprocess.run(
            ["systemctl", "--user", "start", "tmux.service"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        # Give systemd time to start the service
        time.sleep(2)

        # Verify server is running
        return _is_tmux_server_running()
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start tmux via systemd: {e}")
        return False


def _start_tmux_directly() -> bool:
    """
    PURPOSE: Attempts to start tmux server directly using tmux command.

    RETURNS:
    bool: True if server was started successfully, False otherwise
    """
    logger = logging.getLogger("tmux_manager.server")

    logger.info("Starting tmux server directly...")
    try:
        subprocess.run(
            ["tmux", "start-server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        # Give server time to initialize
        time.sleep(1)

        # Verify server is running
        return _is_tmux_server_running()
    except Exception as e:
        logger.error(f"Failed to start tmux server directly: {e}")
        return False


def _start_with_temporary_session() -> bool:
    """
    PURPOSE: Attempts to start tmux by creating a temporary session.

    RETURNS:
    bool: True if server was started successfully, False otherwise
    """
    logger = logging.getLogger("tmux_manager.server")

    logger.info("Initializing server with temporary session...")
    try:
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", "temp_session"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        # Give server time to initialize
        time.sleep(1)

        # Check if the session was created
        result = subprocess.run(
            ["tmux", "has-session", "-t", "temp_session"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if result.returncode == 0:
            # Kill the temporary session, we just needed it to start the server
            subprocess.run(
                ["tmux", "kill-session", "-t", "temp_session"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            logger.info("Tmux server started successfully with temporary session")
            return True
    except Exception as e:
        logger.error(f"Failed to start tmux with temporary session: {e}")

    return False


"""
## KNOWN ERRORS:
- May fail if tmux socket directory has incorrect permissions

## IMPROVEMENTS:
- Added structured logging
- Better error handling with specific error messages
- Modular design with clear function responsibilities
- Type hints for better code comprehension

## FUTURE TODOs:
- Add configuration for custom socket paths and timeouts
- Implement health check to validate server is fully operational
- Allow passing environment variables to tmux server process
"""
