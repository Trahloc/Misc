"""
# PURPOSE: Tests for version command functionality and package version detection.

## INTERFACES:
 - test_version_command: Test basic version command
 - test_version_verbose: Test verbose version output
 - test_version_json: Test JSON version output
 - test_version_error_handling: Test error conditions
 - test_package_version_detection: Test package version detection

## DEPENDENCIES:
 - pytest: Testing framework
 - click.testing: CLI testing
 - template_zeroth_law.commands.version: Version command
"""

import json
from typing import Any, Dict, Tuple
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from template_zeroth_law.commands.version import command, get_package_version


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
        }
    }


@pytest.fixture
def cli_runner() -> CliRunner:
    """
    PURPOSE: Provide Click test runner.
    RETURNS: CliRunner instance
    """
    return CliRunner()


def test_version_command_basic(cli_runner: CliRunner, mock_config: Dict[str, Any]):
    """
    Test basic version command output.
    """
    with patch("template_zeroth_law.commands.version.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config

        # Mock logger
        ctx = MagicMock()
        ctx.obj = {"logger": MagicMock()}

        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(command, obj=ctx.obj)

            assert result.exit_code == 0
            assert "test_app v1.0.0" in result.output


def test_version_verbose(cli_runner: CliRunner, mock_config: Dict[str, Any]):
    """
    Test verbose version command output.
    """
    with patch("template_zeroth_law.commands.version.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config

        # Mock package version detection
        with patch(
            "template_zeroth_law.commands.version.get_package_version"
        ) as mock_get_version:
            mock_get_version.return_value = "1.0.0"

            # Mock logger
            ctx = MagicMock()
            ctx.obj = {"logger": MagicMock()}

            with cli_runner.isolated_filesystem():
                result = cli_runner.invoke(command, ["--verbose"], obj=ctx.obj)

                assert result.exit_code == 0
                assert "Description:" in result.output
                assert "Python:" in result.output
                assert "Platform:" in result.output
                assert "Dependencies:" in result.output


def test_version_json(cli_runner: CliRunner, mock_config: Dict[str, Any]):
    """
    Test JSON version command output.
    """
    with patch("template_zeroth_law.commands.version.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config

        # Mock logger
        ctx = MagicMock()
        ctx.obj = {"logger": MagicMock()}

        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(command, ["--json"], obj=ctx.obj)

            assert result.exit_code == 0
            # Verify JSON output
            data = json.loads(result.output)
            assert data["name"] == "test_app"
            assert data["version"] == "1.0.0"
            assert data["description"] == "Test application"


@pytest.mark.parametrize(
    "py_version,expected_func",
    [
        ((3, 8), "pkg_resources.get_distribution"),
        ((3, 11), "importlib.metadata.version"),
    ],
)
def test_package_version_detection(py_version: Tuple[int, ...], expected_func: str):
    """
    Test package version detection with different Python versions.
    """
    with patch("sys.version_info", py_version):
        if py_version >= (3, 8):
            with patch("importlib.metadata.version") as mock_version:
                mock_version.return_value = "1.0.0"
                assert get_package_version("test_package") == "1.0.0"
                mock_version.assert_called_once_with("test_package")
        else:
            with patch("pkg_resources.get_distribution") as mock_dist:
                mock_dist.return_value = MagicMock(version="1.0.0")
                assert get_package_version("test_package") == "1.0.0"
                mock_dist.assert_called_once_with("test_package")


def test_version_error_handling(cli_runner: CliRunner):
    """
    Test error handling in version command.
    """
    with patch("template_zeroth_law.commands.version.get_config") as mock_get_config:
        mock_get_config.side_effect = Exception("Test error")

        # Mock logger
        ctx = MagicMock()
        ctx.obj = {"logger": MagicMock()}

        result = cli_runner.invoke(command, obj=ctx.obj)

        assert result.exit_code == 1
        assert "Error" in result.output


def test_version_package_not_found(cli_runner: CliRunner, mock_config: Dict[str, Any]):
    """
    Test handling of missing package version information.
    """
    with patch("template_zeroth_law.commands.version.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config

        with patch(
            "template_zeroth_law.commands.version.get_package_version"
        ) as mock_get_version:
            mock_get_version.return_value = "unknown"

            # Mock logger
            ctx = MagicMock()
            ctx.obj = {"logger": MagicMock()}

            with cli_runner.isolated_filesystem():
                result = cli_runner.invoke(command, ["--verbose"], obj=ctx.obj)

                assert result.exit_code == 0
                assert "unknown" in result.output


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added comprehensive test coverage
 - Added dependency version testing
 - Added error handling tests
 - Added JSON output validation
 - Added Python version compatibility tests
 - Added mock configuration fixture
 - Added proper type hints
 - Fixed Click compatibility issues with proper typing
 - Added isolated_filesystem for testing
 - Used plain dictionaries instead of MagicMock for config

## FUTURE TODOs:
 - Add tests for Git version information
 - Add tests for build date information
 - Add tests for license information
 - Add performance benchmarks
"""
