# FILE: src/zeroth_law/subcommands/tools/sync/_identify_target_tools.py
"""Helper function for Stage 3: Identifying target tools."""

from typing import Tuple, Dict, Set, Optional
import structlog

# --- Import project modules --- #
# Relative path needs adjustment (add one more dot)
from ..reconcile import ToolStatus  # Import from sibling command

log = structlog.get_logger()


def _identify_target_tools(
    specific_tools: Tuple[str, ...],
    reconciliation_results: Dict[str, ToolStatus],
    managed_tools_set: Set[str],
) -> Optional[Set[str]]:
    """STAGE 3: Determines the final set of tool names to target based on --tool option.

    Returns the set of target tool names, or None if no valid targets found.
    """
    log.info("STAGE 3: Identifying target tools...")
    target_tool_names: Set[str]
    if specific_tools:
        target_tool_names = set(specific_tools)
        all_known_tools = set(reconciliation_results.keys())
        missing_specified = target_tool_names - all_known_tools
        if missing_specified:
            log.warning(f"Specified tools not found in reconciliation results: {missing_specified}")
        target_tool_names = target_tool_names.intersection(all_known_tools)
        if not target_tool_names:
            log.error("None of the specified tools are known. Nothing to sync.")
            return None
    else:
        target_tool_names = managed_tools_set
        if not target_tool_names:
            log.info("No managed tools identified by reconciliation. Nothing to sync.")
            return None

    log.info(f"Targeting {len(target_tool_names)} tools for sync: {sorted(list(target_tool_names))}")
    return target_tool_names
