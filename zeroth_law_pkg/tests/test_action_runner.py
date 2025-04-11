# File: tests/test_action_runner.py

import subprocess
from pathlib import Path
from typing import Any

import pytest

from zeroth_law.action_runner import YAML_MAPPING_FILE_NAME, load_tool_mapping, run_action

# Sample valid YAML content for testing
VALID_YAML_CONTENT = """
format:
  description: Formats code.
  tools:
    ruff_format:
      command: ruff format
test:
  description: Runs tests.
  tools:
    pytest:
      command: pytest
"""

# --- Tests for run_action ---

# Minimal mapping for run_action tests
RUN_ACTION_MAPPING = {
    "simple_action": {"description": "A simple action.", "tools": {"simple_tool": {"command": ["echo", "hello"], "option_mappings": {}}}},
    "action_with_args": {
        "description": "Action with args.",
        "tools": {
            "tool_with_args": {
                "command": ["ls"],
                "option_mappings": {
                    "verbose": {"type": "flag", "tool_arg": "-l"},
                    "all": {"type": "flag", "tool_arg": "-a"},
                    "output": {"type": "value", "tool_arg": "-o"},
                },
            }
        },
    },
    "action_with_paths": {
        "description": "Action with paths.",
        "tools": {"tool_with_paths": {"command": ["cat"], "option_mappings": {"paths": {"type": "positional"}}}},
    },
    "mypy_action": {
        "description": "Action running mypy.",
        "tools": {"mypy": {"command": ["mypy"], "option_mappings": {"paths": {"type": "positional", "default": ["src"]}}}},
    },
}


@pytest.fixture
def mock_subprocess_run(mocker):
    """Fixture to mock subprocess.run"""
    return mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="Success", stderr=""))


def test_run_action_simple_success(tmp_path: Path, mock_subprocess_run):
    """Test run_action with a simple command, successful execution."""
    action_name = "simple_action"
    project_root = tmp_path
    cli_args: dict[str, Any] = {}
    paths: list[Path] = []

    result = run_action(action_name, RUN_ACTION_MAPPING, project_root, cli_args, paths)

    assert result is True
    mock_subprocess_run.assert_called_once()
    call_args, call_kwargs = mock_subprocess_run.call_args
    # call_args is a tuple, the first element is the command list
    expected_command = ["poetry", "run", "echo", "hello"]
    assert call_args[0] == expected_command
    assert call_kwargs.get("cwd") == project_root
    assert call_kwargs.get("check") is False
    assert call_kwargs.get("env") is None  # No special env for this command


def test_run_action_with_args(tmp_path: Path, mock_subprocess_run):
    """Test run_action translates CLI args based on mapping."""
    action_name = "action_with_args"
    project_root = tmp_path
    # Simulate providing cli args: a flag, a value, and an unmapped arg
    cli_args: dict[str, Any] = {"verbose": True, "output": "out.txt", "unmapped": "ignore"}
    paths: list[Path] = []

    result = run_action(action_name, RUN_ACTION_MAPPING, project_root, cli_args, paths)

    assert result is True
    mock_subprocess_run.assert_called_once()
    call_args, call_kwargs = mock_subprocess_run.call_args
    # Expected: poetry run ls -l -o out.txt (order of -l and -o might vary, check presence)
    expected_base = ["poetry", "run", "ls"]
    assert call_args[0][:3] == expected_base
    assert "-l" in call_args[0]
    assert "-o" in call_args[0]
    assert "out.txt" in call_args[0]
    assert call_args[0].index("-o") + 1 == call_args[0].index("out.txt")  # Value follows flag
    assert "-a" not in call_args[0]  # 'all' was not in cli_args
    assert "ignore" not in call_args[0]  # Unmapped arg ignored
    assert call_kwargs.get("cwd") == project_root


def test_run_action_with_paths(tmp_path: Path, mock_subprocess_run):
    """Test run_action passes positional paths."""
    action_name = "action_with_paths"
    project_root = tmp_path
    cli_args: dict[str, Any] = {}
    path1 = tmp_path / "file1.txt"
    path2 = tmp_path / "dir1"
    paths: list[Path] = [path1, path2]

    result = run_action(action_name, RUN_ACTION_MAPPING, project_root, cli_args, paths)

    assert result is True
    mock_subprocess_run.assert_called_once()
    call_args, _ = mock_subprocess_run.call_args
    expected_command = ["poetry", "run", "cat", str(path1), str(path2)]
    assert call_args[0] == expected_command


