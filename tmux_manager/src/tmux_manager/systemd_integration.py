# FILE: tmux_manager/src/tmux_manager/systemd_integration.py
"""
# PURPOSE: Manages integration with systemd for tmux service control.

## INTERFACES:
  - get_service_status(service_name: str) -> dict: Returns status information for the specified systemd service
  - restart_tmux_service(service_name: str) -> bool: Restarts the tmux systemd service
  - is_service_active(service_name: str) -> bool: Checks if a systemd service is active

## DEPENDENCIES:
  - subprocess: For executing systemd commands
  - logging: For structured logging
  - re: For parsing systemd output

## TODO:
  - Add support for non-systemd init systems
  - Support custom systemd unit paths
"""

import subprocess
import logging
import re
from typing import Dict


def get_service_status(service_name: str) -> Dict[str, str]:
    """
    PURPOSE: Gets the status of the specified systemd service.

    PARAMS:
    service_name: str - Name of the systemd service

    RETURNS:
    Dict[str, str]: Dictionary containing service status information
    """
    logger = logging.getLogger("tmux_manager.systemd")

    status_info = {
        "status": "UNKNOWN",
        "active_state": "",
        "main_pid": "",
        "loaded": False,
        "enabled": False,
        "unit_file_state": "",
    }

    # Check if service is active
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        status_info["active_state"] = result.stdout.decode("utf-8").strip()
        status_info["status"] = "RUNNING" if result.returncode == 0 else "STOPPED"

        # Get detailed status
        if result.returncode == 0:
            detailed_status = subprocess.run(
                ["systemctl", "--user", "status", service_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            output = detailed_status.stdout.decode("utf-8")

            # Extract main PID
            pid_match = re.search(r"Main PID: (\d+)", output)
            if pid_match:
                status_info["main_pid"] = pid_match.group(1)

        # Check if service is enabled
        is_enabled = subprocess.run(
            ["systemctl", "--user", "is-enabled", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        status_info["unit_file_state"] = is_enabled.stdout.decode("utf-8").strip()
        status_info["enabled"] = is_enabled.returncode == 0

        # Check if service is loaded
        list_units = subprocess.run(
            ["systemctl", "--user", "list-units", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        status_info["loaded"] = service_name in list_units.stdout.decode("utf-8")

    except Exception as e:
        logger.error(f"Error getting service status: {e}")

    return status_info


def restart_tmux_service(service_name: str) -> bool:
    """
    PURPOSE: Restarts the tmux systemd service.

    PARAMS:
    service_name: str - Name of the tmux systemd service

    RETURNS:
    bool: True if service was restarted successfully, False otherwise
    """
    logger = logging.getLogger("tmux_manager.systemd")

    if not is_service_available(service_name):
        logger.warning(f"Service {service_name} is not available")
        return False

    logger.info(f"Restarting {service_name} via systemd...")

    try:
        subprocess.run(
            ["systemctl", "--user", "restart", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        # Verify service is now active
        if is_service_active(service_name):
            logger.info(f"Successfully restarted {service_name}")
            return True
        else:
            logger.error(f"Service {service_name} failed to restart")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to restart service {service_name}: {e}")
        return False


def is_service_active(service_name: str) -> bool:
    """
    PURPOSE: Checks if a systemd service is active.

    PARAMS:
    service_name: str - Name of the systemd service

    RETURNS:
    bool: True if service is active, False otherwise
    """
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result.returncode == 0
    except:
        return False


def is_service_available(service_name: str) -> bool:
    """
    PURPOSE: Checks if a systemd service unit file is available.

    PARAMS:
    service_name: str - Name of the systemd service

    RETURNS:
    bool: True if service is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["systemctl", "--user", "list-unit-files", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result.returncode == 0 and service_name in result.stdout.decode("utf-8")
    except:
        return False


def get_timer_status(timer_name: str) -> Dict[str, str]:
    """
    PURPOSE: Gets the status of the specified systemd timer.

    PARAMS:
    timer_name: str - Name of the systemd timer

    RETURNS:
    Dict[str, str]: Dictionary containing timer status information
    """
    status_info = {
        "status": "UNKNOWN",
        "active": False,
        "last_trigger": "",
        "next_trigger": "",
    }

    try:
        # Check if timer is active
        is_active = subprocess.run(
            ["systemctl", "--user", "is-active", timer_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        status_info["active"] = is_active.returncode == 0
        status_info["status"] = "ACTIVE" if is_active.returncode == 0 else "INACTIVE"

        # Get detailed status
        if is_active.returncode == 0:
            detailed_status = subprocess.run(
                ["systemctl", "--user", "status", timer_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            output = detailed_status.stdout.decode("utf-8")

            # Extract trigger times
            last_trigger = re.search(r"Triggered: (.*)", output)
            if last_trigger:
                status_info["last_trigger"] = last_trigger.group(1).strip()

            next_trigger = re.search(r"Trigger: (.*)", output)
            if next_trigger:
                status_info["next_trigger"] = next_trigger.group(1).strip()

    except Exception:
        pass

    return status_info


"""
## KNOWN ERRORS:
- May not work on systems that don't use systemd
- Regular expression parsing may break if systemd output format changes

## IMPROVEMENTS:
- Added comprehensive service status retrieval
- Implemented timer status retrieval for autosave timers
- Better error handling with detailed logging

## FUTURE TODOs:
- Add support for non-systemd init systems
- Support custom systemd unit paths
- Add functionality to generate systemd unit files
"""
