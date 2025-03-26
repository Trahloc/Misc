"""
# PURPOSE: Tests for project information display functionality.

## INTERFACES:
 - test_info_command: Test basic info display
 - test_info_details: Test detailed info display
 - test_info_json: Test JSON output
 - test_info_error_handling: Test error conditions
 - test_config_loading: Test configuration loading

## DEPENDENCIES:
 - pytest: Testing framework
 - click.testing: CLI testing
 - template_zeroth_law.commands.info: Info command
"""
import json
from datetime import datetime
import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from template_zeroth_law.commands.info import command
from template_zeroth_law.types import create_click_compatible_mock

@pytest.fixture
def cli_runner() -> CliRunner:
    """
    PURPOSE: Provide Click test runner.

    RETURNS: CliRunner instance
    """
    return CliRunner()


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """
    PURPOSE: Create mock configuration for testing.

    RETURNS: Mock configuration dictionary
    """
    return {
        "app": {
            "name": "test_app",
            "version": "1.0.0",
            "description": "Test application",
            "debug": False
        },
        "logging": {
            "level": "INFO",
            "format": "%(message)s"
        },
        "paths": {
            "data_dir": "data",
            "output_dir": "output",
            "cache_dir": ".cache"
        },
        "project": {
            "author": "Test Author",
            "repository": "https://github.com/test/project"
        }
    }


def test_info_command_basic(cli_runner: CliRunner, mock_config: Dict[str, Any]):
    """Test basic info command output."""
    with patch("template_zeroth_law.commands.info.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config

        # Mock logger
        ctx = MagicMock()
        ctx.obj = {"logger": MagicMock()}

        # Use isolated_filesystem to avoid file system issues
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(command, obj=ctx.obj)

            assert result.exit_code == 0
            assert mock_config["app"]["name"] in result.output
            assert mock_config["app"]["version"] in result.output
            assert mock_config["app"]["description"] in result.output


def test_info_details(cli_runner: CliRunner, mock_config: Dict[str, Any]):
    """Test detailed info command output."""
    with patch("template_zeroth_law.commands.info.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config

        # Mock logger
        ctx = MagicMock()
        ctx.obj = {"logger": MagicMock()}

        # Use isolated_filesystem to avoid file system issues
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(command, ["--details"], obj=ctx.obj)

            assert result.exit_code == 0
            # Verify standard info
            assert mock_config["app"]["name"] in result.output
            assert mock_config["app"]["version"] in result.output

            # Verify detailed info
            assert mock_config["logging"]["level"] in result.output
            assert "data_dir:" in result.output
            assert "output_dir:" in result.output
            assert mock_config["project"]["author"] in result.output

            # Verify timestamp included
            current_year = str(datetime.now().year)
            assert current_year in result.output


def test_info_json(cli_runner: CliRunner, mock_config: Dict[str, Any]):
    """Test JSON output format."""
    with patch("template_zeroth_law.commands.info.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config

        # Mock logger
        ctx = MagicMock()
        ctx.obj = {"logger": MagicMock()}

        # Use isolated_filesystem to avoid file system issues
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(command, ["--json"], obj=ctx.obj)

            assert result.exit_code == 0
            # Parse and verify JSON output
            data = json.loads(result.output)
            assert data["name"] == mock_config["app"]["name"]
            assert data["version"] == mock_config["app"]["version"]
            assert data["description"] == mock_config["app"]["description"]


def test_info_error_handling(cli_runner: CliRunner):
    """Test error handling in info command."""
    with patch("template_zeroth_law.commands.info.get_config") as mock_get_config:
        mock_get_config.side_effect = Exception("Test error")

        # Mock logger
        ctx = MagicMock()
        ctx.obj = {"logger": MagicMock()}

        result = cli_runner.invoke(command, obj=ctx.obj)

        assert result.exit_code == 1
        assert "Error" in result.output


def test_config_missing_fields(cli_runner: CliRunner):
    """Test handling of missing configuration fields."""
    minimal_config = {
        "app": {
            "name": "test_app",
            "version": "1.0.0"
        }
    }

    with patch("template_zeroth_law.commands.info.get_config") as mock_get_config:
        mock_get_config.return_value = minimal_config

        # Mock logger
        ctx = MagicMock()
        ctx.obj = {"logger": MagicMock()}

        # Use isolated_filesystem to avoid file system issues
        with cli_runner.isolated_filesystem():
            # Test with details flag
            result = cli_runner.invoke(command, ["--details"], obj=ctx.obj)

            assert result.exit_code == 0
            assert minimal_config["app"]["name"] in result.output
            assert minimal_config["app"]["version"] in result.output


def test_custom_config_sections(cli_runner: CliRunner, mock_config: Dict[str, Any]):
    """Test handling of custom configuration sections."""
    # Add a custom section
    config_with_custom = mock_config.copy()
    config_with_custom["custom"] = {
        "setting1": "value1",
        "setting2": "value2"
    }

    with patch("template_zeroth_law.commands.info.get_config") as mock_get_config:
        mock_get_config.return_value = config_with_custom

        # Mock logger
        ctx = MagicMock()
        ctx.obj = {"logger": MagicMock()}

        # Use isolated_filesystem to avoid file system issues
        with cli_runner.isolated_filesystem():
            # Test with details flag
            result = cli_runner.invoke(command, ["--details"], obj=ctx.obj)

            assert result.exit_code == 0
            # Custom section should be included in detailed output
            assert "custom" in result.output.lower()
            assert "setting1" in result.output
            assert "value1" in result.output


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added comprehensive test coverage
 - Added JSON output validation
 - Added error handling tests
 - Added config field validation
 - Added custom section handling
 - Added type hints
 - Added mock fixtures
 - Added proper docstrings
 - Added isolated_filesystem to avoid file system issues
 - Fixed MagicMock configuration issues by using plain dictionaries
 - Added proper Click compatibility for tests

## FUTURE TODOs:
 - Add tests for custom output formats
 - Add tests for config file loading
 - Add tests for environment variable overrides
 - Add performance benchmarks
"""
