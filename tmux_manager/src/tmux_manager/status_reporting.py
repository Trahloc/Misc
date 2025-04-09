# FILE: tmux_manager/src/tmux_manager/status_reporting.py
"""
# PURPOSE: Provides status reporting and diagnostics for tmux service and sessions.

## INTERFACES:
  - get_service_status_report() -> str: Returns a formatted status report of tmux service and sessions
  - get_diagnostics_report() -> str: Returns a comprehensive diagnostic report for troubleshooting

## DEPENDENCIES:
  - subprocess: For executing tmux commands
  - pathlib: For file path operations
  - os: For environment and user information
  - systemd_integration: For systemd service status
  - session_management: For session information
  - datetime: For timestamp formatting

## TODO:
  - Add machine-readable output formats (JSON, YAML)
  - Support different verbosity levels
"""

import subprocess
import os
import shutil
import platform
from pathlib import Path
from datetime import datetime

# Local imports
from . import systemd_integration
from . import session_management


def get_service_status_report(
    tmux_service_name: str = "tmux.service",
    autosave_timer_name: str = "tmuxp_autosave.timer",
    session_name: str = "autosaved_session",
) -> str:
    """
    PURPOSE: Generates a human-readable status report of tmux service and sessions.

    PARAMS:
    tmux_service_name: str - Name of the tmux systemd service
    autosave_timer_name: str - Name of the autosave timer
    session_name: str - Name of the default session

    RETURNS:
    str: Formatted status report
    """
    report = []
    report.append("=== Tmux Service Status ===")

    # Check systemd service status
    service_status = systemd_integration.get_service_status(tmux_service_name)
    if service_status["status"] == "RUNNING":
        report.append("Tmux Service: RUNNING")
        if service_status["main_pid"]:
            report.append(f"  Main PID: {service_status['main_pid']}")
        report.append(f"  Active: {service_status['active_state']}")
    else:
        report.append("Tmux Service: STOPPED")

    report.append("")
    report.append("=== Tmux Sessions ===")

    # Get active sessions
    active_sessions = session_management.get_active_sessions()
    if active_sessions:
        for session in active_sessions:
            report.append(f"  {session}")
    else:
        report.append("  No active sessions")

    report.append("")
    report.append("=== Saved Configurations ===")

    # Check for tmuxp config
    config_path = _get_tmuxp_config_path(session_name)
    if config_path.exists():
        last_modified = datetime.fromtimestamp(config_path.stat().st_mtime)
        size = _get_file_size_human_readable(config_path.stat().st_size)

        report.append(f"  Config: {config_path}")
        report.append(f"  Last saved: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"  Size: {size}")
    else:
        report.append(f"  No saved configuration found for '{session_name}'")

    report.append("")
    report.append("=== Auto-Save Status ===")

    # Check autosave timer status
    timer_status = systemd_integration.get_timer_status(autosave_timer_name)
    if timer_status["status"] == "ACTIVE":
        report.append("  Auto-save timer: ACTIVE")
        if timer_status["last_trigger"]:
            report.append(f"  Last triggered: {timer_status['last_trigger']}")
        if timer_status["next_trigger"]:
            report.append(f"  Next trigger: {timer_status['next_trigger']}")
    else:
        report.append("  Auto-save timer: INACTIVE")

    return "\n".join(report)


def get_diagnostics_report() -> str:
    """
    PURPOSE: Generates a comprehensive diagnostic report for troubleshooting.

    RETURNS:
    str: Formatted diagnostics report
    """
    report = []
    report.append("=== Tmux Diagnostics Information ===")

    # User and system information
    uid = os.getuid()
    username = os.environ.get("USER", "unknown")
    report.append(f"User: {username} (UID: {uid})")

    # Socket information
    socket_path = f"/tmp/tmux-{uid}/default"
    socket_exists = Path(socket_path).exists()
    report.append(f"Socket Path: {socket_path}")
    report.append(f"Socket Exists: {'YES' if socket_exists else 'NO'}")

    if socket_exists:
        try:
            socket_perms = subprocess.run(
                ["ls", "-la", socket_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            report.append(
                f"Socket Permissions: {socket_perms.stdout.decode('utf-8').strip()}"
            )
        except:
            report.append("Socket Permissions: Unable to determine")

    # Tmux binary information
    tmux_path = shutil.which("tmux")
    report.append(f"Tmux Binary: {tmux_path if tmux_path else 'Not found'}")

    if tmux_path:
        try:
            tmux_version = subprocess.run(
                ["tmux", "-V"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            report.append(
                f"Tmux Version: {tmux_version.stdout.decode('utf-8').strip()}"
            )
        except:
            report.append("Tmux Version: Unable to determine")

    # Systemd service information
    try:
        service_file = subprocess.run(
            ["systemctl", "--user", "cat", "tmux.service"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if service_file.returncode == 0:
            report.append("Systemd Service:")
            for line in service_file.stdout.decode("utf-8").strip().split("\n"):
                report.append(f"  {line}")
        else:
            report.append("Systemd Service: No service file found")
    except:
        report.append("Systemd Service: Unable to retrieve")

    # Tmuxp information
    tmuxp_path = shutil.which("tmuxp")
    report.append(
        f"Tmuxp Installation: {tmuxp_path if tmuxp_path else 'Not installed'}"
    )

    config_dir = _get_tmuxp_config_dir()
    report.append(f"Tmuxp Config Path: {config_dir}")

    # List tmuxp configs
    try:
        if config_dir.exists():
            configs = list(config_dir.glob("*.yaml"))
            if configs:
                report.append("Tmuxp Configs:")
                for config in configs:
                    report.append(f"  {config}")
            else:
                report.append("Tmuxp Configs: None found")
        else:
            report.append("Tmuxp Configs: Config directory does not exist")
    except:
        report.append("Tmuxp Configs: Unable to list")

    # Check platform information
    report.append("")
    report.append("=== System Information ===")
    report.append(f"Platform: {platform.platform()}")
    report.append(f"Python Version: {platform.python_version()}")

    # Try direct tmux commands with output
    report.append("")
    report.append("=== Attempting Direct Tmux Commands ===")

    # Try start-server
    report.append("$ tmux start-server:")
    try:
        start_result = subprocess.run(
            ["tmux", "start-server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if start_result.returncode == 0:
            report.append("  Success")
        else:
            report.append(f"  Failed: {start_result.stderr.decode('utf-8').strip()}")
    except Exception as e:
        report.append(f"  Error: {str(e)}")

    # Try list-sessions
    report.append("$ tmux list-sessions:")
    try:
        list_result = subprocess.run(
            ["tmux", "list-sessions"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if list_result.returncode == 0:
            sessions = list_result.stdout.decode("utf-8").strip()
            if sessions:
                report.append(f"  {sessions}")
            else:
                report.append("  No sessions")
        else:
            report.append(f"  Failed: {list_result.stderr.decode('utf-8').strip()}")
    except Exception as e:
        report.append(f"  Error: {str(e)}")

    return "\n".join(report)
