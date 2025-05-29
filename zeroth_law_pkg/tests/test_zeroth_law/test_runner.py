import pytest
from pathlib import Path
from typing import List, Dict, Any

# Assume the translation logic will be in this module
from zeroth_law.runner import build_tool_command_arguments

# --- Mock Tool Definitions (subset relevant for options) ---
MOCK_TOOL_DEFS = {
    "ruff_check": {
        "command_sequence": ["ruff", "check"],
        "options": {
            "--verbose": {
                "type": "flag",
                "description": "Enable verbose logging.",
                "maps_to_zlt_option": "verbose",  # Maps to canonical 'verbose'
            },
            "--quiet": {
                "type": "flag",
                "description": "Suppress non-error messages.",
                "maps_to_zlt_option": "quiet",  # Maps to canonical 'quiet'
            },
            "--config": {
                "type": "value",
                "value_name": "FILE",
                "description": "Path to configuration file.",
                "maps_to_zlt_option": "config",  # Maps to canonical 'config'
            },
            "--select": {
                "type": "value",
                "value_name": "RULE_CODE",
                "description": "Select specific rules.",
                "maps_to_zlt_option": None,  # Tool-specific, no mapping
            },
        },
        "arguments": {
            "files": {
                "type": "positional",
                "nargs": "*",
                "description": "Files or directories to lint.",
                "maps_to_zlt_option": "paths",  # Maps to canonical 'paths'
            }
        },
        "metadata": {
            "tool_name": "ruff",
            "command_name": "check",
            "provides_capabilities": ["Linter", "Analyzer"],
            "supported_filetypes": [".py", ".pyi"],
        },
    },
    "another_linter": {
        "command_sequence": ["another-lint"],
        "options": {
            "-V": {  # Different flag for verbose
                "type": "flag",
                "description": "Show verbose output.",
                "maps_to_zlt_option": "verbose",
            },
            "--conf": {  # Different flag for config
                "type": "value",
                "value_name": "PATH",
                "description": "Config file path.",
                "maps_to_zlt_option": "config",
            },
        },
        "arguments": {
            "input_path": {
                "type": "positional",
                "nargs": "*",
                "description": "Path to check.",
                "maps_to_zlt_option": "paths",
            }
        },
        "metadata": {
            "tool_name": "another-lint",
            "command_name": None,
            "provides_capabilities": ["Linter"],
            "supported_filetypes": [".py"],
        },
    },
}


# --- Test Cases ---


def test_translate_verbose_option_ruff():
    """Test translating ZLT's verbose option for ruff_check."""
    selected_tool_def = MOCK_TOOL_DEFS["ruff_check"]
    # Simulate ZLT context where --verbose was passed
    zlt_options_activated = {
        "verbose": True,
        "quiet": False,
        "config": None,
        "paths": [Path("file1.py")],
    }
    target_files_for_tool = [Path("file1.py")]

    # Expected result: base command + tool's verbose flag + positional paths
    expected_args = ["ruff", "check", "--verbose", "file1.py"]

    actual_args = build_tool_command_arguments(selected_tool_def, zlt_options_activated, target_files_for_tool)

    assert actual_args == expected_args


def test_translate_config_option_ruff():
    """Test translating ZLT's config option for ruff_check."""
    selected_tool_def = MOCK_TOOL_DEFS["ruff_check"]
    config_file = Path("my_ruff.toml")
    # Simulate ZLT context where --config was passed
    zlt_options_activated = {
        "verbose": False,
        "quiet": False,
        "config": config_file,
        "paths": [Path("file1.py")],
    }
    target_files_for_tool = [Path("file1.py")]

    # Expected result: base command + tool's config flag/value + positional paths
    expected_args = ["ruff", "check", "--config", str(config_file), "file1.py"]

    actual_args = build_tool_command_arguments(selected_tool_def, zlt_options_activated, target_files_for_tool)

    assert actual_args == expected_args


