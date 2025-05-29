"""
# PURPOSE: Tests for configuration management.

## INTERFACES:
 - test_config_default_values: Test default configuration values
 - test_config_env_override: Test environment variable overrides
 - test_config_type_conversion: Test type conversion
 - test_config_invalid_file: Test invalid config handling
 - test_config_immutability: Test config immutability

## DEPENDENCIES:
 - pytest: Testing framework
 - template_zeroth_law.config: Configuration module
"""

from pathlib import Path
from typing import Any, Dict

import pytest

from template_zeroth_law.config import Config, get_config, load_config
from template_zeroth_law.exceptions import ConfigError


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Provide test configuration data."""
    return {
        "app": {
            "name": "test_app",
            "version": "1.0.0",
            "description": "Test application",
            "debug": False,
        },
        "logging": {"level": "INFO", "format": "%(message)s"},
        "paths": {"data_dir": "data", "output_dir": "output", "cache_dir": ".cache"},
    }


def test_config_default_values():
    """Test that default configuration has expected values."""
    config = Config()
    assert config.app.name == "template_zeroth_law"
    assert config.logging.level == "INFO"
    assert config.paths.data_dir == "data"


def test_config_env_override(monkeypatch: pytest.MonkeyPatch):
    """Test environment variable overrides."""
    monkeypatch.setenv("APP_LOGGING_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_PATHS_DATA_DIR", "/custom/path")

    config = Config()
    config.update_from_env()

    assert config.logging.level == "DEBUG"
    assert config.paths.data_dir == "/custom/path"


def test_config_type_conversion(monkeypatch: pytest.MonkeyPatch):
    """Test configuration type conversion."""
    monkeypatch.setenv("APP_DEBUG", "true")

    config = Config()
    config.update_from_env()

    assert isinstance(config.app.debug, bool)
    assert config.app.debug is True


def test_config_invalid_file():
    """Test handling of invalid configuration file."""
    with pytest.raises(ConfigError):
        load_config(Path("nonexistent.toml"))


def test_config_to_dict():
    """Test configuration serialization to dictionary."""
    config = Config()
    data = config.to_dict()

    assert isinstance(data, dict)
    assert "app" in data
    assert "logging" in data
    assert "paths" in data


def test_config_from_dict(mock_config: Dict[str, Any]):
    """Test configuration creation from dictionary."""
    config = Config.from_dict(mock_config)

    assert config.app.name == mock_config["app"]["name"]
    assert config.logging.level == mock_config["logging"]["level"]
    assert config.paths.data_dir == mock_config["paths"]["data_dir"]


def test_singleton_config():
    """Test that get_config returns singleton instance."""
    config1 = get_config()
    config2 = get_config()

    assert config1 is config2


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Updated tests for new config implementation
 - Added comprehensive test coverage
 - Added proper fixtures
 - Added type hints
 - Added descriptive docstrings

## FUTURE TODOs:
 - Add performance tests
 - Add stress tests
 - Add security tests
"""
