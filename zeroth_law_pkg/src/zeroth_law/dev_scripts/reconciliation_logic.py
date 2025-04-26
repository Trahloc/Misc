"""Shared logic for discovering, reconciling, and filtering tools."""

import logging
from pathlib import Path
from typing import Any, Dict, Set, Tuple
from pprint import pprint

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


def perform_tool_reconciliation(
    project_root_dir: Path, tool_defs_dir: Path
) -> Tuple[Dict[str, ToolStatus], Set[str], Set[str]]:
    """
    Performs the full tool discovery, reconciliation, and filtering process.

    Args:
        project_root_dir: The root directory of the project.
        tool_defs_dir: The directory containing tool definitions.

    Returns:
        A tuple containing:
            - The full reconciliation results dictionary.
            - A set of managed tool names suitable for further processing.
            - The blacklist set loaded from the config.

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
    dir_tools = get_tool_dirs(tool_defs_dir)
    logger.info(f"Found {len(dir_tools)} tool definitions in {tool_defs_dir}.")
    env_tools = get_executables_from_env(whitelist, dir_tools)
    logger.info(f"Found {len(env_tools)} relevant executables in environment after filtering.")

    # 3. Scan Tool Definitions Directory - REMOVED Redundant Scan
    # We already scanned dir_tools in step 2, use that result.
    # if not tool_defs_dir.is_dir():
    #     raise FileNotFoundError(f\"Tool definitions directory not found: {tool_defs_dir}\")
    # dir_tools = get_tool_dirs(tool_defs_dir) # Redundant scan removed
    # logger.info(f\"Found {len(dir_tools)} tool definitions in {tool_defs_dir}.\") # Logged in step 2

    # 4. Reconcile
    logger.debug(f"Reconciling with:")
    logger.debug(f"  Whitelist: {whitelist}")
    logger.debug(f"  Blacklist: {blacklist}")
    logger.debug(f"  Env Tools (filtered): {env_tools}")
    logger.debug(f"  Dir Tools: {dir_tools}")
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
        # Using explicit OR instead of tuple membership for clarity
        if (
            status == ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR
            or status == ToolStatus.ERROR_MISSING_WHITELISTED
            # CRITICAL: Treat newly discovered, unmanaged tools in env as errors
            or status == ToolStatus.NEW_ENV_TOOL
        ):
            # Default message structure, will be overwritten by specific conditions
            log_message = f"Reconciliation Error! Tool: {tool}, Status: {status.name}."

            # Specific messages for clarity
            if status == ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR:
                log_message = (
                    f"Reconciliation Error! Tool: {tool}, Status: {status.name}. "
                    f"A directory exists in '{tool_defs_dir.relative_to(project_root_dir)}' "
                    "but the tool is blacklisted in pyproject.toml. Remove the directory."
                )
            elif status == ToolStatus.ERROR_MISSING_WHITELISTED:
                log_message = (
                    f"Reconciliation Error! Tool: {tool}, Status: {status.name}. "
                    f"Tool is whitelisted in pyproject.toml but no directory found in '{tool_defs_dir.relative_to(project_root_dir)}'. "
                    "Run regeneration scripts or remove from whitelist."
                )
            elif status == ToolStatus.NEW_ENV_TOOL:
                log_message = (
                    f"Reconciliation Error! Tool: {tool}, Status: {status.name}. "
                    "Found in environment but not in pyproject.toml whitelist or blacklist. "
                    "Please assess its long-term utility and add to either list."
                )

            logger.error(log_message)
            errors_found = True
        elif status == ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR:
            # Warn about orphan tools instead of treating as error
            logger.warning(
                f"Reconciliation Warning! Orphan Tool Found: {tool}, Status: {status.name}. "
                f"Directory exists in '{tool_defs_dir.relative_to(project_root_dir)}' but tool is not in whitelist or blacklist. "
                "Assess and add to pyproject.toml or remove directory."
            )
        elif (
            status == ToolStatus.MANAGED_OK
            or status == ToolStatus.MANAGED_MISSING_ENV
            or status == ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR
        ):
            managed_tools_for_processing.add(tool)

    # --- REMOVED DEBUG --- Print the final dict before raising error
    if errors_found:
        # from pprint import pprint
        # print("\n--- DEBUG: Reconciliation results BEFORE raising error: ---")
        # pprint(reconciliation_results)
        # print("--- END DEBUG ---")
        raise ReconciliationError("Errors detected during tool reconciliation. See logs.")

    logger.info(f"Identified {len(managed_tools_for_processing)} managed tools for processing.")

    return reconciliation_results, managed_tools_for_processing, blacklist
