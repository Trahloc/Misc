"""Reconciles discovered tools from environment and tools directory against configuration."""

from enum import Enum, auto
from typing import Set, Dict
import logging

log = logging.getLogger(__name__)

class ToolStatus(Enum):
    """Represents the reconciliation status of a discovered tool."""
    MANAGED_OK = auto()                      # In tools/, whitelisted, in env (Ideal state for managed)
    MANAGED_MISSING_ENV = auto()             # In tools/, whitelisted, NOT in env (Needs install?)
    WHITELISTED_NOT_IN_TOOLS_DIR = auto()    # Whitelisted, in env, NOT in tools/ (Needs baseline generation)
    BLACKLISTED_IN_ENV = auto()              # Blacklisted, in env, NOT in tools/ (Correct state for blacklisted)
    NEW_ENV_TOOL = auto()                    # In env, NOT in tools/, whitelist, or blacklist (Needs classification)
    # Error States
    ERROR_BLACKLISTED_IN_TOOLS_DIR = auto() # Blacklisted AND in tools/ (Contradiction)
    ERROR_ORPHAN_IN_TOOLS_DIR = auto()      # In tools/, NOT whitelisted or blacklisted (Needs classification)
    ERROR_MISSING_WHITELISTED = auto()      # Whitelisted, NOT in env or tools/ (Config error or missing tool)


def reconcile_tools(
    env_tools: Set[str],
    dir_tools: Set[str],
    whitelist: Set[str],
    blacklist: Set[str],
) -> Dict[str, ToolStatus]:
    """Reconciles tool sets from environment, tools directory, whitelist, and blacklist.

    Args:
        env_tools: Set of tool names discovered in the environment bin directory.
        dir_tools: Set of tool names discovered as directories in the tools directory.
        whitelist: Set of tool names explicitly whitelisted in configuration.
        blacklist: Set of tool names explicitly blacklisted in configuration.

    Returns:
        A dictionary mapping each discovered tool name to its reconciled ToolStatus.
    """
    reconciliation_status: Dict[str, ToolStatus] = {}
    all_potential_tools = env_tools.union(dir_tools).union(whitelist).union(blacklist)

    log.debug(f"Reconciling {len(all_potential_tools)} potential tools...")
    log.debug(f"Env tools: {env_tools}")
    log.debug(f"Dir tools: {dir_tools}")
    log.debug(f"Whitelist: {whitelist}")
    log.debug(f"Blacklist: {blacklist}")

    for tool in all_potential_tools:
        in_env = tool in env_tools
        in_dir = tool in dir_tools
        is_whitelisted = tool in whitelist
        is_blacklisted = tool in blacklist

        status: ToolStatus | None = None

        # --- Error States First ---
        if is_blacklisted and in_dir:
            status = ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR
        elif in_dir and not is_whitelisted and not is_blacklisted:
            status = ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR
        elif is_whitelisted and not in_env and not in_dir:
            status = ToolStatus.ERROR_MISSING_WHITELISTED

        # --- Managed States (Requires Whitelist and Dir presence ideally) ---
        elif is_whitelisted and in_dir:
            if in_env:
                status = ToolStatus.MANAGED_OK
            else:
                status = ToolStatus.MANAGED_MISSING_ENV

        # --- Other Valid States ---
        elif is_whitelisted and in_env and not in_dir:
             status = ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR # Whitelisted, but needs setup
        elif is_blacklisted and in_env and not in_dir:
            status = ToolStatus.BLACKLISTED_IN_ENV # Correct state for blacklisted
        elif in_env and not in_dir and not is_whitelisted and not is_blacklisted:
            status = ToolStatus.NEW_ENV_TOOL # Needs classification

        # --- Handle tools only in lists but not found anywhere else (covered by ERROR_MISSING_WHITELISTED) ---
        # No explicit case needed here as ERROR_MISSING_WHITELISTED covers it.
        # Also handles cases only in blacklist/env (BLACKLISTED_IN_ENV) or only in env (NEW_ENV_TOOL).

        if status:
            reconciliation_status[tool] = status
        else:
            # This case should ideally not be reached if logic is exhaustive,
            # but log a warning if it does.
            log.warning(
                f"Tool '{tool}' did not match any reconciliation criteria. "
                f"(in_env={in_env}, in_dir={in_dir}, wl={is_whitelisted}, bl={is_blacklisted})"
            )

    log.debug(f"Reconciliation complete: {reconciliation_status}")
    return reconciliation_status