def test_translate_paths_option_ruff():
    """Test translating ZLT's paths option for ruff_check."""
    selected_tool_def = MOCK_TOOL_DEFS["ruff_check"]
    paths = [Path("src/"), Path("tests/")]
    # Simulate ZLT context where multiple paths were passed
    zlt_options_activated = {
        "verbose": False,
        "quiet": False,
        "config": None,
        "paths": paths,
    }
    target_files_for_tool = paths  # Assume all target files apply to this tool

    # Expected result: base command + positional paths
    # Adjust expectation: str(Path("dir/")) becomes "dir"
    expected_args = ["ruff", "check", "src", "tests"]

    actual_args = build_tool_command_arguments(selected_tool_def, zlt_options_activated, target_files_for_tool)

    # Convert Path objects to strings for comparison if needed by the function
    actual_args_str = [str(arg) if isinstance(arg, Path) else arg for arg in actual_args]

    assert actual_args_str == expected_args


def test_translate_multiple_options_ruff():
    """Test translating multiple ZLT options for ruff_check."""
    selected_tool_def = MOCK_TOOL_DEFS["ruff_check"]
    config_file = Path("../ruff.toml")
    paths = [Path(".")]
    # Simulate ZLT context with verbose, config, and paths
    zlt_options_activated = {
        "verbose": True,
        "quiet": False,
        "config": config_file,
        "paths": paths,
    }
    target_files_for_tool = paths

    # Order might matter depending on implementation, let's assume flags first, then values, then positionals
    expected_args = ["ruff", "check", "--verbose", "--config", str(config_file), "."]

    actual_args = build_tool_command_arguments(selected_tool_def, zlt_options_activated, target_files_for_tool)
    actual_args_str = [str(arg) if isinstance(arg, Path) else arg for arg in actual_args]
    assert actual_args_str == expected_args


def test_translate_options_different_tool():
    """Test translating options for a tool with different flags."""
    selected_tool_def = MOCK_TOOL_DEFS["another_linter"]
    config_file = Path("other_config.ini")
    paths = [Path("script.py")]
    # Simulate ZLT context with verbose, config, and paths
    zlt_options_activated = {
        "verbose": True,
        "quiet": False,
        "config": config_file,
        "paths": paths,
    }
    target_files_for_tool = paths

    # Expected args use the tool's specific flags (-V, --conf)
    expected_args = ["another-lint", "-V", "--conf", str(config_file), "script.py"]

    actual_args = build_tool_command_arguments(selected_tool_def, zlt_options_activated, target_files_for_tool)
    actual_args_str = [str(arg) if isinstance(arg, Path) else arg for arg in actual_args]
    assert actual_args_str == expected_args


def test_ignore_unmapped_zlt_options():
    """Test that ZLT options not mapped by the tool are ignored."""
    selected_tool_def = MOCK_TOOL_DEFS["ruff_check"]
    paths = [Path("file.py")]
    # Simulate ZLT context with recursive (which ruff_check doesn't map)
    zlt_options_activated = {
        "verbose": False,
        "quiet": False,
        "config": None,
        "recursive": True,
        "paths": paths,
    }
    target_files_for_tool = paths

    # Expected: base command + paths (recursive is ignored)
    expected_args = ["ruff", "check", "file.py"]

    actual_args = build_tool_command_arguments(selected_tool_def, zlt_options_activated, target_files_for_tool)
    actual_args_str = [str(arg) if isinstance(arg, Path) else arg for arg in actual_args]
    assert actual_args_str == expected_args


def test_translate_quiet_option_ruff():
    """Test translating ZLT's quiet option for ruff_check."""
    selected_tool_def = MOCK_TOOL_DEFS["ruff_check"]
    # Simulate ZLT context where --quiet was passed
    zlt_options_activated = {
        "verbose": False,
        "quiet": True,
        "config": None,
        "paths": [Path("file1.py")],
    }
    target_files_for_tool = [Path("file1.py")]

    # Expected result: base command + tool's quiet flag + positional paths
    expected_args = ["ruff", "check", "--quiet", "file1.py"]

    actual_args = build_tool_command_arguments(selected_tool_def, zlt_options_activated, target_files_for_tool)
    assert actual_args == expected_args


# TODO: Add tests for:
# - Default behaviors (e.g., if a tool always recurses unless told not to)
