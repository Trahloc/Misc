# File: tests/test_cli_json_output.py
"""Tests for the JSON output functionality in the CLI."""

import importlib
import json
import logging
import os  # Import os for chdir
import sys
from pathlib import Path

import pytest
import toml
from click.testing import CliRunner
import src.zeroth_law.cli as cli_module

# Assuming project root is detectable or tests run from root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Add src to path to allow importing the cli module
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent / "src"))

# Import the module containing the CLI definitions


# Helper function to create temporary project environment
def setup_temp_project(tmp_path: Path, action_config: str):
    project_dir = tmp_path / "json_test_pkg"
    project_dir.mkdir()
    # Create pyproject.toml
    # Use triple quotes for the main f-string to handle internal quotes easily
    pyproject_content = f"""
[tool.poetry]
name = "json-test-project"
version = "0.1.0"
description = ""
authors = ["Test User <test@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.zeroth-law]
# Minimal base config needed
max_lines = 100

# Define the action passed to the helper
{action_config}
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)
    return project_dir


@pytest.mark.parametrize(
    "option_name,expected_in_output",
    [
        ("--json", True),
        ("", False),
    ],
    ids=["with_json_flag", "without_json_flag"],
)
def test_cli_json_output_flag(option_name, expected_in_output, tmp_path):
    """Test that the CLI handles the --json flag correctly."""
    # Arrange
    # Use a simpler command to isolate subprocess execution issues
    test_tool_output = "TEST_OUTPUT_MARKER"
    simple_command = ["python", "-c", f"print('{test_tool_output}', end='')"]

    # Define the action configuration as a Python dictionary
    lint_action_data = {
        "description": "Run simple python print for json test.",
        "zlt_options": {"paths": {"type": "positional"}, "json": {"type": "flag"}},
        "tools": {"simple_print": {"command": simple_command, "maps_options": {}}},
    }

    # Create the full dictionary structure for pyproject.toml
    full_config_dict = {
        "tool": {
            "zeroth-law": {
                "project_root_marker": ".git",
                "max_lines": 100,  # Example base config
                "actions": {"lint": lint_action_data},
            }
        }
    }

    # Dump the dictionary to a valid TOML string
    lint_action_config_str = toml.dumps(full_config_dict)

    # Setup project directory directly to avoid setup_temp_project interpolation issues
    project_dir = tmp_path / "json_test_pkg"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text(lint_action_config_str)

    # Create a dummy target file for the lint command to operate on
    test_py = project_dir / "some_file.py"
    test_py.touch()

    original_cwd = Path.cwd()
    os.chdir(project_dir)

    try:
        # Reload module to load commands from temp pyproject.toml
        importlib.reload(cli_module)

        runner = CliRunner(mix_stderr=False)  # Capture stdout/stderr separately

        # Act
        command = ["lint", str(test_py)]
        if option_name:
            command.insert(1, option_name)

        result = runner.invoke(cli_module.cli_group, command, catch_exceptions=False)

    finally:
        os.chdir(original_cwd)

    # Assert
    assert result.exit_code == 0, f"Command failed when --json specified. " f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"

    # Verify JSON output presence/absence and content
    print(f"--- Test Case: {option_name} ---")
    print(f"stderr:\n{result.stderr}")  # Print stderr for debugging
    print(f"stdout:\n{result.stdout}")  # Print stdout for debugging
    print("---------------------------")

    if expected_in_output:  # --json flag used
        # Action runner should print the tool's raw stdout when --json is used.
        # Check that stdout contains the expected output from the simple command.
        assert result.stdout.strip(), f"Expected stdout to not be empty when --json specified. stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
        assert test_tool_output in result.stdout, f"Expected tool output ('{test_tool_output}') not found in stdout when --json specified. stderr:\n{result.stderr}\nstdout:\n{result.stdout}"

        # No JSON parsing needed for this simplified test

    else:  # No --json flag used
        # Action runner should log the tool's output via log.info, *not* print to stdout.
        # Check that stdout *only* contains initial debug logs (if any), not the tool output.
        assert test_tool_output not in result.stdout, f"Tool output ('{test_tool_output}') unexpectedly found in stdout without --json flag. stdout:\n{result.stdout}"

        # Check that stdout is NOT parseable as JSON
        is_json = False
        try:
            json.loads(result.stdout.strip())
            is_json = True
        except json.JSONDecodeError:
            pass  # Expected
        assert not is_json, f"stdout unexpectedly contained valid JSON without --json flag. stdout:\n{result.stdout}"
