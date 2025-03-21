# FILE_LOCATION: hugsearch/tests/hugsearch/test_config.py
"""
# PURPOSE: Tests for hugsearch.config.

## INTERFACES:
#   test_config_exists: Verify the module exists.
#   test_default_config: Test the default configuration values.
#   test_get_config: Test the get_config function.
#   test_load_config: Test the load_config function.

## DEPENDENCIES:
#   pytest
#   hugsearch.config
#   json
#   tempfile
"""
import json
import tempfile
import os
import pytest
from hugsearch.config import get_config, load_config, DEFAULT_CONFIG

def test_config_exists():
    """
    PURPOSE: Verify that the config module exists.

    PARAMS: None

    RETURNS: None
    """
    # This import will raise an ImportError if the module doesn't exist
    from hugsearch import config
    assert config

def test_default_config():
    """
    PURPOSE: Test that the default configuration has expected values.

    PARAMS: None

    RETURNS: None
    """
    # Verify some key default configuration values
    assert DEFAULT_CONFIG["limits"]["max_line_length"] == 140
    assert DEFAULT_CONFIG["limits"]["max_function_lines"] == 30
    assert DEFAULT_CONFIG["limits"]["max_parameters"] == 7
    assert "ignore_patterns" in DEFAULT_CONFIG
    assert isinstance(DEFAULT_CONFIG["ignore_patterns"], list)
    # Check that some expected patterns are in the ignore list
    assert any("__pycache__" in pattern for pattern in DEFAULT_CONFIG["ignore_patterns"])
    assert any(".git" in pattern for pattern in DEFAULT_CONFIG["ignore_patterns"])

def test_get_config():
    """
    PURPOSE: Test that get_config returns a Config object with the default values.

    PARAMS: None

    RETURNS: None
    """
    config = get_config()
    # Check it's a Config object
    from hugsearch.config import Config
    assert isinstance(config, Config)
    
    # Check it has the expected values
    assert config.limits.max_line_length == 140
    assert config.limits.max_function_lines == 30
    
    # Test dictionary access
    assert config["limits"]["max_line_length"] == 140
    assert config["limits"]["max_function_lines"] == 30

def test_load_config():
    """
    PURPOSE: Test that load_config properly loads and merges configuration.

    PARAMS: None

    RETURNS: None
    """
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp:
        # Write a partial config
        json.dump({"limits": {"max_line_length": 120}, "custom_setting": "test"}, temp)
        temp_path = temp.name
    
    try:
        # Test loading the config
        config = load_config(temp_path)
        
        # Check merged values
        assert config.limits.max_line_length == 120  # From custom config
        assert config.limits.max_function_lines == 30  # From default config
        assert config.custom_setting == "test"  # New in custom config
    finally:
        # Clean up
        os.unlink(temp_path)

def test_load_config_file_not_found():
    """
    PURPOSE: Test that load_config returns default config when file is not found.

    PARAMS: None

    RETURNS: None
    """
    # Test with a non-existent file
    config = load_config("non_existent_config.json")
    assert config.limits.max_line_length == 140
    assert config.limits.max_function_lines == 30

def test_load_config_invalid_json():
    """
    PURPOSE: Test that load_config raises an exception for invalid JSON.

    PARAMS: None

    RETURNS: None
    """
    # Create a temporary file with invalid JSON
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp:
        temp.write("{invalid json")
        temp_path = temp.name
    
    try:
        # Direct test of _load_from_file function to ensure it raises ValueError
        from hugsearch.config import _load_from_file
        try:
            _load_from_file(temp_path)
            assert False, "_load_from_file did not raise ValueError"
        except ValueError:
            print("_load_from_file correctly raised ValueError")
        
        # Let's try calling load_config directly without pytest.raises
        try:
            config = load_config(temp_path)
            print(f"load_config did not raise an exception, returned: {config}")
            assert False, "load_config did not raise ValueError"
        except ValueError as e:
            print(f"load_config correctly raised ValueError: {e}")
            pass  # This is expected
        except Exception as e:
            print(f"load_config raised unexpected exception: {type(e).__name__}: {e}")
            raise  # Re-raise any other exceptions
    finally:
        # Clean up
        os.unlink(temp_path)
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added comprehensive tests for config module
 - Tests for default configuration values
 - Tests for config loading and merging
 - Tests for error handling

## FUTURE TODOs:
 - Add tests for additional configuration scenarios if needed
""" 