"""Tests for src/zeroth_law/dev_scripts/reconciliation_logic.py"""

import logging
from pathlib import Path
from typing import Set, Dict, Tuple
from unittest.mock import patch, MagicMock

import pytest

# Import the target function and related classes/enums
from src.zeroth_law.dev_scripts.reconciliation_logic import (
    perform_tool_reconciliation,
    ReconciliationError,
)
from src.zeroth_law.dev_scripts.tool_reconciler import ToolStatus


# --- Fixtures ---


@pytest.fixture
def mock_paths(tmp_path) -> Tuple[Path, Path]:
    """Provides mocked project root and tool definitions paths."""
    project_root = tmp_path
    tool_defs = tmp_path / "src/zeroth_law/tools"
    tool_defs.mkdir(parents=True, exist_ok=True)
    # Create a dummy pyproject.toml
    (project_root / "pyproject.toml").touch()
    return project_root, tool_defs


# --- Test Cases ---


@patch("src.zeroth_law.dev_scripts.reconciliation_logic.load_tool_lists_from_toml")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.get_tool_dirs")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.get_executables_from_env")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.reconcile_tools")
def test_perform_reconciliation_success(
    mock_reconcile,
    mock_get_env,
    mock_get_dirs,
    mock_load_config,
    mock_paths,
    caplog,
):
    """Test successful reconciliation with no errors."""
    project_root, tool_defs = mock_paths
    caplog.set_level(logging.INFO)

    # Setup Mocks
    mock_load_config.return_value = ({"toolA", "toolB"}, {"toolC"})  # whitelist, blacklist
    mock_get_dirs.return_value = {"toolA"}
    mock_get_env.return_value = {"toolA", "toolB", "toolC"}
    mock_reconcile.return_value = {
        "toolA": ToolStatus.MANAGED_OK,
        "toolB": ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR,
        "toolC": ToolStatus.BLACKLISTED_IN_ENV,
    }

    # Execute
    results, managed, blacklist = perform_tool_reconciliation(project_root, tool_defs)

    # Assert
    assert results == {
        "toolA": ToolStatus.MANAGED_OK,
        "toolB": ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR,
        "toolC": ToolStatus.BLACKLISTED_IN_ENV,
    }
    assert managed == {"toolA", "toolB"}  # Only managed/whitelisted tools for processing
    assert blacklist == {"toolC"}
    assert "Tool reconciliation complete." in caplog.text
    assert "Identified 2 managed tools for processing." in caplog.text
    mock_load_config.assert_called_once_with(project_root / "pyproject.toml")
    mock_get_dirs.assert_called_once_with(tool_defs)
    mock_get_env.assert_called_once_with({"toolA", "toolB"}, {"toolA"})  # Called with whitelist, dir_tools
    mock_reconcile.assert_called_once_with(
        whitelist={"toolA", "toolB"},
        blacklist={"toolC"},
        env_tools={"toolA", "toolB", "toolC"},
        dir_tools={"toolA"},
    )


@patch("src.zeroth_law.dev_scripts.reconciliation_logic.load_tool_lists_from_toml")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.get_tool_dirs")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.get_executables_from_env")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.reconcile_tools")
def test_perform_reconciliation_error_missing_whitelisted(
    mock_reconcile,
    mock_get_env,
    mock_get_dirs,
    mock_load_config,
    mock_paths,
    caplog,
):
    """Test reconciliation failure due to ERROR_MISSING_WHITELISTED."""
    project_root, tool_defs = mock_paths
    caplog.set_level(logging.ERROR)

    mock_load_config.return_value = ({"toolA", "missingTool"}, set())
    mock_get_dirs.return_value = {"toolA"}
    mock_get_env.return_value = {"toolA"}
    mock_reconcile.return_value = {
        "toolA": ToolStatus.MANAGED_OK,
        "missingTool": ToolStatus.ERROR_MISSING_WHITELISTED,
    }

    with pytest.raises(ReconciliationError, match="Errors detected"):
        perform_tool_reconciliation(project_root, tool_defs)

    assert "Reconciliation Error! Tool: missingTool, Status: ERROR_MISSING_WHITELISTED" in caplog.text


