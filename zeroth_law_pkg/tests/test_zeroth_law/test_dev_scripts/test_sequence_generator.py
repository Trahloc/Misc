import pytest
import sys
from pathlib import Path
from typing import Set, List, Tuple, Dict, Any

# Add path to import the module under test
_test_file_path = Path(__file__).resolve()
_project_root = _test_file_path.parents[2]
_src_path = _project_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Module to be tested (will be created next)
from zeroth_law.dev_scripts.sequence_generator import generate_sequences_for_tool

# --- Test Data ---
SUBCOMMANDS_SIMPLE: Dict[str, Any] = {
    "check": {"description": "Check files"},
    "format": {"description": "Format files"},
}

SUBCOMMANDS_NESTED: Dict[str, Any] = {
    "config": {
        "description": "Configure settings",
        "subcommands_detail": {
            "show": {"description": "Show config"},
            "set": {"description": "Set config value"},
        },
    },
    "run": {"description": "Run process"},
}

SUBCOMMANDS_EMPTY: Dict[str, Any] = {}

BLACKLIST_SIMPLE: Set[str] = {"tool_a_format"}  # Blacklist one subcommand
BLACKLIST_NESTED: Set[str] = {"tool_b_config_set"}  # Blacklist a nested subcommand
BLACKLIST_BASE: Set[str] = {"tool_c"}  # Blacklist the base tool (should prevent all sequence gen)

# --- Test Cases ---


def test_generate_base_only():
    """Tool with no subcommands should generate only the base sequence."""
    tool_name = "tool_x"
    subcommands = SUBCOMMANDS_EMPTY
    blacklist = set()
    expected = [("tool_x",)]
    result = generate_sequences_for_tool(tool_name, subcommands, blacklist)
    assert result == expected


def test_generate_simple_subcommands():
    """Tool with simple subcommands."""
    tool_name = "tool_a"
    subcommands = SUBCOMMANDS_SIMPLE
    blacklist = set()
    expected = [("tool_a",), ("tool_a", "check"), ("tool_a", "format")]
    result = generate_sequences_for_tool(tool_name, subcommands, blacklist)
    assert sorted(result) == sorted(expected)  # Order might vary


def test_generate_nested_subcommands():
    """Tool with nested subcommands."""
    tool_name = "tool_b"
    subcommands = SUBCOMMANDS_NESTED
    blacklist = set()
    expected = [
        ("tool_b",),
        ("tool_b", "config"),
        ("tool_b", "config", "show"),
        ("tool_b", "config", "set"),
        ("tool_b", "run"),
    ]
    result = generate_sequences_for_tool(tool_name, subcommands, blacklist)
    assert sorted(result) == sorted(expected)


def test_generate_with_blacklist_simple():
    """Tool with simple subcommands and one blacklisted."""
    tool_name = "tool_a"
    subcommands = SUBCOMMANDS_SIMPLE
    blacklist = BLACKLIST_SIMPLE  # tool_a_format
    expected = [("tool_a",), ("tool_a", "check")]  # format is excluded
    result = generate_sequences_for_tool(tool_name, subcommands, blacklist)
    assert sorted(result) == sorted(expected)


def test_generate_with_blacklist_nested():
    """Tool with nested subcommands and one blacklisted."""
    tool_name = "tool_b"
    subcommands = SUBCOMMANDS_NESTED
    blacklist = BLACKLIST_NESTED  # tool_b_config_set
    expected = [
        ("tool_b",),
        ("tool_b", "config"),
        ("tool_b", "config", "show"),
        # ("tool_b", "config", "set"), # Excluded
        ("tool_b", "run"),
    ]
    result = generate_sequences_for_tool(tool_name, subcommands, blacklist)
    assert sorted(result) == sorted(expected)


def test_generate_with_blacklist_base():
    """Test when the base tool itself is blacklisted (should yield nothing)."""
    # Although reconcile should prevent calling this for a blacklisted tool,
    # the function itself should handle it gracefully.
    tool_name = "tool_c"
    subcommands = SUBCOMMANDS_SIMPLE
    blacklist = BLACKLIST_BASE  # tool_c
    expected: List[Tuple[str, ...]] = []
    result = generate_sequences_for_tool(tool_name, subcommands, blacklist)
    assert result == expected


def test_generate_empty_subcommands_dict():
    """Test with an empty subcommands dictionary passed in."""
    tool_name = "tool_y"
    subcommands = {}
    blacklist = set()
    expected = [("tool_y",)]
    result = generate_sequences_for_tool(tool_name, subcommands, blacklist)
    assert result == expected
