# FILE_LOCATION: source_project2/tests/source_project2/test_config.py
"""
# PURPOSE: Tests for source_project2.config.

## INTERFACES:
#   test_config_exists: Verify the module exists.
#   test_default_config: Test the default configuration values.
#   test_get_config: Test the get_config function.
#   test_load_config: Test the load_config function.

## DEPENDENCIES:
#   pytest
#   source_project2.config
#   json
#   tempfile
"""
import json
import tempfile
import os
import pytest
from {{ cookiecutter.project_name }}.config import get_config, load_config, DEFAULT_CONFIG

def test_config_exists():
    """
    PURPOSE: Verify that the config module exists.

    PARAMS: None

    RETURNS: None
    """
    # This import will raise an ImportError if the module doesn't exist
    from {{ cookiecutter.project_name }} import config
    assert config

def test_default_config():
    """
    PURPOSE: Test that the default configuration has expected values.

    PARAMS: None

    RETURNS: None
    """
    # Verify some key default configuration values
    assert DEFAULT_CONFIG["max_line_length"] == 140
    assert DEFAULT_CONFIG["max_function_lines"] == 30
    assert DEFAULT_CONFIG["max_parameters"] == 7
    assert "ignore_patterns" in DEFAULT_CONFIG
    assert isinstance(DEFAULT_CONFIG["ignore_patterns"], list)
    # Check that some expected patterns are in the ignore list
    assert any("__pycache__" in pattern for pattern in DEFAULT_CONFIG["ignore_patterns"])
    assert any(".git" in pattern for pattern in DEFAULT_CONFIG["ignore_patterns"])

def test_get_config():
    """
    PURPOSE: Test that get_config returns a copy of the default config.

    PARAMS: None

    RETURNS: None
    """
    config = get_config()
    # Check it's a copy, not the same object
    assert config is not DEFAULT_CONFIG
    # But has the same values
    assert config == DEFAULT_CONFIG
    
    # Modifying the returned config should not affect DEFAULT_CONFIG
    config["max_line_length"] = 999
    assert DEFAULT_CONFIG["max_line_length"] == 140

def test_load_config():
    """
    PURPOSE: Test that load_config properly loads and merges configuration.

    PARAMS: None

    RETURNS: None
    """
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp:
        # Write a partial config
        json.dump({"max_line_length": 120, "custom_setting": "test"}, temp)
        temp_path = temp.name
    
    try:
        # Test loading the config
        config = load_config(temp_path)
        
        # Check merged values
        assert config["max_line_length"] == 120  # From custom config
        assert config["max_function_lines"] == 30  # From default config
        assert config["custom_setting"] == "test"  # New in custom config
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
    assert config == DEFAULT_CONFIG

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
        # Test loading the invalid config
        with pytest.raises(ValueError):
            load_config(temp_path)
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