@patch("src.zeroth_law.dev_scripts.reconciliation_logic.load_tool_lists_from_toml")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.get_tool_dirs")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.get_executables_from_env")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.reconcile_tools")
def test_perform_reconciliation_error_blacklisted_in_dir(
    mock_reconcile,
    mock_get_env,
    mock_get_dirs,
    mock_load_config,
    mock_paths,
    caplog,
):
    """Test reconciliation failure due to ERROR_BLACKLISTED_IN_TOOLS_DIR."""
    project_root, tool_defs = mock_paths
    caplog.set_level(logging.ERROR)

    mock_load_config.return_value = ({"toolA"}, {"blacklistedTool"})
    mock_get_dirs.return_value = {"toolA", "blacklistedTool"}  # Blacklisted tool exists in dir
    mock_get_env.return_value = {"toolA", "blacklistedTool"}
    mock_reconcile.return_value = {
        "toolA": ToolStatus.MANAGED_OK,
        "blacklistedTool": ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR,
    }

    with pytest.raises(ReconciliationError, match="Errors detected"):
        perform_tool_reconciliation(project_root, tool_defs)

    assert "Reconciliation Error! Tool: blacklistedTool, Status: ERROR_BLACKLISTED_IN_TOOLS_DIR" in caplog.text


@patch("src.zeroth_law.dev_scripts.reconciliation_logic.load_tool_lists_from_toml")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.get_tool_dirs")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.get_executables_from_env")
@patch("src.zeroth_law.dev_scripts.reconciliation_logic.reconcile_tools")
def test_perform_reconciliation_warning_orphan_in_dir(
    mock_reconcile,
    mock_get_env,
    mock_get_dirs,
    mock_load_config,
    mock_paths,
    caplog,
):
    """Test reconciliation handles ERROR_ORPHAN_IN_TOOLS_DIR as a warning, not error."""
    project_root, tool_defs = mock_paths
    caplog.set_level(logging.WARNING)

    mock_load_config.return_value = ({"toolA"}, {"toolC"})
    mock_get_dirs.return_value = {"toolA", "orphanTool"}  # Orphan tool in dir
    mock_get_env.return_value = {"toolA", "toolC"}
    mock_reconcile.return_value = {
        "toolA": ToolStatus.MANAGED_OK,
        "toolC": ToolStatus.BLACKLISTED_IN_ENV,
        "orphanTool": ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR,
    }

    # Execute - Should NOT raise ReconciliationError
    results, managed, blacklist = perform_tool_reconciliation(project_root, tool_defs)

    # Assert Warning Log
    assert "Reconciliation Warning! Orphan Tool Found: orphanTool, Status: ERROR_ORPHAN_IN_TOOLS_DIR" in caplog.text

    # Assert results are returned correctly despite the warning
    assert results == {
        "toolA": ToolStatus.MANAGED_OK,
        "toolC": ToolStatus.BLACKLISTED_IN_ENV,
        "orphanTool": ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR,
    }
    assert managed == {"toolA"}  # Orphan is not included in managed
    assert blacklist == {"toolC"}


def test_perform_reconciliation_file_not_found(mock_paths):
    """Test FileNotFoundError if pyproject.toml is missing."""
    project_root, tool_defs = mock_paths
    # Delete the dummy config file
    (project_root / "pyproject.toml").unlink()

    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        perform_tool_reconciliation(project_root, tool_defs)


# Note: Testing FileNotFoundError for tool_defs_dir is harder because
# get_tool_dirs itself might handle the non-existent directory gracefully.
# The core logic of perform_tool_reconciliation depends on get_tool_dirs's return value.
# Similarly, testing exceptions from underlying functions (toml load, scans)
# might be better suited for the unit tests of those specific functions.
