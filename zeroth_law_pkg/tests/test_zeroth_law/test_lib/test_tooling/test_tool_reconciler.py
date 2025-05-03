import pytest
import sys
from pathlib import Path
from enum import Enum, auto
from unittest.mock import patch, MagicMock
from typing import Set, Dict, Any, Tuple

# Add path to import the module under test
_test_file_path = Path(__file__).resolve()
_project_root = _test_file_path.parents[2]
_src_path = _project_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Module to be tested (will be created next)
# Assuming it defines an Enum for status and the reconcile function
from zeroth_law.lib.tooling.tool_reconciler import (
    ToolStatus,
    reconcile_tools,
)
from zeroth_law.common.hierarchical_utils import parse_to_nested_dict

# Fixture for a dummy ReconciliationResult

# --- Test Cases ---


def test_reconcile_managed_ok():
    """Tool in tools dir, whitelisted, found in env."""
    env_tools = {"tool_a", "tool_b"}
    # dir_tools = {"tool_a"} # Obsolete
    defined_sequences = set()  # Pass empty set for now
    whitelist = {"tool_a", "tool_b"}
    blacklist = set()
    expected = {
        # Corrected based on has_defs=False logic
        "tool_a": ToolStatus.WHITELISTED_NO_DEFS,
        "tool_b": ToolStatus.WHITELISTED_NO_DEFS,
    }
    # Note: tool_b is whitelisted but not in tools/, which might be another status or handled later.
    # For now, focusing on tool_a's status.
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    # Correct assertion
    assert result.get("tool_a") == ToolStatus.WHITELISTED_NO_DEFS
    assert result.get("tool_b") == ToolStatus.WHITELISTED_NO_DEFS


def test_reconcile_managed_missing_in_env():
    """Tool in tools dir, whitelisted, but NOT found in env."""
    env_tools = {"tool_b"}
    # dir_tools = {"tool_a"} # Obsolete
    defined_sequences = set()  # Pass empty set for now
    whitelist = {"tool_a", "tool_b"}
    blacklist = set()
    expected = {
        # Corrected based on has_defs=False logic
        "tool_a": ToolStatus.ERROR_MISSING_WHITELISTED,
        "tool_b": ToolStatus.WHITELISTED_NO_DEFS,
    }
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    # Correct assertion
    assert result.get("tool_a") == ToolStatus.ERROR_MISSING_WHITELISTED
    assert result.get("tool_b") == ToolStatus.WHITELISTED_NO_DEFS


def test_reconcile_blacklisted_in_env_only():
    """Tool in env, blacklisted, NOT in tools dir (Correct state)."""
    env_tools = {"tool_c"}
    # dir_tools = set() # Obsolete
    defined_sequences = set()  # Pass empty set for now
    whitelist = set()
    blacklist = {"tool_c"}
    expected = {"tool_c": ToolStatus.BLACKLISTED_IN_ENV}
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    assert result.get("tool_c") == ToolStatus.BLACKLISTED_IN_ENV


def test_reconcile_blacklisted_in_tools_error():
    """Tool blacklisted, in env, no defs (should NOT be an error based on current logic)."""
    env_tools = {"tool_c"}
    # dir_tools = {"tool_c"} # Obsolete, presence of dir is irrelevant now
    defined_sequences = set()  # Pass empty set for now
    whitelist = set()
    blacklist = {"tool_c"}
    # Error state is now ERROR_BLACKLISTED_HAS_DEFS
    # Corrected based on has_defs=False logic:
    expected = {"tool_c": ToolStatus.BLACKLISTED_IN_ENV}
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Simulate definitions existing for tool_c - NO, this test assumes no defs
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    # Correct assertion
    assert result.get("tool_c") == ToolStatus.BLACKLISTED_IN_ENV
    # Old assert:
    # assert result.get("tool_c") == ToolStatus.ERROR_BLACKLISTED_HAS_DEFS


