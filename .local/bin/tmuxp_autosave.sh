#!/bin/bash
# FILE: tmuxp_autosave.sh
"""
# PURPOSE: Automatically saves the current tmux session configuration using tmuxp.

## INTERFACES:
  - main(): Entry point that handles the automatic saving of tmux sessions
  - verify_session_exists(session_name): Verifies that the specified session exists
  - save_session(session_name): Saves the session configuration using tmuxp

## DEPENDENCIES:
  - tmux: Terminal multiplexer
  - tmuxp: Tmux session manager for saving configurations

## TODO:
  - Add notification on save failure
"""

# Define our default session name
SESSION_NAME="autosaved_session"

# Set the display for graphical applications
export DISPLAY=":0"

verify_session_exists() {
  """
  PURPOSE: Verifies that the specified tmux session exists.

  PARAMS:
    - $1: Name of the session to check

  RETURNS:
    - 0 (true) if session exists, 1 (false) otherwise
  """
  if ! tmux has-session -t "$1" 2>/dev/null; then
    echo "Error: Session '$1' does not exist." >&2
    return 1
  fi
  return 0
}

save_session() {
  """
  PURPOSE: Saves the tmux session configuration using tmuxp.

  CONTEXT:
    - Requires tmuxp to be installed
    - Saves to the default location (~/.config/tmuxp/${session_name}.yaml)

  PARAMS:
    - $1: Name of the session to save

  RETURNS:
    - 0 on success, non-zero on failure
  """
  # Check if tmuxp is available
  if ! command -v tmuxp &>/dev/null; then
    echo "Error: tmuxp is not installed." >&2
    return 1
  fi

  # Try to save the session
  local save_output
  save_output=$(tmuxp freeze "$1" 2>&1)
  local save_status=$?

  if [ $save_status -ne 0 ]; then
    echo "Error saving session: $save_output" >&2
    return $save_status
  fi

  # Get timestamp for logging
  local timestamp
  timestamp=$(date "+%Y-%m-%d %H:%M:%S")

  # Log successful save
  echo "[$timestamp] Successfully saved session '$1'" >&2
  return 0
}

main() {
  """
  PURPOSE: Main entry point for automatic tmux session saving.

  CONTEXT:
    - Designed to be called from systemd timer
    - Handles verification and saving of tmux session

  PARAMS: None, uses environment and global variables

  RETURNS:
    - 0 on success, non-zero on failure
  """
  # First verify that the session exists
  if ! verify_session_exists "$SESSION_NAME"; then
    return 1
  fi

  # Then save the session
  if ! save_session "$SESSION_NAME"; then
    return 1
  fi

  return 0
}

# Execute main function
main "$@"

"""
## KNOWN ERRORS:
  - May fail if tmux server is not running
  - May fail if the session does not exist

## IMPROVEMENTS:
  - Restructured to follow Zeroth Law standard
  - Added proper error checking and handling
  - Added timestamp to successful save messages
  - Improved function separation for better maintainability

## FUTURE TODOs:
  - Add logging to a log file for historical tracking
  - Implement backup rotation to keep multiple configuration versions
  - Add a quiet mode for cron/systemd usage (suppress normal output)
"""