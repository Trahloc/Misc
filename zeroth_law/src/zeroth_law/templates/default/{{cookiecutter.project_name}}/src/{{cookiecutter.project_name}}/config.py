# FILE_LOCATION: {{ cookiecutter.project_name }}/src/zeroth_law_template/config.py
"""
# PURPOSE: Comprehensive configuration management.

## INTERFACES:
 - load_config(config_path: Optional[str] = None) -> Config: Load configuration from multiple sources
 - get_config(config_path: Optional[str] = None) -> Config: Get the current configuration
 - Config: Configuration class with attribute access

## DEPENDENCIES:
 - json: JSON parsing
 - os: Environment variables
 - yaml: YAML parsing (optional)
 - tomli: TOML parsing (for Python < 3.11)
 - tomllib: TOML parsing (for Python >= 3.11)
 - typing: Type hints
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from {{ cookiecutter.project_name }}.utils import merge_dicts, get_project_root

# Define default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "name": "{{ cookiecutter.project_name }}",
        "version": "0.1.0",
        "description": "A project created with the Zeroth Law AI Framework",
        "debug": False,
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "log_file": None,
    },
    "paths": {
        "data_dir": "data",
        "output_dir": "output",
        "cache_dir": ".cache",
    },
    "limits": {
        "max_line_length": 140,
        "min_docstring_length": 10,
        "max_executable_lines": 300,
        "max_function_lines": 30,
        "max_function_length": 30,
        "max_cyclomatic_complexity": 8,
        "max_parameters": 7,
    },
    "penalties": {
        "missing_header_penalty": 20,
        "missing_footer_penalty": 10,
        "missing_docstring_penalty": 2,
    },
    "ignore_patterns": [
        "**/__pycache__/**",
        "**/.git/**",
        "**/.venv/**",
        "**/venv/**",
        "**/*.pyc",
        "**/.pytest_cache/**",
        "**/.coverage",
        "**/htmlcov/**",
        ".*\\.egg-info.*",
    ]
}

_config_instance = None

class Config:
    """
    Configuration class with attribute and dictionary access to config values.
    
    Allows accessing configuration values using both attribute notation (config.app.name)
    and dictionary notation (config['app']['name']).
    """
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize with a configuration dictionary.
        
        Args:
            config_dict: Dictionary containing configuration values
        """
        self._config = config_dict
        
    def __getattr__(self, name: str) -> Any:
        """
        Access configuration values as attributes.
        
        Args:
            name: Attribute name to access
            
        Returns:
            The configuration value, or a Config object for nested dictionaries
            
        Raises:
            AttributeError: If the attribute does not exist
        """
        if name in self._config:
            value = self._config[name]
            if isinstance(value, dict):
                return Config(value)
            return value
        raise AttributeError(f"No configuration value for '{name}'")
    
    def __getitem__(self, key: str) -> Any:
        """
        Access configuration values as dictionary items.
        
        Args:
            key: Key to access
            
        Returns:
            The configuration value, or a Config object for nested dictionaries
            
        Raises:
            KeyError: If the key does not exist
        """
        if key in self._config:
            value = self._config[key]
            if isinstance(value, dict):
                return Config(value)
            return value
        raise KeyError(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with a default if not found.
        
        Args:
            key: Key to access
            default: Default value to return if key is not found
            
        Returns:
            The configuration value or the default
        """
        value = self._config.get(key, default)
        if isinstance(value, dict):
            return Config(value)
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this config back to a dictionary.
        
        Returns:
            A deep copy of the configuration dictionary
        """
        return self._config.copy()

def _load_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load configuration from a file based on its extension.
    
    Supports JSON, YAML, and TOML file formats. The file format is determined
    by the file extension.
    
    Args:
        file_path: Path to the configuration file
        
    Returns:
        Dictionary with configuration values from the file
        
    Raises:
        ValueError: If the file format is unsupported or if the file contains
                   invalid syntax
        ImportError: If required dependencies for YAML or TOML parsing are missing
    """
    path = Path(file_path)
    
    if not path.exists():
        return {}
    
    if path.suffix.lower() == '.json':
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}") from e
    elif path.suffix.lower() in ('.yaml', '.yml'):
        if not YAML_AVAILABLE:
            raise ImportError("YAML configuration requires PyYAML. Install with: pip install PyYAML")
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    elif path.suffix.lower() == '.toml':
        if tomllib is None:
            raise ImportError("TOML configuration requires tomli (Python < 3.11). Install with: pip install tomli")
        with open(path, 'rb') as f:
            return tomllib.load(f)
    else:
        raise ValueError(f"Unsupported config file format: {path.suffix}")

def _load_from_env(prefix: str = "APP_") -> Dict[str, Any]:
    """
    Load configuration from environment variables with the given prefix.
    
    Environment variables are converted to a nested dictionary structure. For example,
    APP_LOGGING_LEVEL=DEBUG becomes {'logging': {'level': 'DEBUG'}}.
    
    Args:
        prefix: Prefix for environment variables to consider (default: "APP_")
        
    Returns:
        Dictionary with configuration values from environment variables
    """
    result: Dict[str, Any] = {}
    
    for key, value in os.environ.items():
        if key.startswith(prefix):
            # Convert APP_LOGGING_LEVEL to config['logging']['level']
            parts = key[len(prefix):].lower().split('_')
            
            # Handle boolean values
            if value.lower() in ('true', 'yes', '1'):
                value = True
            elif value.lower() in ('false', 'no', '0'):
                value = False
            # Handle integer values
            elif value.isdigit():
                value = int(value)
            # Handle float values
            elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                value = float(value)
            
            # Build nested dict structure
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            current[parts[-1]] = value
    
    return result

def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from multiple sources in this order:
    1. Default values
    2. Configuration file (if provided)
    3. Environment variables (APP_*)
    
    Returns a Config object with all merged values.
    
    Args:
        config_path: Optional path to a configuration file
        
    Returns:
        Config object with merged configuration values
        
    Raises:
        ValueError: If the configuration file exists but contains invalid syntax
    """
    global _config_instance
    
    # Start with default config
    config_dict = DEFAULT_CONFIG.copy()
    
    # Look for config files in common locations if not specified
    if not config_path:
        # Look for config files in standard locations
        project_root = get_project_root()
        config_locations = [
            project_root / "config.yaml",
            project_root / "config.yml",
            project_root / "config.json",
            project_root / "config.toml",
            project_root / "config" / "config.yaml",
            project_root / "config" / "config.yml",
            project_root / "config" / "config.json",
            project_root / "config" / "config.toml",
        ]
        
        for location in config_locations:
            if location.exists():
                config_path = str(location)
                break
    
    # Load from config file if provided or found
    if config_path:
        # We no longer catch exceptions here to allow ValueError to propagate
        file_config = _load_from_file(config_path)
        config_dict = merge_dicts(config_dict, file_config)
    
    # Load from environment variables
    env_config = _load_from_env()
    config_dict = merge_dicts(config_dict, env_config)
    
    # Create and store the config instance
    _config_instance = Config(config_dict)
    return _config_instance

def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get the current configuration, loading default if not already loaded.
    
    This function is used to access the configuration throughout the application.
    If the configuration has not been loaded yet, it will be loaded using the
    default settings.
    
    Args:
        config_path: Optional path to a configuration file
        
    Returns:
        Config object with the current configuration
    """
    global _config_instance
    if _config_instance is None or config_path is not None:
        return load_config(config_path)
    return _config_instance

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added support for YAML and TOML configs
 - Added environment variable configuration
 - Added attribute-based access to config values
 - Organized config into logical sections

## FUTURE TODOs:
 - Add schema validation for configurations
 - Add support for encrypted secrets
 - Add dynamic reloading of configuration
"""