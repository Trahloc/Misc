"""
# PURPOSE: Configuration management for Zeroth Law Framework.

## INTERFACES:
 - Config: Configuration class
 - get_config: Get application configuration
 - load_config: Load configuration from file
 - ConfigSection: Base class for config sections

## DEPENDENCIES:
 - os: Environment variables
 - pathlib: Path handling
 - typing: Type hints
 - template_zeroth_law.exceptions: Custom exceptions
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from .exceptions import ConfigError
from .types import LogLevel

# Define default configuration values that tests can reference
DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "name": "template_zeroth_law",
        "version": "1.0.0",
        "description": "Zeroth Law Framework",
        "debug": False,
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
    },
    "paths": {
        "data_dir": "data",
        "output_dir": "output",
        "cache_dir": ".cache"
    }
}

@dataclass
class ConfigSection:
    """Base class for configuration sections."""
    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


@dataclass
class AppConfig(ConfigSection):
    """Application configuration section."""
    name: str = "template_zeroth_law"
    version: str = "1.0.0"
    description: str = "Zeroth Law Framework"
    debug: bool = False


@dataclass
class LoggingConfig(ConfigSection):
    """Logging configuration section."""
    level: LogLevel = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class PathsConfig(ConfigSection):
    """Path configuration section."""
    data_dir: str = "data"
    output_dir: str = "output"
    cache_dir: str = ".cache"


@dataclass
class Config:
    """Main configuration class."""
    app: AppConfig = field(default_factory=AppConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'app': self.app.to_dict(),
            'logging': self.logging.to_dict(),
            'paths': self.paths.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary."""
        app_data = data.get('app', {})
        logging_data = data.get('logging', {})
        paths_data = data.get('paths', {})

        return cls(
            app=AppConfig(**app_data),
            logging=LoggingConfig(**logging_data),
            paths=PathsConfig(**paths_data)
        )

    def update_from_env(self) -> None:
        """Update configuration from environment variables."""
        # App section
        if 'APP_NAME' in os.environ:
            self.app.name = os.environ['APP_NAME']
        if 'APP_VERSION' in os.environ:
            self.app.version = os.environ['APP_VERSION']
        if 'APP_DEBUG' in os.environ:
            self.app.debug = os.environ['APP_DEBUG'].lower() == 'true'

        # Logging section
        if 'APP_LOGGING_LEVEL' in os.environ:
            level = os.environ['APP_LOGGING_LEVEL'].upper()
            if level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                self.logging.level = level
            else:
                raise ConfigError(f"Invalid logging level: {level}")

        # Paths section
        if 'APP_PATHS_DATA_DIR' in os.environ:
            self.paths.data_dir = os.environ['APP_PATHS_DATA_DIR']
        if 'APP_PATHS_OUTPUT_DIR' in os.environ:
            self.paths.output_dir = os.environ['APP_PATHS_OUTPUT_DIR']
        if 'APP_PATHS_CACHE_DIR' in os.environ:
            self.paths.cache_dir = os.environ['APP_PATHS_CACHE_DIR']


_config_instance: Optional[Config] = None


def get_config(config_path: Optional[Path] = None) -> Config:
    """Get the application configuration singleton.

    Args:
        config_path: Optional path to config file

    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None or config_path is not None:
        _config_instance = load_config(config_path)
    return _config_instance


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from file and environment.

    PARAMS:
        config_path: Optional path to config file

    RETURNS:
        Config instance

    RAISES:
        ConfigError: If configuration is invalid
    """
    config = Config()

    if config_path and config_path.exists():
        # Load from file if it exists
        try:
            import toml
            data = toml.load(config_path)
            config = Config.from_dict(data)
        except Exception as e:
            raise ConfigError(f"Failed to load config from {config_path}: {e}")

    # Update with environment variables
    try:
        config.update_from_env()
    except Exception as e:
        raise ConfigError(f"Failed to update config from environment: {e}")

    return config


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added proper environment variable handling
 - Added config validation
 - Added config sections as dataclasses
 - Added proper error handling
 - Added type hints and documentation

## FUTURE TODOs:
 - Add config schema validation
 - Add config file watching
 - Add secure config handling
 - Add config versioning
"""
