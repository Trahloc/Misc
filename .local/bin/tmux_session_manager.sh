#!/bin/bash
# FILE: tmux_service_manager.sh
# alias: ~/.local/bin/tmux
# PURPOSE: Manages tmux service lifecycle including ensuring server is running and sessions are properly saved/restored.

## INTERFACES:
#  - main(): Entry point that manages tmux service orchestration
#  - ensure_tmux_running(): Ensures tmux server is running
#  - ensure_session_exists(session_name): Ensures the specified session exists
#  - get_service_status(): Reports on tmux service and session status

## DEPENDENCIES:
#  - tmux: Terminal multiplexer
#  - tmuxp: Tmux session manager
#  - systemd: For service management

# Define our default session name
SESSION_NAME="autosaved_session"
TMUX_SERVICE_NAME="tmux.service"

# Debug levels
# 0 = normal, 1 = verbose, 2+ = very verbose
DEBUG_LEVEL=0

# Debug function for controlled output based on verbosity
debug() {
  local level=$1
  shift
  if [ "$DEBUG_LEVEL" -ge "$level" ]; then
    echo "[DEBUG:$level] $*" >&2
  fi
}

ensure_tmux_running() {
  # PURPOSE: Ensures the tmux server is running.
  # Check if server is running already
  debug 1 "Checking if tmux server is running..."
  if tmux list-sessions &>/dev/null; then
    debug 1 "Server is already running."
    return 0
  fi

  debug 1 "Checking tmux socket at /tmp/tmux-$(id -u)/default"
  if [ -S "/tmp/tmux-$(id -u)/default" ]; then
    debug 1 "Socket exists but server not responding, removing stale socket..."
    rm -f "/tmp/tmux-$(id -u)/default"
  fi

  echo "No tmux server running. Starting server..."

  # First try: systemd if service file exists
  if systemctl --user list-unit-files "$TMUX_SERVICE_NAME" &>/dev/null; then
    echo "Starting tmux via systemd service..."
    systemctl --user start "$TMUX_SERVICE_NAME"
    sleep 2  # Give systemd time to start the service

    # Check if systemd successfully started tmux
    if tmux list-sessions &>/dev/null; then
      echo "Tmux started successfully via systemd."
      return 0
    else
      echo "Systemd service failed to start tmux properly. Trying direct methods..."
    fi
  else
    echo "No systemd service found for tmux. Using direct methods..."
  fi

  # Second try: direct tmux server start
  echo "Starting tmux server directly..."
  tmux start-server 2>/dev/null
  sleep 1  # Give server time to initialize

  # Check if that worked
  if tmux list-sessions &>/dev/null; then
    echo "Tmux server started successfully."
    return 0
  fi

  # Third try: create a temporary session to kickstart the server
  echo "Initializing server with temporary session..."
  tmux new-session -d -s "temp_session" 2>/dev/null
  sleep 1

  # Verify success
  if tmux has-session -t "temp_session" 2>/dev/null; then
    # Kill the temporary session, we just needed it to start the server
    tmux kill-session -t "temp_session" 2>/dev/null
    echo "Tmux server started successfully with temporary session."
    return 0
  fi

  # If we get here, all methods failed
  echo "Failed to start tmux server by any method." >&2
  return 1
}

ensure_session_exists() {
  # PURPOSE: Ensures the specified tmux session exists.
  local session_name="$1"

  # Check if session already exists
  if tmux has-session -t "$session_name" 2>/dev/null; then
    return 0
  fi

  # Session doesn't exist, try to restore it
  echo "Session '$session_name' not found. Attempting to restore..."

  # Check for tmuxp config
  local config_path="$HOME/.config/tmuxp/${session_name}.yaml"
  if [ -f "$config_path" ]; then
    echo "Restoring session from tmuxp config..."
    # Try to load the session - be explicit about environment
    TMUX="" tmuxp load -d "$session_name" 2>/dev/null

    # Check if the session was created successfully
    if tmux has-session -t "$session_name" 2>/dev/null; then
      return 0
    else
      echo "Failed to load session from tmuxp config."
    fi
  else
    echo "No saved config found."
  fi

  # Either no config or loading failed, create a new session
  echo "Creating new session..."
  tmux new-session -d -s "$session_name"
  return $?
}

get_service_status() {
  # PURPOSE: Reports on tmux service status and sessions.
  echo "=== Tmux Service Status ==="

  # Check systemd service
  if systemctl --user is-active "$TMUX_SERVICE_NAME" &>/dev/null; then
    echo "Tmux Service: RUNNING"
    systemctl --user status "$TMUX_SERVICE_NAME" | grep -E "Active:|Main PID:" | sed 's/^/  /'
  else
    echo "Tmux Service: STOPPED"
  fi

  echo ""
  echo "=== Tmux Sessions ==="
  if tmux list-sessions 2>/dev/null; then
    echo ""
  else
    echo "  No active sessions"
    echo ""
  fi

  echo "=== Saved Configurations ==="
  local config_path="$HOME/.config/tmuxp/${SESSION_NAME}.yaml"
  if [ -f "$config_path" ]; then
    local last_modified
    last_modified=$(stat -c %y "$config_path" 2>/dev/null || stat -f "%Sm" "$config_path" 2>/dev/null)
    echo "  Config: $config_path"
    echo "  Last saved: $last_modified"
    echo "  Size: $(du -h "$config_path" | cut -f1)"
  else
    echo "  No saved configuration found."
  fi

  echo ""
  echo "=== Auto-Save Status ==="
  if systemctl --user is-active "tmuxp_autosave.timer" &>/dev/null; then
    echo "  Auto-save timer: ACTIVE"
    systemctl --user status "tmuxp_autosave.timer" | grep -E "Trigger|Triggered" | sed 's/^/  /'
  else
    echo "  Auto-save timer: INACTIVE"
  fi
}

