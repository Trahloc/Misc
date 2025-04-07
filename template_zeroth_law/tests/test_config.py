"""
# PURPOSE: Test configuration management functionality.

## INTERFACES: N/A (Test module)
## DEPENDENCIES:
 - pytest: Testing framework
 - template_zeroth_law.config: Configuration handling
 - template_zeroth_law.exceptions: Custom exception classes

## TODO: Add more test cases as needed
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from template_zeroth_law.config import Config, get_config, load_config
from template_zeroth_law.exceptions import ConfigError, FileError


def test_config_init():
    """
    PURPOSE: Test Config initialization
    CONTEXT: Unit test for configuration constructor
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS: None
    EXCEPTIONS: None
    """
    # Create empty config
    config = Config()
    assert config.data == {}

    # Create config with data
    test_data = {"app": {"name": "test", "debug": True}}
    config = Config(test_data)
    assert config.data == test_data


def test_config_get():
    """
    PURPOSE: Test Config.get method
    CONTEXT: Unit test for configuration value retrieval
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS: None
    EXCEPTIONS: None
    """
    # Set up test data
    test_data = {"app": {"name": "test", "debug": True}, "logging": {"level": "INFO"}}
    config = Config(test_data)

    # Test valid paths
    assert config.get("app.name") == "test"
    assert config.get("app.debug") is True
    assert config.get("logging.level") == "INFO"

    # Test invalid paths with defaults
    assert config.get("app.version", "0.1.0") == "0.1.0"
    assert config.get("database", {}) == {}
    assert config.get("invalid.path", None) is None


def test_config_from_file():
    """
    PURPOSE: Test Config.from_file factory method
    CONTEXT: Unit test for configuration loading from file
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS: None
    EXCEPTIONS: None
    """
    # Create a temporary JSON config file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp:
        test_data = {"app": {"name": "file_test", "debug": False}}
        temp.write(json.dumps(test_data).encode())
        temp_path = temp.name

    try:
        # Load config from file
        config = Config.from_file(temp_path)

        # Test loaded data
        assert config.data == test_data
        assert config.get("app.name") == "file_test"
        assert config.get("app.debug") is False

        # Test with non-existent file
        with pytest.raises(FileError):
            Config.from_file("non_existent_file.json")

        # Test with invalid path type
        with pytest.raises(AttributeError):
            Config.from_file(None)

    finally:
        # Clean up temp file
        os.unlink(temp_path)


def test_get_config_singleton():
    """
    PURPOSE: Test get_config and load_config functions
    CONTEXT: Unit test for configuration singleton pattern
    PRE-CONDITIONS & ASSUMPTIONS: None
    PARAMS: None
    POST-CONDITIONS & GUARANTEES: None
    RETURNS: None
    EXCEPTIONS: None
    """
    # Load initial config
    test_data = {"app": {"name": "singleton_test"}}
    config1 = load_config(test_data)

    # Get config should return the same instance
    config2 = get_config()
    assert config1 is config2
    assert config2.get("app.name") == "singleton_test"

    # Load new config
    new_data = {"app": {"name": "updated_test"}}
    config3 = load_config(new_data)

    # Get config should return the updated instance
    config4 = get_config()
    assert config3 is config4
    assert config4.get("app.name") == "updated_test"


"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Added comprehensive test cases for configuration management
## FUTURE TODOs: Add tests for TOML and YAML configuration formats
"""
