# FILE: tmux_manager/src/tmux_manager/__init__.py
"""
# PURPOSE: Provides a comprehensive tmux service manager for reliable session persistence.

## INTERFACES:
  - ensure_tmux_running() -> bool: Ensures tmux server is running
  - ensure_session_exists(session_name: str) -> bool: Ensures the specified session exists
  - save_session(session_name: str) -> bool: Saves the specified session
  - get_service_status() -> str: Returns formatted status report
  - get_diagnostics() -> str: Returns diagnostics information
  - restart_tmux_service() -> bool: Restarts tmux server
  - main(args: List[str]) -> int: CLI entry point

## DEPENDENCIES:
  - server_management: For tmux server operations
  - session_management: For tmux session operations
  - status_reporting: For status reporting
  - systemd_integration: For systemd operations
  - config_management: For configuration
  - cli: For command-line interface

## TODO:
  - Add integration with tmux plugins
  - Support for non-systemd platforms
"""

import logging
from typing import List, Optional

# Configure a null handler to avoid "No handler found" warnings
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Import module components
from . import server_management
from . import session_management
from . import status_reporting
from . import systemd_integration
from . import config_management
from . import cli

# Version information
__version__ = "0.1.0"
__author__ = "Tmux Manager Authors"
__license__ = "MIT"

# Public API functions
def ensure_tmux_running() -> bool:
    """
    PURPOSE: Ensures the tmux server is running.
    
    RETURNS:
    bool: True if server is running or was started successfully, False otherwise
    """
    config = config_management.get_config()
    return server_management.ensure_tmux_server_is_running(config.debug_level)

def ensure_session_exists(session_name: Optional[str] = None) -> bool:
    """
    PURPOSE: Ensures the specified session exists, creating or restoring if needed.
    
    PARAMS:
    session_name: Optional[str] - Name of the session, or None to use default
    
    RETURNS:
    bool: True if session exists or was created successfully, False otherwise
    """
    if session_name is None:
        session_name = config_management.get_config().default_session_name
    
    return session_management.ensure_session_exists(session_name)

def save_session(session_name: Optional[str] = None) -> bool:
    """
    PURPOSE: Saves the specified session using tmuxp.
    
    PARAMS:
    session_name: Optional[str] - Name of the session, or None to use default
    
    RETURNS:
    bool: True if session was saved successfully, False otherwise
    """
    if session_name is None:
        session_name = config_management.get_config().default_session_name
    
    return session_management.save_session(session_name)

def get_service_status() -> str:
    """
    PURPOSE: Returns a formatted status report of tmux service and sessions.
    
    RETURNS:
    str: Formatted status report
    """
    config = config_management.get_config()
    return status_reporting.get_service_status_report(
        tmux_service_name=config.tmux_service_name,
        autosave_timer_name=config.autosave_timer_name,
        session_name=config.default_session_name
    )

def get_diagnostics() -> str:
    """
    PURPOSE: Returns a comprehensive diagnostic report for troubleshooting.
    
    RETURNS:
    str: Formatted diagnostics report
    """
    return status_reporting.get_diagnostics_report()

def restart_tmux_service() -> bool:
    """
    PURPOSE: Restarts the tmux service.
    
    RETURNS:
    bool: True if service was restarted successfully, False otherwise
    """
    config = config_management.get_config()
    
    if systemd_integration.is_service_available(config.tmux_service_name):
        return systemd_integration.restart_tmux_service(config.tmux_service_name)
    else:
        # Manual restart
        try:
            import subprocess
            subprocess.run(["tmux", "kill-server"], check=False)
        except Exception:
            pass
        
        return server_management.ensure_tmux_server_is_running(config.debug_level)

def main(args: Optional[List[str]] = None) -> int:
    """
    PURPOSE: Main entry point for the CLI.
    
    PARAMS:
    args: Optional[List[str]] - Command-line arguments, or None to use sys.argv
    
    RETURNS:
    int: Exit code
    """
    return cli.main(args)

"""
## KNOWN ERRORS:
- No major known errors

## IMPROVEMENTS:
- Clean public API with sensible defaults
- Comprehensive documentation for all functions
- Proper exception handling throughout modules

## FUTURE TODOs:
- Add plugin system for extending functionality
- Implement deep session state saving beyond tmuxp
- Support for non-systemd init systems
- Add automated testing suite
"""