main() {
  # PURPOSE: Main entry point for tmux service management.

  # Check for debug flags first
  case "$1" in
    -v)
      DEBUG_LEVEL=1
      shift
      debug 1 "Verbose mode enabled"
      ;;
    -vv|-vvv|--debug)
      DEBUG_LEVEL=2
      shift
      debug 2 "Debug mode enabled"
      ;;
  esac

  # Process command line options
  case "$1" in
    --status)
      # Try to start the server for status checks but don't error if it fails
      ensure_tmux_running >/dev/null 2>&1
      get_service_status
      return $?
      ;;
    --diagnostics)
      # System diagnostics - print extensive system information
      cat <<EOF
=== Tmux Diagnostics Information ===
User: $(whoami) (UID: $(id -u))
Socket Path: /tmp/tmux-$(id -u)/default
Socket Exists: $([ -S "/tmp/tmux-$(id -u)/default" ] && echo "YES" || echo "NO")
Socket Permissions: $(ls -la /tmp/tmux-$(id -u)/default 2>/dev/null || echo "N/A")
Tmux Binary: $(which tmux)
Tmux Version: $(command tmux -V)
Systemd Service: $(systemctl --user cat tmux.service 2>/dev/null || echo "No service file found")
Tmuxp Installation: $(which tmuxp 2>/dev/null || echo "Not installed")
Tmuxp Config Path: $HOME/.config/tmuxp/
Tmuxp Configs: $(ls -la $HOME/.config/tmuxp/*.yaml 2>/dev/null || echo "None found")
EOF
      # Try direct tmux commands with full error output
      echo ""
      echo "=== Attempting Direct Tmux Commands ==="
      echo "$ tmux start-server:"
      command tmux start-server 2>&1 || echo "Failed"
      echo ""
      echo "$ tmux list-sessions:"
      command tmux list-sessions 2>&1 || echo "Failed"
      return 0
      ;;
    --restart)
      # First try to use systemd if service exists
      if systemctl --user list-unit-files "$TMUX_SERVICE_NAME" &>/dev/null; then
        echo "Restarting tmux via systemd service..."
        systemctl --user restart "$TMUX_SERVICE_NAME"
        sleep 2
      else
        # Otherwise do it manually
        echo "Restarting tmux server directly..."
        tmux kill-server 2>/dev/null || true  # Don't error if no server running
        ensure_tmux_running
      fi
      return $?
      ;;
    --save)
      # Manually trigger a session save
      # Make sure server is running first
      if ! ensure_tmux_running; then
        echo "Cannot save session: tmux server not running"
        return 1
      fi

      if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo "Saving session '$SESSION_NAME'..."
        tmuxp freeze "$SESSION_NAME"
        return $?
      else
        echo "Error: Session '$SESSION_NAME' does not exist." >&2
        return 1
      fi
      ;;
    --ensure)
      # Just make sure everything is running
      if ! ensure_tmux_running; then
        return 1
      fi
      if ! ensure_session_exists "$SESSION_NAME"; then
        return 1
      fi
      echo "Tmux service and session verified."
      return 0
      ;;
  esac

  # Try to execute the original tmux command if passed with standard flags
  if [[ "$1" == "-"* && "$1" != "--"* ]]; then
    debug 1 "Passing through to original tmux command: tmux $*"
    command tmux "$@"
    return $?
  fi

  # Default behavior: ensure tmux is running then handle session
  debug 1 "Attempting to ensure tmux server is running"
  if ! ensure_tmux_running; then
    echo "Error: Failed to start tmux server. Please check your tmux installation."
    return 1
  fi

  # Check if we're already in a tmux session
  if [ -n "$TMUX" ]; then
    debug 1 "Already inside a tmux session, passing through arguments"
    # Already in tmux, pass through any arguments
    command tmux "$@"
    return $?
  else
    # Not in tmux, connect to existing session or create one
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
      # Session exists, attach to it
      exec tmux attach-session -t "$SESSION_NAME"
    else
      # Ensure session exists (creates or restores)
      if ! ensure_session_exists "$SESSION_NAME"; then
        echo "Failed to create or restore session. Creating a basic session."
        # Last resort: create a simple session directly
        exec tmux new-session -s "$SESSION_NAME"
      fi
      # Attach to the session
      exec tmux attach-session -t "$SESSION_NAME"
    fi
  fi
}

# Execute main function with all arguments
main "$@"

## KNOWN ERRORS:
#  - May need to adjust paths for different system configurations

## IMPROVEMENTS:
#  - Integrated with systemd service management
#  - Added comprehensive status reporting
#  - Created session restoration logic using tmuxp
#  - Added command line options for different operations
#  - Added manual save option (--save)

## FUTURE TODOs:
#  - Add integration with system startup for headless servers
#  - Implement session backup verification to prevent corruption
#  - Create configuration file for customizing behavior