def test_run_action_failure(tmp_path: Path, mocker):
    """Test run_action returns False when a tool fails."""
    action_name = "simple_action"
    project_root = tmp_path
    cli_args: dict[str, Any] = {}
    paths: list[Path] = []

    # Mock subprocess.run to return non-zero exit code
    mock_fail_run = mocker.patch(
        "subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Error")
    )

    result = run_action(action_name, RUN_ACTION_MAPPING, project_root, cli_args, paths)

    assert result is False
    mock_fail_run.assert_called_once()


def test_run_action_mypy_env(tmp_path: Path, mock_subprocess_run, mocker):
    """Test run_action sets MYPYPATH correctly for mypy."""
    action_name = "mypy_action"
    project_root = tmp_path
    cli_args: dict[str, Any] = {}
    paths: list[Path] = []  # Use default path from mapping
    src_dir = tmp_path / "src"
    src_dir.mkdir()  # Create src dir for MYPYPATH logic

    # Mock os.environ.copy to check MYPYPATH later
    original_environ = {"OTHER_VAR": "value"}
    mock_environ = mocker.patch("os.environ", original_environ)

    result = run_action(action_name, RUN_ACTION_MAPPING, project_root, cli_args, paths)

    assert result is True
    mock_subprocess_run.assert_called_once()
    call_args, call_kwargs = mock_subprocess_run.call_args

    # Check command includes default path
    expected_command = ["poetry", "run", "mypy", "src"]
    assert call_args[0] == expected_command

    # Check environment passed to subprocess.run
    passed_env = call_kwargs.get("env")
    assert passed_env is not None
    expected_src_path = str(src_dir.resolve())
    assert passed_env.get("MYPYPATH") == expected_src_path
    assert passed_env.get("OTHER_VAR") == "value"  # Check original env is preserved


def test_load_tool_mapping_success(tmp_path: Path):
    """Test loading a valid tool_mapping.yaml file."""
    # Arrange: Create a dummy project structure and YAML file
    src_dir = tmp_path / "src" / "zeroth_law"
    src_dir.mkdir(parents=True)
    yaml_file = src_dir / YAML_MAPPING_FILE_NAME
    yaml_file.write_text(VALID_YAML_CONTENT, encoding="utf-8")

    # Act: Call the function under test
    mapping = load_tool_mapping(project_root=tmp_path)

    # Assert: Check if the mapping was loaded correctly
    assert mapping is not None
    assert "format" in mapping
    assert "test" in mapping
    assert mapping["format"]["description"] == "Formats code."
    assert "ruff_format" in mapping["format"]["tools"]
    assert mapping["format"]["tools"]["ruff_format"]["command"] == "ruff format"
    assert mapping["test"]["tools"]["pytest"]["command"] == "pytest"


def test_load_tool_mapping_not_found(tmp_path: Path):
    """Test loading when the mapping file is not found."""
    # Arrange: Create the directory structure but not the file
    src_dir = tmp_path / "src" / "zeroth_law"
    src_dir.mkdir(parents=True)

    # Act: Call the function under test
    mapping = load_tool_mapping(project_root=tmp_path)

    # Assert: Check that None is returned
    assert mapping is None


def test_load_tool_mapping_invalid_yaml(tmp_path: Path):
    """Test loading when the mapping file contains invalid YAML."""
    # Arrange: Create the directory structure and an invalid YAML file
    src_dir = tmp_path / "src" / "zeroth_law"
    src_dir.mkdir(parents=True)
    yaml_file = src_dir / YAML_MAPPING_FILE_NAME
    # Use single quotes for the outer string to avoid issues with inner double quotes
    invalid_yaml_content = 'format: { description: "missing closing quote }\n  extra: ['  # An invalid YAML structure
    yaml_file.write_text(invalid_yaml_content, encoding="utf-8")

    # Act: Call the function under test
    mapping = load_tool_mapping(project_root=tmp_path)

    # Assert: Check that None is returned
    assert mapping is None


# Add more tests here for failure cases (file not found, invalid YAML)
