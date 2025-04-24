"""Shared logic for discovering, reconciling, and filtering tools."""

import logging
from pathlib import Path
from typing import Any, Dict, Set, Tuple

from .config_reader import load_tool_lists_from_toml
from .environment_scanner import get_executables_from_env
from .tool_reconciler import ToolStatus, reconcile_tools
from .tools_dir_scanner import get_tool_dirs

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ReconciliationError(Exception):
    """Custom exception for errors during tool reconciliation."""

    pass


def perform_tool_reconciliation(project_root_dir: Path, tool_defs_dir: Path) -> Tuple[Dict[str, ToolStatus], Set[str]]:
    """
    Performs the full tool discovery, reconciliation, and filtering process.

    Args:
        project_root_dir: The root directory of the project.
        tool_defs_dir: The directory containing tool definitions.

    Returns:
        A tuple containing:
            - The full reconciliation results dictionary.
            - A set of managed tool names suitable for further processing.

    Raises:
        ReconciliationError: If any errors are detected during reconciliation.
        FileNotFoundError: If pyproject.toml or tool_defs_dir are not found.
        Exception: For other unexpected errors during scanning or reading.
    """
    logger.info("Starting tool discovery and reconciliation...")

    # 1. Read Config
    config_path = project_root_dir / "pyproject.toml"
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    whitelist, blacklist = load_tool_lists_from_toml(config_path)
    logger.info(f"Whitelist: {whitelist}, Blacklist: {blacklist}")

    # 2. Scan Environment
    env_tools = get_executables_from_env()
    logger.info(f"Found {len(env_tools)} executables in environment.")

    # 3. Scan Tool Definitions Directory
    if not tool_defs_dir.is_dir():
        raise FileNotFoundError(f"Tool definitions directory not found: {tool_defs_dir}")
    dir_tools = get_tool_dirs(tool_defs_dir)
    logger.info(f"Found {len(dir_tools)} tool definitions in {tool_defs_dir}.")

    # 4. Reconcile
    reconciliation_results = reconcile_tools(
        whitelist=whitelist,
        blacklist=blacklist,
        env_tools=env_tools,
        dir_tools=dir_tools,
    )
    logger.info("Tool reconciliation complete.")

    # 5. Check for Errors and Filter
    errors_found = False
    managed_tools_for_processing = set()

    for tool, status in reconciliation_results.items():
        # Check only for valid error statuses defined in ToolStatus
        if status in (
            ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR,
            ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR,
            ToolStatus.ERROR_MISSING_WHITELISTED,
        ):
            logger.error(f"Reconciliation Error! Tool: {tool}, Status: {status.name}")
            errors_found = True
        elif status in (
            ToolStatus.MANAGED_OK,
            ToolStatus.MANAGED_MISSING_ENV,
            ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR,
        ):
            managed_tools_for_processing.add(tool)

    if errors_found:
        raise ReconciliationError("Errors detected during tool reconciliation. See logs.")

    logger.info(f"Identified {len(managed_tools_for_processing)} managed tools for processing.")

    return reconciliation_results, managed_tools_for_processing
