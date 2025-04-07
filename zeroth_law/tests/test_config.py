"""
# PURPOSE: Test configuration loading and validation functionality

## INTERFACES:
  - test_find_pylintrc: Test finding and loading pylintrc files
  - test_load_config_with_pylint: Test loading configuration with pylint settings
  - test_load_config_with_toml: Test loading configuration with TOML settings
  - test_load_config_defaults: Test loading default configuration

## DEPENDENCIES:
    pytest
    tempfile
    os
    pathlib
"""

import pytest
import tempfile
import os
from pathlib import Path
from zeroth_law.utils.config import find_pylintrc, load_config


def test_find_pylintrc():
    """Test finding and loading pylintrc files in different locations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test pylintrc file
        pylintrc_content = """
[FORMAT]
max-line-length=120

[DESIGN]
max-args=5
max-locals=20
max-statements=50
"""
        # Test current directory
        current_pylintrc = os.path.join(temp_dir, ".pylintrc")
        with open(current_pylintrc, "w") as f:
            f.write(pylintrc_content)

        config = find_pylintrc(temp_dir)
        assert config is not None
        assert config["FORMAT"]["max-line-length"] == "120"
        assert config["DESIGN"]["max-args"] == "5"
        assert config["DESIGN"]["max-locals"] == "20"
        assert config["DESIGN"]["max-statements"] == "50"

        # Test parent directory
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        config = find_pylintrc(subdir)
        assert config is not None
        assert config["FORMAT"]["max-line-length"] == "120"


def test_load_config_with_pylint():
    """Test loading configuration with pylint settings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test pylintrc file
        pylintrc_content = """
[FORMAT]
max-line-length=120

[DESIGN]
max-args=5
max-locals=20
max-statements=50
"""
        pylintrc_path = os.path.join(temp_dir, ".pylintrc")
        with open(pylintrc_path, "w") as f:
            f.write(pylintrc_content)

        config = load_config(temp_dir)
        assert config["max_line_length"] == 120
        assert config["max_parameters"] == 5
        assert config["max_locals"] == 20
        assert config["max_function_lines"] == 50
        # Verify defaults are still present
        assert config["max_executable_lines"] == 300
        assert config["max_cyclomatic_complexity"] == 8


def test_load_config_with_toml():
    """Test loading configuration with TOML settings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test TOML config file
        toml_content = """
max_executable_lines = 400
max_cyclomatic_complexity = 10
missing_header_penalty = 15
"""
        toml_path = os.path.join(temp_dir, "config.toml")
        with open(toml_path, "w") as f:
            f.write(toml_content)

        config = load_config(toml_path)
        assert config["max_executable_lines"] == 400
        assert config["max_cyclomatic_complexity"] == 10
        assert config["missing_header_penalty"] == 15
        # Verify defaults are still present for unspecified values
        assert config["max_function_lines"] == 30
        assert config["max_parameters"] == 4


def test_load_config_with_both():
    """Test loading configuration with both pylintrc and TOML settings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test pylintrc file
        pylintrc_content = """
[FORMAT]
max-line-length=120

[DESIGN]
max-args=5
max-locals=20
max-statements=50
"""
        pylintrc_path = os.path.join(temp_dir, ".pylintrc")
        with open(pylintrc_path, "w") as f:
            f.write(pylintrc_content)

        # Create a test TOML config file
        toml_content = """
max_executable_lines = 400
max_cyclomatic_complexity = 10
missing_header_penalty = 15
"""
        toml_path = os.path.join(temp_dir, "config.toml")
        with open(toml_path, "w") as f:
            f.write(toml_content)

        config = load_config(toml_path)
        # Verify pylint settings
        assert config["max_line_length"] == 120
        assert config["max_parameters"] == 5
        assert config["max_locals"] == 20
        assert config["max_function_lines"] == 50
        # Verify TOML settings
        assert config["max_executable_lines"] == 400
        assert config["max_cyclomatic_complexity"] == 10
        assert config["missing_header_penalty"] == 15


def test_load_config_defaults():
    """Test loading default configuration when no config files exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = load_config(temp_dir)
        # Verify all default values are present
        assert config["max_executable_lines"] == 300
        assert config["max_function_lines"] == 30
        assert config["max_cyclomatic_complexity"] == 8
        assert config["max_parameters"] == 4
        assert config["missing_header_penalty"] == 20
        assert config["missing_footer_penalty"] == 10
        assert config["missing_docstring_penalty"] == 2
        assert isinstance(config["ignore_patterns"], list)
        assert len(config["ignore_patterns"]) > 0


def test_load_config_invalid_toml():
    """Test handling of invalid TOML configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create an invalid TOML file
        toml_path = os.path.join(temp_dir, "config.toml")
        with open(toml_path, "w") as f:
            f.write("invalid toml content")

        with pytest.raises(Exception):
            load_config(toml_path)


def test_load_config_invalid_pylintrc():
    """Test handling of invalid pylintrc configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create an invalid pylintrc file
        pylintrc_path = os.path.join(temp_dir, ".pylintrc")
        with open(pylintrc_path, "w") as f:
            f.write("invalid pylintrc content")

        # Should not raise an exception, just use defaults
        config = load_config(temp_dir)
        assert config["max_function_lines"] == 30  # Default value
