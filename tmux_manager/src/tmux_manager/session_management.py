# FILE: tmux_manager/src/tmux_manager/session_management.py
"""
# PURPOSE: Manages tmux session lifecycle including creation and restoration.

## INTERFACES:
  - ensure_session_exists(session_name: str) -> bool: Ensures the specified session exists, returns success status
  - save_session(session_name: str) -> bool: Saves the specified session using tmuxp, returns success status

## DEPENDENCIES:
  - subprocess: For executing tmux and tmuxp commands
  - pathlib: For config file path management
  - logging: For structured logging
  - os: For environment variable manipulation

## TODO:
  - Add support for different session managers (not just tmuxp)
  - Implement session backup/restore from custom formats
"""

import subprocess
import os
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, Optional, List

def ensure_session_exists(session_name: str) -> bool:
    """
    PURPOSE: Ensures the specified tmux session exists, creating or restoring if needed.

    PARAMS:
    session_name: str - Name of the session to ensure exists

    RETURNS:
    bool: True if session exists (or was successfully created), False otherwise
    """
    logger = logging.getLogger("tmux_manager.session")

    # Check if tmuxp is installed for potential restoration
    has_tmuxp = shutil.which("tmuxp") is not None

    # Check if session already exists
    if _does_session_exist(session_name):
        logger.debug(f"Session '{session_name}' already exists")
        return True

    logger.info(f"Session '{session_name}' not found. Attempting to restore...")

    # Try to restore from tmuxp config if available
    if has_tmuxp:
        config_path = _get_tmuxp_config_path(session_name)
        if config_path.exists():
            success = _restore_session_from_tmuxp(session_name)
            if success:
                logger.info(f"Successfully restored session '{session_name}' from tmuxp config")
                return True
            else:
                logger.warning(f"Failed to load session from tmuxp config")
        else:
            logger.info(f"No saved config found at {config_path}")
    else:
        logger.warning("Tmuxp not installed, cannot restore from saved configuration")

    # Create a new session as fallback
    logger.info(f"Creating new session '{session_name}'...")
    success = _create_new_session(session_name)

    if success:
        logger.info(f"Created new session '{session_name}'")
    else:
        logger.error(f"Failed to create session '{session_name}'")

    return success

def save_session(session_name: str, timeout: int = 60) -> bool:
    """
    PURPOSE: Saves the specified tmux session using the official tmuxp freeze tool.

    PARAMS:
    session_name: str - Name of the session to save
    timeout: int - Maximum time in seconds to wait for operations to complete

    RETURNS:
    bool: True if session was saved successfully, False otherwise
    """
    logger = logging.getLogger("tmux_manager.session")

    # Check if tmuxp is installed
    if not shutil.which("tmuxp"):
        logger.error("Cannot save session: tmuxp not installed")
        return False

    # Check if session exists
    if not _does_session_exist(session_name):
        logger.error(f"Cannot save session: session '{session_name}' does not exist")
        return False

    logger.info(f"Saving session '{session_name}'...")

    # Get the config directory path
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
    if xdg_config_home:
        config_dir = Path(xdg_config_home) / "tmuxp"
    else:
        config_dir = Path.home() / ".config" / "tmuxp"

    # Create config dir if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # Output file path
    config_path = config_dir / f"{session_name}.yaml"

    try:
        # Use the official tmuxp freeze command, but with -yes to avoid prompts
        # Uses a temporary file approach to avoid the interactive prompts
        temp_config_path = config_path.with_suffix('.tmp.yaml')

        # First, capture the session using --yes to auto-accept, and -o to specify output file
        # This prevents the interactive prompts that cause hanging
        command = ["tmuxp", "freeze", session_name, "-o", str(temp_config_path), "--yes"]
        logger.debug(f"Executing command: {' '.join(command)}")

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False
        )

        # Check if the file was created
        if temp_config_path.exists():
            # Move the temporary file to the final location
            if config_path.exists():
                config_path.unlink()
            temp_config_path.rename(config_path)
            logger.info(f"Successfully saved session '{session_name}' to {config_path}")
            return True
        else:
            stderr = result.stderr.decode('utf-8') if result.stderr else ""
            stdout = result.stdout.decode('utf-8') if result.stdout else ""
            logger.error(f"tmuxp freeze failed to create config file. Exit code: {result.returncode}")
            logger.debug(f"tmuxp stdout: {stdout}")
            logger.debug(f"tmuxp stderr: {stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Save operation timed out after {timeout} seconds")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving session '{session_name}': {e}")
        return False

def get_active_sessions() -> List[str]:
    """
    PURPOSE: Gets a list of all active tmux sessions.

    RETURNS:
    List[str]: List of session names
    """
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        sessions = result.stdout.decode('utf-8').strip().split('\n')
        return [s for s in sessions if s]  # Filter out empty strings
    except subprocess.CalledProcessError:
        return []

def _does_session_exist(session_name: str) -> bool:
    """
    PURPOSE: Checks if the specified tmux session exists.

    PARAMS:
    session_name: str - Name of the session to check

    RETURNS:
    bool: True if session exists, False otherwise
    """
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        return result.returncode == 0
    except:
        return False

def _get_tmuxp_config_path(session_name: str) -> Path:
    """
    PURPOSE: Gets the path to the tmuxp configuration file for the specified session.

    PARAMS:
    session_name: str - Name of the session

    RETURNS:
    Path: Path to the tmuxp configuration file
    """
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
    if xdg_config_home:
        config_dir = Path(xdg_config_home) / "tmuxp"
    else:
        config_dir = Path.home() / ".config" / "tmuxp"

    return config_dir / f"{session_name}.yaml"

def _restore_session_from_tmuxp(session_name: str) -> bool:
    """
    PURPOSE: Attempts to restore a tmux session from a tmuxp config.

    PARAMS:
    session_name: str - Name of the session to restore

    RETURNS:
    bool: True if session was restored successfully, False otherwise
    """
    logger = logging.getLogger("tmux_manager.session")

    # Ensure we're not trying to restore from within tmux
    env = os.environ.copy()
    if "TMUX" in env:
        env.pop("TMUX")

    try:
        result = subprocess.run(
            ["tmuxp", "load", "-d", session_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False
        )

        # Verify session was created
        return _does_session_exist(session_name)
    except Exception as e:
        logger.error(f"Error restoring session from tmuxp: {e}")
        return False

def _create_new_session(session_name: str) -> bool:
    """
    PURPOSE: Creates a new tmux session.

    PARAMS:
    session_name: str - Name of the session to create

    RETURNS:
    bool: True if session was created successfully, False otherwise
    """
    try:
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

"""
## KNOWN ERRORS:
- May fail if tmuxp is not installed when trying to restore sessions
- Session restoration might be incomplete if tmuxp config is corrupted

## IMPROVEMENTS:
- Follows XDG specification for config paths
- Improved error handling with detailed logging
- Clear separation of concerns between checking, restoring, and creating

## FUTURE TODOs:
- Add support for different session managers
- Implement session backup verification
- Add session templates for new sessions
"""