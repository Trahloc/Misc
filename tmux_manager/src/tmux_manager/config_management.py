# FILE: tmux_manager/src/tmux_manager/config_management.py
"""
# PURPOSE: Manages configuration settings for the tmux manager.

## INTERFACES:
  - get_config() -> Config: Returns the configuration object
  - load_config(config_path: Optional[Path] = None) -> Config: Loads configuration from file or defaults
  - save_config(config: Config, config_path: Optional[Path] = None) -> bool: Saves configuration to file

## DEPENDENCIES:
  - os: For environment variables
  - pathlib: For file path operations
  - dataclasses: For structured configuration
  - yaml: For configuration file format
  - logging: For structured logging

## TODO:
  - Add configuration validation
  - Support different configuration formats
"""

import os
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

@dataclass
class Config:
    """Configuration settings for tmux manager."""
    # Default session name
    default_session_name: str = "autosaved_session"

    # Systemd service names
    tmux_service_name: str = "tmux.service"
    autosave_timer_name: str = "tmuxp_autosave.timer"

    # Logging settings
    debug_level: int = 0
    log_file: Optional[str] = None

    # Paths
    socket_dir: Optional[str] = None  # If None, use default (/tmp/tmux-$UID/)

    # Commands
    tmux_binary: Optional[str] = None  # If None, use from PATH
    tmuxp_binary: Optional[str] = None  # If None, use from PATH

    # Backup settings
    backup_configs: bool = True
    max_backups: int = 5

    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)

def get_config() -> Config:
    """
    PURPOSE: Returns the current configuration (loads it if not already loaded).

    RETURNS:
    Config: Configuration object
    """
    global _config

    if _config is None:
        _config = load_config()

    return _config

def load_config(config_path: Optional[Path] = None) -> Config:
    """
    PURPOSE: Loads configuration from file or uses defaults.

    PARAMS:
    config_path: Optional[Path] - Path to configuration file, or None to use default

    RETURNS:
    Config: Loaded configuration
    """
    logger = logging.getLogger("tmux_manager.config")

    # Use default path if none provided
    if config_path is None:
        config_path = _get_default_config_path()

    # Start with default configuration
    config = Config()

    # Try to load from file
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)

                if loaded_config is None:
                    logger.warning(f"Empty config file: {config_path}")
                    return config

                # Update configuration with loaded values
                for key, value in loaded_config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                    else:
                        config.custom_settings[key] = value

                logger.info(f"Loaded configuration from {config_path}")

        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            logger.info("Using default configuration")
    else:
        logger.info(f"Configuration file {config_path} not found, using defaults")

    return config

def save_config(config: Config, config_path: Optional[Path] = None) -> bool:
    """
    PURPOSE: Saves configuration to file.

    PARAMS:
    config: Config - Configuration to save
    config_path: Optional[Path] - Path to save to, or None to use default

    RETURNS:
    bool: True if saved successfully, False otherwise
    """
    logger = logging.getLogger("tmux_manager.config")

    # Use default path if none provided
    if config_path is None:
        config_path = _get_default_config_path()

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dictionary for saving
    config_dict = asdict(config)

    try:
        # Create backup if file exists and backup is enabled
        if config_path.exists() and config.backup_configs:
            _create_backup(config_path, config.max_backups)

        # Save configuration
        with open(config_path, 'w') as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False)

        logger.info(f"Saved configuration to {config_path}")
        return True

    except Exception as e:
        logger.error(f"Error saving configuration to {config_path}: {e}")
        return False

def _get_default_config_path() -> Path:
    """
    PURPOSE: Gets the default path for the configuration file.

    RETURNS:
    Path: Default configuration file path
    """
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
    if xdg_config_home:
        config_dir = Path(xdg_config_home) / "tmux_manager"
    else:
        config_dir = Path.home() / ".config" / "tmux_manager"

    return config_dir / "config.yaml"

def _create_backup(file_path: Path, max_backups: int) -> None:
    """
    PURPOSE: Creates a backup of the specified file.

    PARAMS:
    file_path: Path - Path to the file to backup
    max_backups: int - Maximum number of backups to keep
    """
    from datetime import datetime
    import shutil

    # Create backup directory
    backup_dir = file_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = backup_dir / f"{file_path.name}.{timestamp}"

    # Create backup
    shutil.copy2(file_path, backup_path)

    # Remove old backups if exceeding max_backups
    if max_backups > 0:
        backups = sorted(backup_dir.glob(f"{file_path.name}.*"))
        if len(backups) > max_backups:
            for old_backup in backups[:-max_backups]:
                old_backup.unlink()

# Global configuration instance
_config = None

"""
## KNOWN ERRORS:
- May not create proper backups if file permissions are insufficient

## IMPROVEMENTS:
- Uses dataclass for type safety and clear structure
- Follows XDG standards for config locations
- Supports configuration backups

## FUTURE TODOs:
- Add configuration validation
- Support different configuration formats (JSON, TOML)
- Add environment variable overrides
"""