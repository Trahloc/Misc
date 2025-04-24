import pytest
import sys
from pathlib import Path
from enum import Enum, auto

# Add path to import the module under test
_test_file_path = Path(__file__).resolve()
_project_root = _test_file_path.parents[2]
_src_path = _project_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Module to be tested (will be created next)
# Assuming it defines an Enum for status and the reconcile function
from zeroth_law.dev_scripts.tool_reconciler import reconcile_tools, ToolStatus

# --- Test Cases ---


def test_reconcile_managed_ok():
    """Tool in tools dir, whitelisted, found in env."""
    env_tools = {"tool_a", "tool_b"}
    dir_tools = {"tool_a"}
    whitelist = {"tool_a", "tool_b"}
    blacklist = set()
    expected = {"tool_a": ToolStatus.MANAGED_OK, "tool_b": ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR}
    # Note: tool_b is whitelisted but not in tools/, which might be another status or handled later.
    # For now, focusing on tool_a's status.
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result.get("tool_a") == ToolStatus.MANAGED_OK
    # We might refine expected status for tool_b later


def test_reconcile_managed_missing_in_env():
    """Tool in tools dir, whitelisted, but NOT found in env."""
    env_tools = {"tool_b"}
    dir_tools = {"tool_a"}
    whitelist = {"tool_a", "tool_b"}
    blacklist = set()
    expected = {"tool_a": ToolStatus.MANAGED_MISSING_ENV, "tool_b": ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR}
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result.get("tool_a") == ToolStatus.MANAGED_MISSING_ENV


def test_reconcile_blacklisted_in_env_only():
    """Tool in env, blacklisted, NOT in tools dir (Correct state)."""
    env_tools = {"tool_c"}
    dir_tools = set()
    whitelist = set()
    blacklist = {"tool_c"}
    expected = {"tool_c": ToolStatus.BLACKLISTED_IN_ENV}
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result.get("tool_c") == ToolStatus.BLACKLISTED_IN_ENV


def test_reconcile_blacklisted_in_tools_error():
    """Tool in tools dir AND blacklisted (ERROR state)."""
    env_tools = {"tool_c"}
    dir_tools = {"tool_c"}  # Error: Blacklisted tool has a directory
    whitelist = set()
    blacklist = {"tool_c"}
    expected = {"tool_c": ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR}
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result.get("tool_c") == ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR


def test_reconcile_orphan_dir():
    """Tool in tools dir, but NOT whitelisted or blacklisted (Orphan)."""
    env_tools = {"orphan_tool"}
    dir_tools = {"orphan_tool"}  # Has a directory
    whitelist = {"tool_a"}
    blacklist = {"tool_b"}
    expected = {"orphan_tool": ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR}
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result.get("orphan_tool") == ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR


def test_reconcile_new_env_tool():
    """Tool in env, but NOT in tools dir, whitelist, or blacklist (New)."""
    env_tools = {"new_tool"}
    dir_tools = set()
    whitelist = {"tool_a"}
    blacklist = {"tool_b"}
    expected = {"new_tool": ToolStatus.NEW_ENV_TOOL}
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result.get("new_tool") == ToolStatus.NEW_ENV_TOOL


def test_reconcile_whitelisted_missing_dir():
    """Tool whitelisted, in env, but NOT in tools dir."""
    env_tools = {"tool_a"}
    dir_tools = set()  # Missing directory
    whitelist = {"tool_a"}
    blacklist = set()
    expected = {"tool_a": ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR}
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result.get("tool_a") == ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR


def test_reconcile_whitelisted_missing_dir_and_env():
    """Tool whitelisted, but NOT in tools dir or env."""
    env_tools = set()
    dir_tools = set()
    whitelist = {"tool_a"}  # Whitelisted, but nowhere to be found
    blacklist = set()
    expected = {"tool_a": ToolStatus.ERROR_MISSING_WHITELISTED}
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result.get("tool_a") == ToolStatus.ERROR_MISSING_WHITELISTED


def test_reconcile_mixed_complex():
    """Test a mix of different tool statuses."""
    env_tools = {"managed", "missing_env", "blacklisted_env", "new", "orphan"}
    dir_tools = {"managed", "missing_env", "blacklisted_tools", "orphan"}
    whitelist = {"managed", "missing_env", "missing_all"}
    blacklist = {"blacklisted_env", "blacklisted_tools"}
    expected = {
        "managed": ToolStatus.MANAGED_OK,
        "missing_env": ToolStatus.MANAGED_OK,
        "blacklisted_env": ToolStatus.BLACKLISTED_IN_ENV,
        "blacklisted_tools": ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR,
        "new": ToolStatus.NEW_ENV_TOOL,
        "orphan": ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR,
        "missing_all": ToolStatus.ERROR_MISSING_WHITELISTED,
    }
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result == expected


def test_reconcile_empty_inputs():
    """Test with all input sets empty."""
    env_tools = set()
    dir_tools = set()
    whitelist = set()
    blacklist = set()
    expected = {}
    result = reconcile_tools(env_tools, dir_tools, whitelist, blacklist)
    assert result == expected