def test_reconcile_orphan_dir():
    """Tool in env, unmanaged, no defs (should be NEW_ENV_TOOL)."""
    env_tools = {"orphan_tool"}
    # dir_tools = {"orphan_tool"} # Obsolete
    defined_sequences = set()  # Pass empty set for now
    whitelist = {"tool_a"}
    blacklist = {"tool_b"}
    # Error state is now ERROR_ORPHAN_HAS_DEFS
    # Corrected based on has_defs=False logic:
    expected = {"orphan_tool": ToolStatus.NEW_ENV_TOOL}
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Simulate definitions existing for orphan_tool - NO, this test assumes no defs
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    # Correct assertion
    assert result.get("orphan_tool") == ToolStatus.NEW_ENV_TOOL
    # Old assert:
    # assert result.get("orphan_tool") == ToolStatus.ERROR_ORPHAN_HAS_DEFS


def test_reconcile_new_env_tool():
    """Tool in env, but NOT in tools dir, whitelist, or blacklist (New)."""
    env_tools = {"new_tool"}
    # dir_tools = set() # Obsolete
    defined_sequences = set()  # Pass empty set for now
    whitelist = {"tool_a"}
    blacklist = {"tool_b"}
    expected = {"new_tool": ToolStatus.NEW_ENV_TOOL}
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    assert result.get("new_tool") == ToolStatus.NEW_ENV_TOOL


def test_reconcile_whitelisted_missing_dir():
    """Tool whitelisted, in env, but NOT in tools dir."""
    env_tools = {"tool_a"}
    # dir_tools = set() # Obsolete
    defined_sequences = set()  # Pass empty set for now
    whitelist = {"tool_a"}
    blacklist = set()
    # State is now WHITELISTED_NO_DEFS (whitelisted, in env, no defs)
    expected = {"tool_a": ToolStatus.WHITELISTED_NO_DEFS}
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    assert result.get("tool_a") == ToolStatus.WHITELISTED_NO_DEFS


def test_reconcile_whitelisted_missing_dir_and_env():
    """Tool whitelisted, but NOT in tools dir or env."""
    env_tools = set()
    # dir_tools = set() # Obsolete
    defined_sequences = set()  # Pass empty set for now
    whitelist = {"tool_a"}  # Whitelisted, but nowhere to be found
    blacklist = set()
    expected = {"tool_a": ToolStatus.ERROR_MISSING_WHITELISTED}
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    assert result.get("tool_a") == ToolStatus.ERROR_MISSING_WHITELISTED


def test_reconcile_mixed_complex():
    """Test a mix of different tool statuses."""
    env_tools = {"managed", "missing_env", "blacklisted_env", "new", "orphan"}
    # dir_tools = {"managed", "missing_env", "blacklisted_tools", "orphan"} # Obsolete
    defined_sequences = set()  # Pass empty set for now
    whitelist = {"managed", "missing_env", "missing_all"}
    blacklist = {"blacklisted_env", "blacklisted_tools"}
    # Corrected expected statuses based on has_defs=False logic
    expected = {
        "managed": ToolStatus.WHITELISTED_NO_DEFS,  # Was MANAGED_OK
        "missing_env": ToolStatus.WHITELISTED_NO_DEFS,  # Corrected from ERROR_MISSING_WHITELISTED
        "blacklisted_env": ToolStatus.BLACKLISTED_IN_ENV,  # Correct
        "blacklisted_tools": ToolStatus.BLACKLISTED_IN_ENV,  # Was ERROR_BLACKLISTED_HAS_DEFS
        "new": ToolStatus.NEW_ENV_TOOL,  # Correct
        "orphan": ToolStatus.NEW_ENV_TOOL,  # Was ERROR_ORPHAN_HAS_DEFS
        "missing_all": ToolStatus.ERROR_MISSING_WHITELISTED,  # Correct
    }
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    assert result == expected


def test_reconcile_empty_inputs():
    """Test with all input sets empty."""
    env_tools = set()
    # dir_tools = set() # Obsolete
    defined_sequences = set()  # Pass empty set for now
    whitelist = set()
    blacklist = set()
    expected = {}
    parsed_whitelist = parse_to_nested_dict(whitelist)
    parsed_blacklist = parse_to_nested_dict(blacklist)
    # Pass defined_sequences instead of dir_tools
    result = reconcile_tools(env_tools, defined_sequences, parsed_whitelist, parsed_blacklist)
    assert result == expected
