# File: tests/test_action_runner.py

import os  # Added for os.pathsep
import subprocess
from pathlib import Path
from typing import Any

import pytest

# from zeroth_law.action_runner import YAML_MAPPING_FILE_NAME, load_tool_mapping, run_action # Old import
from zeroth_law.action_runner import run_action  # Corrected import

# Define action configurations directly for testing
TEST_ACTION_CONFIGS = {
    "simple_action": {
        "description": "A simple echo action.",
        "zlt_options": {"paths": {"type": "positional", "default": []}},
        "tools": {
            "simple_echo": {
                "command": ["echo", "hello"],
                "maps_options": {"paths": None},  # Positional paths
            }
        },
    },
    "action_with_args": {
        "description": "Action with args.",
        "zlt_options": {
            "verbose": {"type": "flag", "description": "Verbose flag"},
            "output": {"type": "value", "value_type": "str", "description": "Output file"},
            "paths": {"type": "positional", "default": []},
        },
        "tools": {
            "tool_with_args": {
                # Use a command less likely to vary output (like echo) than ls
                "command": ["echo", "tool_command"],
                "maps_options": {
                    "verbose": "--verbose-arg",
                    "output": "--output-arg",
                    "paths": None,
                },
            }
        },
    },
    "action_with_paths": {
        "description": "Action passing paths.",
        "zlt_options": {"paths": {"type": "positional", "default": []}},
        "tools": {
            "tool_needing_paths": {
                "command": ["echo", "paths:"],  # Simple command
                "maps_options": {"paths": None},  # Positional paths
            }
        },
    },
    "mypy_action": {
        "description": "Action simulating mypy env setup.",
        "zlt_options": {"paths": {"type": "positional", "default": ["src"]}},
        "tools": {
            # Rename tool back to 'mypy' so _prepare_environment recognizes it
            "mypy": {
                "command": ["echo", "mypy_command"],
                "maps_options": {"paths": None},
            }
        },
    },
}


@pytest.fixture
def mock_subprocess_run(mocker):
    """Fixture to mock subprocess.run"""
    return mocker.patch(
        "subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="Success", stderr="")
    )


def test_run_action_simple_success(tmp_path: Path, mocker):
    """Test run_action with a simple command, successful execution."""
    action_name = "simple_action"
    action_config = TEST_ACTION_CONFIGS[action_name]
    project_root = tmp_path
    cli_args: dict[str, Any] = {}
    paths: list[Path] = []  # No paths provided

    # Mock subprocess.run for this test
    mock_run = mocker.patch(
        "subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b"")
    )

    result = run_action(action_name, action_config, project_root, cli_args, paths)

    assert result is True
    mock_run.assert_called_once()
    call_args, call_kwargs = mock_run.call_args

    # Path should be added by _build_path_arguments as no paths/defaults provided
    try:
        relative_root = str(project_root.relative_to(Path.cwd()))
    except ValueError:
        relative_root = str(project_root)
    expected_command = ["echo", "hello", relative_root]
    assert call_args[0] == expected_command
    assert call_kwargs.get("cwd") == project_root
    assert call_kwargs.get("check") is False  # ActionRunner doesn't use check=True


def test_run_action_with_args(tmp_path: Path, mocker):
    """Test run_action translates CLI args based on maps_options."""
    action_name = "action_with_args"
    action_config = TEST_ACTION_CONFIGS[action_name]
    project_root = tmp_path
    cli_args: dict[str, Any] = {"verbose": True, "output": "out.txt", "unmapped": "ignore"}
    paths: list[Path] = []  # No paths

    mock_run = mocker.patch(
        "subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b"")
    )

    result = run_action(action_name, action_config, project_root, cli_args, paths)

    assert result is True
    mock_run.assert_called_once()
    call_args, call_kwargs = mock_run.call_args
    command_list = call_args[0]

    # Expected: echo tool_command --verbose-arg --output-arg out.txt <project_root_path>
    expected_base = ["echo", "tool_command"]
    assert command_list[:2] == expected_base
    assert "--verbose-arg" in command_list  # Mapped from verbose: True
    assert "--output-arg" in command_list  # Mapped from output: out.txt
    assert "out.txt" in command_list
    assert command_list.index("--output-arg") + 1 == command_list.index("out.txt")
    assert "unmapped" not in command_list  # Unmapped arg ignored
    assert "ignore" not in command_list

    try:
        relative_root = str(project_root.relative_to(Path.cwd()))
    except ValueError:
        relative_root = str(project_root)
    assert command_list[-1] == relative_root  # Path fallback
    assert call_kwargs.get("cwd") == project_root


def test_run_action_with_paths(tmp_path: Path, mocker):
    """Test run_action passes positional paths correctly."""
    action_name = "action_with_paths"
    action_config = TEST_ACTION_CONFIGS[action_name]
    project_root = tmp_path
    cli_args: dict[str, Any] = {}
    path1 = tmp_path / "file1.txt"
    path2 = tmp_path / "dir1"
    path1.touch()
    path2.mkdir()
    paths: list[Path] = [path1, path2]

    mock_run = mocker.patch(
        "subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b"")
    )

    result = run_action(action_name, action_config, project_root, cli_args, paths)

    assert result is True
    mock_run.assert_called_once()
    call_args, _ = mock_run.call_args
    # Expected: echo paths: file1.txt dir1
    expected_command = ["echo", "paths:", str(path1), str(path2)]
    assert call_args[0] == expected_command


def test_run_action_failure(tmp_path: Path, mocker):
    """Test run_action returns False when the tool subprocess fails."""
    action_name = "simple_action"
    action_config = TEST_ACTION_CONFIGS[action_name]
    project_root = tmp_path
    cli_args: dict[str, Any] = {}
    paths: list[Path] = []

    # Mock subprocess.run to simulate failure
    mock_fail_run = mocker.patch(
        "subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=1, stderr="Tool Error")
    )

    result = run_action(action_name, action_config, project_root, cli_args, paths)

    assert result is False
    mock_fail_run.assert_called_once()


def test_run_action_mypy_env(tmp_path: Path, mocker):
    """Test run_action sets MYPYPATH correctly for tools named 'mypy' or similar."""
    action_name = "mypy_action"
    action_config = TEST_ACTION_CONFIGS[action_name]
    project_root = tmp_path
    cli_args: dict[str, Any] = {}
    paths: list[Path] = []  # Let default paths be used
    src_dir = tmp_path / "src"
    src_dir.mkdir()  # Create src dir for MYPYPATH logic

    mock_run = mocker.patch(
        "subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b"")
    )

    # Mock os.environ interaction
    original_environ = {"OTHER_VAR": "value", "MYPYPATH": "/existing/path"}
    mocker.patch.dict(os.environ, original_environ, clear=True)

    result = run_action(action_name, action_config, project_root, cli_args, paths)

    assert result is True
    mock_run.assert_called_once()
    call_args, call_kwargs = mock_run.call_args

    # Check command includes default path "src" from action_config
    expected_command = ["echo", "mypy_command", "src"]
    assert call_args[0] == expected_command

    # Check environment passed to subprocess.run
    passed_env = call_kwargs.get("env")
    assert passed_env is not None
    expected_src_path = str(src_dir.resolve())
    expected_mypypath = f"{expected_src_path}{os.pathsep}{original_environ['MYPYPATH']}"
    assert passed_env.get("MYPYPATH") == expected_mypypath
    assert passed_env.get("OTHER_VAR") == "value"


# <<< ZEROTH LAW FOOTER >>>
