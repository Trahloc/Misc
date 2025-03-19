# Tmux Manager

A comprehensive tmux service manager for reliable session persistence.

## Overview

Tmux Manager ensures your tmux sessions are always available, properly saved, and easily restored. It handles the complexities of tmux server lifecycle management, session persistence, and systemd integration.

Key features:

- **Reliable Server Management**: Ensures the tmux server is always running
- **Session Persistence**: Auto-saves and restores sessions using tmuxp
- **Systemd Integration**: Works seamlessly with systemd for service management
- **Simple Interface**: Just type `tmux-manager` to get started

## Installation

```bash
pip install tmux-manager
```

### Development Installation

```bash
git clone https://github.com/username/tmux_manager.git
cd tmux_manager
pip install -e .
```

## Usage

### Basic Usage

```bash
# Start or connect to default session
tmux-manager

# Show tmux service status
tmux-manager --status

# Save current session
tmux-manager --save

# Show detailed diagnostics
tmux-manager --diagnostics

# Restart tmux server
tmux-manager --restart

# Ensure server and session exist
tmux-manager --ensure
```

### Using a Different Session

```bash
tmux-manager --session myproject
```

### Passing Arguments to Tmux

```bash
tmux-manager -l  # Equivalent to 'tmux -l'
```

## Configuration

Configuration is stored in `~/.config/tmux_manager/config.yaml` (or `$XDG_CONFIG_HOME/tmux_manager/config.yaml` if set).

Example configuration:

```yaml
default_session_name: myproject
tmux_service_name: tmux.service
autosave_timer_name: tmuxp_autosave.timer
debug_level: 0
backup_configs: true
max_backups: 5
```

## Requirements

- Python 3.6+
- tmux
- tmuxp (optional, for session saving/restoring)
- systemd (optional, for service management)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
