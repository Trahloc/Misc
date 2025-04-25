# File: tests/test_cli_json_output.py
"""Tests for the JSON output functionality in the CLI."""

import json
import logging
import os  # Import os for chdir
import sys
from pathlib import Path
import toml

import pytest
from click.testing import CliRunner

# Import cli_module itself
import src.zeroth_law.cli as cli_module

# Import the function to add dynamic commands
from src.zeroth_law.cli import add_dynamic_commands


# Assuming project root is detectable or tests run from root
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # Adjust if tests are not in 'tests' subdir

# Add src to path to allow importing the cli module
current_dir = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


# Helper function to create temporary project environment (Keep or remove based on usage)
# def setup_temp_project(tmp_path: Path, action_config: str): ...


# Helper function to create pyproject.toml string (Keep or remove based on usage)
# def create_test_config(lint_action_data): ...


@pytest.mark.parametrize("with_json_flag", [True, False])
def test_cli_json_output_flag(tmp_path, monkeypatch, with_json_flag):
    """Verify the --json flag correctly outputs JSON or standard text."""
    # Instantiate CliRunner with mix_stderr=False
    runner = CliRunner(mix_stderr=False)

    # Create dummy pyproject.toml
    config_content_str = """
[tool.zeroth-law]
actions = { lint = { description = "Run check-yaml.", tools = ["check-yaml"] } }
    """
    (tmp_path / "pyproject.toml").write_text(config_content_str)

    # Load the dummy config string into a dictionary
    try:
        loaded_config = toml.loads(config_content_str)
        test_config = loaded_config.get("tool", {}).get("zeroth-law", {})
        if not test_config:
            pytest.fail("Failed to load or parse dummy [tool.zeroth-law] config for test.")
    except toml.TomlDecodeError as e:
        pytest.fail(f"Failed to parse dummy TOML config: {e}\nContent:\n{config_content_str}")

    # Create a dummy file to lint
    dummy_file = tmp_path / "dummy.yaml"
    dummy_file.write_text("key: value\n")

    # Change CWD to the temp project dir
    monkeypatch.chdir(tmp_path)

    # Explicitly add dynamic commands AFTER CWD is changed, passing config
    add_dynamic_commands(cli_module.cli_group, config=test_config)
    logging.debug(f"Dynamically added commands. Available: {list(cli_module.cli_group.commands.keys())}")

    # Prepare command arguments
    # The global --json flag is handled by the main cli_group context now
    # The dynamic command stub might have its own hidden --output-json, but we invoke via global flag
    invoke_args = ["lint", str(dummy_file)]
    # Note: We are testing the GLOBAL --json flag set on cli_group, not one potentially defined per-action
    cli_runner_args = {"args": invoke_args}
    if with_json_flag:
        cli_runner_args["args"] = ["--json"] + invoke_args  # Prepend global flag

    # Act
    # Pass the args dictionary to invoke and set the context obj
    result = runner.invoke(
        cli_module.cli_group,
        **cli_runner_args,
        obj={"config": test_config, "project_root": tmp_path, "is_json_output": with_json_flag},
        catch_exceptions=False,
    )

    # Assert
    if result.exit_code != 0:
        # Print stdout and stderr if the command failed
        print(f"Command failed. stdout:\n{result.stdout}")
        print(f"Command failed. stderr:\n{result.stderr}")  # Access stderr safely now
        if hasattr(result, "exception"):
            print(f"Exception: {result.exception}")
        # Use the args list passed to invoke, not result.args
        pytest.fail(f"CLI command {' '.join(cli_runner_args['args'])} failed with exit code {result.exit_code}")

    if with_json_flag:
        # Validate JSON output (coming from run_action now)
        try:
            output_data = json.loads(result.stdout)
            assert isinstance(output_data, dict)
            # Assertions depend on the expected JSON structure from run_action
            assert "results" in output_data or "summary" in output_data  # Example check

        except json.JSONDecodeError:
            pytest.fail(f"Output was not valid JSON:\n{result.stdout}")
    else:
        # Validate standard text output (check stdout, should come from run_action logging/printing)
        assert "check-yaml" in result.stdout or "dummy.yaml" in result.stdout  # Example check
        # Assert that it's NOT JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(result.stdout)
