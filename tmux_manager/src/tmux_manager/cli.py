# FILE: tmux_manager/src/tmux_manager/cli.py
"""
# PURPOSE: Provides the command-line interface for the tmux manager.

## INTERFACES:
  - main() -> int: Entry point for the CLI, returns exit code
  - parse_args(args: List[str]) -> argparse.Namespace: Parses command-line arguments

## DEPENDENCIES:
  - argparse: For command-line argument parsing
  - logging: For structured logging
  - sys: For system-level operations
  - os: For environment variables
  - config_management: For configuration
  - server_management: For tmux server operations
  - session_management: For tmux session operations
  - status_reporting: For status reporting
  - systemd_integration: For systemd operations

## TODO:
  - Add more command-line options for fine-grained control
  - Support configuration overrides via command line
"""

import argparse
import logging
import sys
import os
import subprocess
from typing import List, Optional

# Local imports
from . import config_management
from . import server_management
from . import session_management
from . import status_reporting
from . import systemd_integration

def parse_args(args: List[str]) -> argparse.Namespace:
    """
    PURPOSE: Parses command-line arguments.

    PARAMS:
    args: List[str] - Command-line arguments

    RETURNS:
    argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog="tmux_manager",
        description="Manages tmux service lifecycle including server, sessions, and systemd integration.",
        epilog="When run without options, ensures tmux is running and attaches to the default session."
    )

    # Debug options
    parser.add_argument("-v", "--verbose", action="count", default=0,
                      help="Increase verbosity (can be used multiple times)")

    # Main operation modes
    group = parser.add_mutually_exclusive_group()

    group.add_argument("--status", action="store_true",
                     help="Show status of tmux service and sessions")

    group.add_argument("--diagnostics", action="store_true",
                      help="Show comprehensive diagnostics information")

    group.add_argument("--restart", action="store_true",
                      help="Restart tmux service")

    group.add_argument("--save", action="store_true",
                      help="Save current session using tmuxp")

    group.add_argument("--ensure", action="store_true",
                      help="Ensure tmux server and session exist")

    # Session name override
    parser.add_argument("--session", metavar="NAME",
                      help="Use specified session name instead of default")

    # Passthrough arguments
    parser.add_argument("tmux_args", nargs="*",
                      help="Arguments to pass to tmux (if no operation mode specified)")

    return parser.parse_args(args)

def setup_logging(verbosity: int) -> None:
    """
    PURPOSE: Sets up logging with appropriate verbosity.

    PARAMS:
    verbosity: int - Verbosity level (0=normal, 1=verbose, 2+=debug)
    """
    log_level = logging.WARNING
    if verbosity >= 2:
        log_level = logging.DEBUG
    elif verbosity == 1:
        log_level = logging.INFO

    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def main(args: Optional[List[str]] = None) -> int:
    """
    PURPOSE: Main entry point for the CLI.

    PARAMS:
    args: Optional[List[str]] - Command-line arguments, or None to use sys.argv

    RETURNS:
    int: Exit code
    """
    # Parse arguments
    if args is None:
        args = sys.argv[1:]

    parsed_args = parse_args(args)

    # Setup logging
    setup_logging(parsed_args.verbose)

    # Get logger
    logger = logging.getLogger("tmux_manager")

    # Load configuration
    config = config_management.get_config()

    # Update config with command-line options
    if parsed_args.verbose > 0:
        config.debug_level = parsed_args.verbose

    # Get session name
    session_name = parsed_args.session or config.default_session_name

    # Process command-line options
    try:
        # Status reporting
        if parsed_args.status:
            print(status_reporting.get_service_status_report(
                tmux_service_name=config.tmux_service_name,
                autosave_timer_name=config.autosave_timer_name,
                session_name=session_name
            ))
            return 0

        # Diagnostics
        elif parsed_args.diagnostics:
            print(status_reporting.get_diagnostics_report())
            return 0

        # Restart service
        elif parsed_args.restart:
            logger.info("Restarting tmux service...")
            if systemd_integration.is_service_available(config.tmux_service_name):
                if systemd_integration.restart_tmux_service(config.tmux_service_name):
                    print("Tmux service restarted successfully.")
                    return 0
                else:
                    print("Failed to restart tmux service via systemd.")
                    logger.warning("Falling back to manual restart...")

            # Manual restart
            print("Restarting tmux server directly...")
            try:
                subprocess.run(["tmux", "kill-server"], check=False)
            except Exception as e:
                logger.debug(f"Error killing server: {e}")

            if server_management.ensure_tmux_server_is_running(config.debug_level):
                print("Tmux server restarted successfully.")
                return 0
            else:
                print("Failed to restart tmux server.")
                return 1

        # Save session
        elif parsed_args.save:
            logger.info(f"Saving session '{session_name}'...")
            if not server_management.ensure_tmux_server_is_running(config.debug_level):
                print("Cannot save session: tmux server not running")
                return 1

            if session_management.save_session(session_name):
                print(f"Session '{session_name}' saved successfully.")
                return 0
            else:
                print(f"Failed to save session '{session_name}'.")
                return 1

        # Ensure service
        elif parsed_args.ensure:
            if not server_management.ensure_tmux_server_is_running(config.debug_level):
                print("Failed to ensure tmux server is running.")
                return 1

            if not session_management.ensure_session_exists(session_name):
                print(f"Failed to ensure session '{session_name}' exists.")
                return 1

            print("Tmux service and session verified.")
            return 0

        # Pass through to tmux if arguments start with '-'
        elif parsed_args.tmux_args and parsed_args.tmux_args[0].startswith('-') and not parsed_args.tmux_args[0].startswith('--'):
            logger.debug(f"Passing through to tmux: {parsed_args.tmux_args}")
            return subprocess.run(["tmux"] + parsed_args.tmux_args).returncode

        # Default behavior: ensure server and connect to session
        else:
            logger.debug("Default behavior: ensure server and connect to session")

            if not server_management.ensure_tmux_server_is_running(config.debug_level):
                print("Error: Failed to start tmux server. Please check your tmux installation.")
                return 1

            # Check if we're already in a tmux session
            if "TMUX" in os.environ:
                logger.debug("Already in tmux session, passing through arguments")

                # Already in tmux, pass through any arguments
                if parsed_args.tmux_args:
                    return subprocess.run(["tmux"] + parsed_args.tmux_args).returncode
                else:
                    return 0
            else:
                # Not in tmux, connect to existing session or create one
                if session_management.ensure_session_exists(session_name):
                    # Attach to the session
                    logger.debug(f"Attaching to session '{session_name}'")
                    os.execvp("tmux", ["tmux", "attach-session", "-t", session_name])
                    # If we get here, exec failed
                    print(f"Failed to attach to session '{session_name}'.")
                    return 1
                else:
                    print(f"Failed to create or restore session '{session_name}'.")
                    return 1

    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1

    return 0

# Entry point for the CLI when run directly
if __name__ == "__main__":
    sys.exit(main())

"""
## KNOWN ERRORS:
- May not handle all tmux command-line options correctly when passing through

## IMPROVEMENTS:
- Structured argument parsing with helpful descriptions
- Comprehensive command-line interface for all operations
- Proper error handling with exit codes

## FUTURE TODOs:
- Add tab completion for CLI options
- Add more fine-grained options for controlling tmux behavior
- Support configuration overrides via command line
"""