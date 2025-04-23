# File: tests/test_cli.py
"""Tests for the command-line interface (cli.py)."""

import os
import subprocess
import sys
from pathlib import Path
import click
import pytest
import importlib
import logging
import toml

from click.testing import CliRunner

# Import cli_module itself
import src.zeroth_law.cli as cli_module
from src.zeroth_law.config_loader import load_config
from src.zeroth_law.file_finder import find_python_files
from src.zeroth_law.cli import add_dynamic_commands

# Ensure src is in path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent / "src"))

# Setup basic logging for tests that might use it implicitly
logger = logging.getLogger(__name__)


# Helper to get path to CLI test data file
def get_cli_test_data_path(filename: str) -> Path:
    return Path(__file__).parent / "data" / "cli" / filename


def test_restore_hooks_not_git_repo(mocker, tmp_path: Path, caplog):
    """Test restore hooks failure if the target directory isn't a Git repo."""
    # Arrange
    # Mock subprocess.run to simulate pre-commit install failure
    mock_run = mocker.patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(
            1, ["pre-commit", "install"], output="", stderr="Git repository not found"
        ),
    )

    # Act
    original_cwd = Path.cwd()
    os.chdir(tmp_path)  # Change CWD to the temp dir
    try:
        from src.zeroth_law.git_utils import restore_standard_hooks

        restore_standard_hooks(tmp_path)
    except ValueError as e:
        # Expected exception due to pre-commit install failure
        pass
    finally:
        os.chdir(original_cwd)

    # Assert
    # Check the captured log messages for failure indicators
    assert "'pre-commit install' failed" in caplog.text, f"Missing expected error in logs: {caplog.text}"
    assert (
        "Please check your pre-commit setup and try running manually." in caplog.text
    ), f"Missing expected error summary in logs: {caplog.text}"


def test_cli_runs():
    runner = CliRunner()
    result = runner.invoke(cli_module.cli_group, ["--help"])
    assert result.exit_code == 0
    assert "Usage: cli-group" in result.output


def test_zlt_lint_loads_and_runs(tmp_path, monkeypatch):
    """Verify the lint command loads and executes basic checks."""
    # Arrange
    # Instantiate CliRunner with mix_stderr=False
    runner = CliRunner(mix_stderr=False)
    # monkeypatch.setattr(sys, "argv", ["zlt", "lint"]) # Not needed for CliRunner

    # Create dummy pyproject.toml in tmp_path (which is the CWD due to fixture)
    config_content_str = """
[tool.zeroth-law]
actions = { lint = { description = "Run check-yaml.", tools = ["check-yaml"] } }
"""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text(config_content_str)
    logger.debug(f"Created dummy config: {config_file}")

    # Load the dummy config string into a dictionary
    try:
        loaded_config = toml.loads(config_content_str)
        # Extract the relevant part for add_dynamic_commands (the [tool.zeroth-law] table)
        test_config = loaded_config.get("tool", {}).get("zeroth-law", {})
        if not test_config:
            pytest.fail("Failed to load or parse dummy [tool.zeroth-law] config for test.")
    except toml.TomlDecodeError as e:
        pytest.fail(f"Failed to parse dummy TOML config: {e}\nContent:\n{config_content_str}")

    # Create a dummy file to lint
    dummy_file = tmp_path / "dummy.yaml"
    dummy_file.write_text("key: value\n")
    logger.debug(f"Created dummy file: {dummy_file}")

    # Ensure CWD is correct (handled by fixture, but double-check)
    monkeypatch.chdir(tmp_path)  # Redundant if fixture works, but safe
    logger.debug(f"Confirmed CWD: {Path.cwd()}")

    # Explicitly add dynamic commands *after* environment setup, passing the loaded config
    add_dynamic_commands(cli_module.cli_group, config=test_config)
    logger.debug(f"Dynamically added commands. Available: {list(cli_module.cli_group.commands.keys())}")

    # Act
    # Pass the command and arguments as a list
    # Pass the loaded test_config into the context object
    result = runner.invoke(
        cli_module.cli_group,
        ["lint", str(dummy_file)],
        obj={"config": test_config, "project_root": tmp_path},  # Explicitly set context
        catch_exceptions=False,
    )

    # Debug: Print output if assertion fails
    if result.exit_code != 0:
        print("CLI Output:")
        print(result.output)
        print("CLI Exception:")
        print(result.exception)
        print(f"Invoked with args: ['lint', '{str(dummy_file)}']")
        print(f"Commands available in cli_group: {list(cli_module.cli_group.commands.keys())}")
        if hasattr(result, "stderr") and result.stderr:  # Print stderr if available
            print(f"CLI Stderr:\n{result.stderr}")

    # Assert
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    # Add more specific assertions about the output if needed
    # assert "check-yaml ran" in result.output # Example, adjust based on actual output


# Add more tests for different scenarios, options, and error handling
# e.g., test with no config, test with invalid config, test with verbose/quiet flags
