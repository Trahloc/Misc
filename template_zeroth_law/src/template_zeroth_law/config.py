"""
# PURPOSE: Configuration management for the Zeroth Law template.

## INTERFACES:
 - Config: Configuration class
 - get_config: Get the current configuration singleton
 - load_config: Load configuration from a file

## DEPENDENCIES:
 - json, toml, yaml: Configuration file format parsers (yaml optional)
 - os, pathlib: File system operations

## TODO: Customize configuration handling based on project needs
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from template_zeroth_law.exceptions import ConfigError, FileError

# Global configuration instance (singleton)
_config_instance: Optional["Config"] = None


class Config:
    """
    PURPOSE: Configuration management for the Zeroth Law template.
    CONTEXT: Central configuration store for application settings
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: Configuration initialized
    RETURNS: N/A
    EXCEPTIONS: N/A
    USAGE EXAMPLES:
        >>> config = Config({"app": {"name": "my_app"}})
        >>> config.get("app.name")
        'my_app'
    """

    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """
        PURPOSE: Initialize the configuration object.
        CONTEXT: Constructor for the Config class
        PRE-CONDITIONS & ASSUMPTIONS: None
        PARAMS:
            config_data (Optional[Dict[str, Any]]): Initial configuration data
        POST-CONDITIONS & GUARANTEES: Configuration object is initialized
        RETURNS: None
        EXCEPTIONS: None
        """
        self.data = config_data or {}

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        PURPOSE: Get a configuration value by key path.
        CONTEXT: Configuration value retrieval
        PRE-CONDITIONS & ASSUMPTIONS: None
        PARAMS:
            key_path (str): Dot-separated path to the configuration value
            default (Any): Default value if key doesn't exist
        POST-CONDITIONS & GUARANTEES: None
        RETURNS:
            Any: Configuration value or default
        EXCEPTIONS:
            None: Returns default instead of raising exception
        USAGE EXAMPLES:
            >>> config = Config({"app": {"debug": True}})
            >>> config.get("app.debug")
            True
            >>> config.get("app.name", "default_name")
            'default_name'
        """
        parts = key_path.split(".")
        value = self.data

        for part in parts:
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]

        return value

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "Config":
        """
        PURPOSE: Create a Config instance from a configuration file.
        CONTEXT: Factory method for creating config from file
        PRE-CONDITIONS & ASSUMPTIONS: File exists and is in a supported format
        PARAMS:
            file_path (Union[str, Path]): Path to configuration file
        POST-CONDITIONS & GUARANTEES: Config loaded with file contents
        RETURNS:
            Config: New configuration instance
        EXCEPTIONS:
            FileError: If file doesn't exist or can't be read
            ConfigError: If file format is not supported or content is invalid
        USAGE EXAMPLES:
            >>> config = Config.from_file("config.json")  # doctest: +SKIP
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileError(
                f"Configuration file not found: {file_path}", path=str(file_path)
            )

        suffix = file_path.suffix.lower()

        try:
            with open(file_path, "r") as f:
                if suffix == ".json":
                    data = json.load(f)
                elif suffix == ".toml":
                    try:
                        import toml

                        data = toml.load(f)
                    except ImportError:
                        raise ConfigError(
                            "TOML support requires 'toml' package", format="toml"
                        )
                elif suffix in (".yaml", ".yml"):
                    try:
                        import yaml

                        data = yaml.safe_load(f)
                    except ImportError:
                        raise ConfigError(
                            "YAML support requires 'pyyaml' package", format="yaml"
                        )
                else:
                    raise ConfigError(
                        f"Unsupported config format: {suffix}", format=suffix
                    )

            return cls(data)

        except (json.JSONDecodeError, ValueError) as e:
            raise ConfigError(f"Invalid configuration format: {e}", path=str(file_path))


def get_config() -> Config:
    """
    PURPOSE: Get the current configuration singleton.
    CONTEXT: Global configuration access
    PRE-CONDITIONS & ASSUMPTIONS: Configuration has been initialized
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS:
        Config: Current configuration instance
    EXCEPTIONS:
        ConfigError: If configuration hasn't been initialized
    USAGE EXAMPLES:
        >>> # First initialize config
        >>> _ = load_config({"app": {"name": "example"}})
        >>> # Then retrieve it
        >>> config = get_config()
        >>> config.get("app.name")
        'example'
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def load_config(config_data: Union[Dict[str, Any], str, Path]) -> Config:
    """
    PURPOSE: Load configuration and set as singleton.
    CONTEXT: Global configuration initialization
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS:
        config_data (Union[Dict[str, Any], str, Path]): Configuration data or file path
    POST-CONDITIONS & GUARANTEES: Global configuration is set
    RETURNS:
        Config: The loaded configuration instance
    EXCEPTIONS:
        FileError: If file doesn't exist or can't be read
        ConfigError: If file format is not supported or content is invalid
    USAGE EXAMPLES:
        >>> config = load_config({"app": {"name": "my_app"}})
        >>> config.get("app.name")
        'my_app'
    """
    global _config_instance

    if isinstance(config_data, (str, Path)):
        _config_instance = Config.from_file(config_data)
    else:
        _config_instance = Config(config_data)

    return _config_instance


"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Simplified configuration handling while maintaining flexibility
## FUTURE TODOs: Add environment variable support, add schema validation
"""
