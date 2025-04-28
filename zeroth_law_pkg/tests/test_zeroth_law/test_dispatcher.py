import pytest
from pathlib import Path
from typing import List, Dict, Any, Set

# Assume the dispatcher logic will be in this module
from zeroth_law.dispatcher import find_tool_for_capability_and_files

# --- Mock Tool Definitions ---
MOCK_TOOL_DEFS = {
    "ruff_format": {
        "command_sequence": ["ruff", "format"],
        "options": {},
        "arguments": {},
        "metadata": {
            "tool_name": "ruff",
            "command_name": "format",
            "provides_capabilities": ["Formatter"],
            "supported_filetypes": [".py", ".pyi"],
            # Other metadata...
        },
    },
    "ruff_check": {
        "command_sequence": ["ruff", "check"],
        "options": {},
        "arguments": {},
        "metadata": {
            "tool_name": "ruff",
            "command_name": "check",
            "provides_capabilities": ["Linter", "Analyzer"],
            "supported_filetypes": [".py", ".pyi"],
            # Other metadata...
        },
    },
    "stylua": {
        "command_sequence": ["stylua"],
        "options": {},
        "arguments": {},
        "metadata": {
            "tool_name": "stylua",
            "command_name": None,
            "provides_capabilities": ["Formatter"],
            "supported_filetypes": [".lua"],
            # Other metadata...
        },
    },
    "shellcheck": {
        "command_sequence": ["shellcheck"],
        "options": {},
        "arguments": {},
        "metadata": {
            "tool_name": "shellcheck",
            "command_name": None,
            "provides_capabilities": ["Linter"],
            "supported_filetypes": [".sh", ".bash"],
            # Other metadata...
        },
    },
    "generic_cleaner": {
        "command_sequence": ["generic-cleaner"],
        "options": {},
        "arguments": {},
        "metadata": {
            "tool_name": "generic-cleaner",
            "command_name": None,
            "provides_capabilities": ["Formatter"],  # Example: Generic formatter
            "supported_filetypes": ["*"],  # Supports any file type
            # Other metadata...
        },
    },
}


# --- Test Cases ---


def test_find_formatter_for_python():
    """Test finding a Formatter for a Python file."""
    capability_needed = "Formatter"
    target_files = [Path("src/module/file.py")]
    available_definitions = MOCK_TOOL_DEFS

    # For now, assume the function returns a dictionary mapping file path to the selected tool definition ID
    # Or maybe it returns the definition dict itself? Let's assume ID for now.
    selected_tools = find_tool_for_capability_and_files(capability_needed, target_files, available_definitions)

    assert len(selected_tools) == 1
    assert target_files[0] in selected_tools
    assert (
        selected_tools[target_files[0]] == "ruff_format"
    ), f"Expected 'ruff_format', but got {selected_tools.get(target_files[0])}"


def test_find_linter_for_python():
    """Test finding a Linter for a Python file."""
    capability_needed = "Linter"
    target_files = [Path("src/module/file.py")]
    available_definitions = MOCK_TOOL_DEFS
    selected_tools = find_tool_for_capability_and_files(capability_needed, target_files, available_definitions)
    assert len(selected_tools) == 1
    assert selected_tools.get(target_files[0]) == "ruff_check"


def test_find_formatter_for_lua():
    """Test finding a Formatter for a Lua file."""
    capability_needed = "Formatter"
    target_files = [Path("scripts/script.lua")]
    available_definitions = MOCK_TOOL_DEFS
    selected_tools = find_tool_for_capability_and_files(capability_needed, target_files, available_definitions)
    assert len(selected_tools) == 1
    assert selected_tools.get(target_files[0]) == "stylua"


def test_find_linter_for_shell():
    """Test finding a Linter for a shell script."""
    capability_needed = "Linter"
    target_files = [Path("deploy.sh")]
    available_definitions = MOCK_TOOL_DEFS
    selected_tools = find_tool_for_capability_and_files(capability_needed, target_files, available_definitions)
    assert len(selected_tools) == 1
    assert selected_tools.get(target_files[0]) == "shellcheck"


def test_find_tools_for_multiple_types():
    """Test finding tools for multiple file types in one call."""
    capability_needed = "Formatter"
    target_files = [Path("src/main.py"), Path("utils.lua")]
    available_definitions = MOCK_TOOL_DEFS
    selected_tools = find_tool_for_capability_and_files(capability_needed, target_files, available_definitions)
    assert len(selected_tools) == 2
    assert selected_tools.get(target_files[0]) == "ruff_format"  # Python file
    assert selected_tools.get(target_files[1]) == "stylua"  # Lua file


def test_find_no_tool_for_unknown_type():
    """Test handling a file type with no matching tool for the capability."""
    capability_needed = "Linter"  # Linter for .txt is not defined
    target_files = [Path("notes.txt")]
    available_definitions = MOCK_TOOL_DEFS
    selected_tools = find_tool_for_capability_and_files(capability_needed, target_files, available_definitions)
    assert len(selected_tools) == 1
    assert selected_tools.get(target_files[0]) is None


def test_find_agnostic_tool():
    """Test that a tool supporting '*' matches any file type if capability matches."""
    capability_needed = "Formatter"
    target_files = [Path("README.md")]  # No specific formatter defined for .md
    available_definitions = MOCK_TOOL_DEFS
    selected_tools = find_tool_for_capability_and_files(capability_needed, target_files, available_definitions)
    assert len(selected_tools) == 1
    assert selected_tools.get(target_files[0]) == "generic_cleaner"


def test_find_specific_tool_over_agnostic():
    """Test that a specific tool is preferred over an agnostic one for the same capability."""
    capability_needed = "Formatter"
    target_files = [Path("src/main.py")]  # .py has ruff_format and generic_cleaner
    available_definitions = MOCK_TOOL_DEFS
    selected_tools = find_tool_for_capability_and_files(capability_needed, target_files, available_definitions)
    assert len(selected_tools) == 1
    # Expect ruff_format because it specifically lists .py and is found first in MOCK_TOOL_DEFS iteration
    # NOTE: This relies on dict iteration order which is guaranteed in Python 3.7+
    # A more robust implementation might need explicit priorities.
    assert selected_tools.get(target_files[0]) == "ruff_format"


# Add more tests later:
# - Testing prime tool selection if multiple tools match (e.g., if black was also added)
