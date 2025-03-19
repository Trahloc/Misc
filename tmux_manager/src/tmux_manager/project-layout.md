## Setting up as Tmux Replacement

To use `tmux-manager` as a drop-in replacement for `tmux`:

1. Create an alias in your shell configuration:

```bash
# Add to .bashrc or .zshrc
alias tmux='tmux-manager'
```

2. Or create a symbolic link:

```bash
ln -s $(which tmux-manager) ~/.local/bin/tmux
```

Make sure `~/.local/bin` is earlier in your PATH than the system tmux.# Tmux Manager - Project Layout and Installation Guide

## Project Structure

The project follows the Zeroth Law principles, particularly the Single Responsibility Principle (SRP), and uses a modern src-layout with standardized tooling.

```
tmux_manager/
├── src/
│   └── tmux_manager/
│       ├── __init__.py               # Public API and package entry point
│       ├── __main__.py               # Module entry point for direct execution
│       ├── server_management.py      # Manages tmux server lifecycle
│       ├── session_management.py     # Handles session creation and restoration
│       ├── systemd_integration.py    # Integrates with systemd services
│       ├── status_reporting.py       # Provides status and diagnostic reporting
│       ├── config_management.py      # Manages configuration settings
│       └── cli.py                    # Command-line interface
├── tests/
│   ├── __init__.py                   # Test package initialization
│   ├── test_server_management.py     # Tests for server management
│   └── ...                           # Other test modules
├── tools/
│   ├── __init__.py                   # Tools package initialization
│   └── autoinit.py                   # Tool for auto-generating __init__.py files
├── pyproject.toml                    # Project configuration (replaces setup.py)
├── .pre-commit-config.yaml           # Pre-commit hooks configuration
└── README.md                         # Project documentation
```

## Installation

### Option 1: Install from Source

1. Clone or create the project structure as shown above
2. Navigate to the project root directory (where pyproject.toml is located)
3. Install using pip:

```bash
pip install -e .
```

### Option 2: Direct Script Usage

If you prefer to use it without installing:

1. Create the project structure as shown above
2. Create a simple wrapper script:

```bash
#!/usr/bin/env python3
import sys
from src.tmux_manager import main

if __name__ == "__main__":
    sys.exit(main())
```

3. Make it executable and place it in your PATH:

```bash
chmod +x tmux-manager
cp tmux-manager ~/.local/bin/
```
from tmux_manager import main

if __name__ == "__main__":
    sys.exit(main())
```

3. Make it executable and place it in your PATH:

```bash
chmod +x tmux-manager
cp tmux-manager ~/.local/bin/
```

## Development Setup

To set up a development environment:

1. Clone the repository
2. Install development dependencies:

```bash
pip install -e ".[dev]"
```

3. Install pre-commit hooks:

```bash
pre-commit install
```

4. Run the tests:

```bash
pytest
```

### Using the Development Tools

The project includes several development tools:

1. **Autoinit**: Automatically generates `__init__.py` files:

```bash
python -m tools.autoinit
```

2. **Code Formatting**: Format the code with Black:

```bash
black src tests tools
```

3. **Type Checking**: Run MyPy for static type checking:

```bash
mypy src tests tools
```

4. **Linting**: Lint with Flake8:

```bash
flake8 src tests tools
```

5. **Pre-commit**: Run all checks at once:

```bash
pre-commit run --all-files
```

## Systemd Integration

For seamless operation with systemd:

1. Create a user service file at `~/.config/systemd/user/tmux.service`:

```ini
[Unit]
Description=Tmux Server
Documentation=man:tmux(1)

[Service]
Type=forking
ExecStart=/usr/bin/tmux start-server
ExecStop=/usr/bin/tmux kill-server
Restart=on-failure

[Install]
WantedBy=default.target
```

2. Create an autosave timer at `~/.config/systemd/user/tmuxp_autosave.timer`:

```ini
[Unit]
Description=Auto-save tmux sessions with tmuxp

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min

[Install]
WantedBy=timers.target
```

3. Create the corresponding service at `~/.config/systemd/user/tmuxp_autosave.service`:

```ini
[Unit]
Description=Auto-save tmux sessions with tmuxp

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'for session in $(tmux list-sessions -F "#{session_name}"); do tmuxp freeze "$session"; done'

[Install]
WantedBy=default.target
```

4. Enable the services:

```bash
systemctl --user enable tmux.service
systemctl --user enable tmuxp_autosave.timer
systemctl --user start tmux.service
systemctl --user start tmuxp_autosave.timer
```

## Testing Your Installation

Run the following commands to verify your installation:

```bash
# Check status
tmux-manager --status

# Show diagnostics
tmux-manager --diagnostics

# Connect to default session
tmux-manager
```

If everything is working correctly, you should now have a seamless tmux experience where your sessions persist automatically.
