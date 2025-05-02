"""Core logic for the 'zlt tools reconcile' command."""

import structlog
from pathlib import Path
from typing import Any, Dict, Set, Tuple, List
from enum import Enum, auto

# Import dependencies from lib/tooling and common utils
from ....lib.tooling.environment_scanner import get_executables_from_env
from ....lib.tooling.tool_reconciler import (
    ToolStatus,
    reconcile_tools,
    _get_effective_status,
    _check_for_conflicts,
)
from ....lib.tooling.tools_dir_scanner import get_tool_dirs
from ....common.hierarchical_utils import ParsedHierarchy
# No config loader needed here, expects processed config

log = structlog.get_logger()


# Keep exception local if only used here
class ReconciliationError(Exception):
    """Custom exception for errors during tool reconciliation (used internally)."""

    pass


def _perform_reconciliation_logic(
    project_root_dir: Path,
    config_data: dict,  # Expects the fully loaded config from load_config
) -> Tuple[
    Dict[str, ToolStatus],
    Set[str],
    ParsedHierarchy,  # Return parsed whitelist
    ParsedHierarchy,  # Return parsed blacklist
    List[str],
    List[str],
    bool,
]:
    """Internal logic, adapted from dev_scripts/reconciliation_logic.py.

    Args:
        project_root_dir: Path to the project root.
        config_data: The fully processed configuration dictionary returned by load_config,
                     containing keys like 'parsed_whitelist', 'parsed_blacklist'.

    Returns tuple:
        - reconciliation_results: Dict[tool_name, ToolStatus]
        - managed_tools_set: Set[str] (Top-level tools considered managed by whitelist)
        - parsed_whitelist: ParsedHierarchy (The structure used for reconciliation)
        - parsed_blacklist: ParsedHierarchy (The structure used for reconciliation)
        - error_messages: List[str]
        - warning_messages: List[str]
        - has_errors: bool
    """
    logger = log  # Use module logger

    logger.info("Performing tool discovery and reconciliation logic...")
    errors_found = False
    error_messages = []
    warning_messages = []

    tool_defs_dir = project_root_dir / "src" / "zeroth_law" / "tools"

    # 1. Get PRE-PARSED Config data
    try:
        # Directly retrieve the parsed dictionaries from the config_data object
        whitelist: ParsedHierarchy = config_data.get("parsed_whitelist", {})
        blacklist: ParsedHierarchy = config_data.get("parsed_blacklist", {})
        if not isinstance(whitelist, dict) or not isinstance(blacklist, dict):
            raise TypeError("Parsed whitelist/blacklist in config_data are not dictionaries.")
        logger.info(f"Using pre-parsed Whitelist: {whitelist}, Blacklist: {blacklist}")

    except (TypeError, KeyError, Exception) as e:
        msg = f"Failed to retrieve or validate parsed whitelist/blacklist from config_data: {e}"
        logger.error(msg, exc_info=True)
        raise ReconciliationError(msg) from e

    # 2. Scan Environment & Tool Defs Dir
    try:
        if not tool_defs_dir.is_dir():
            raise FileNotFoundError(f"Tool definitions directory not found: {tool_defs_dir}")
        dir_tools = get_tool_dirs(tool_defs_dir)
        logger.info(f"Found {len(dir_tools)} tool definitions in {tool_defs_dir}.")

        whitelist_top_level_tools = set(whitelist.keys())
        logger.debug(f"Filtering env executables based on whitelist keys: {whitelist_top_level_tools}")

        venv_path = project_root_dir / ".venv"
        venv_bin_path = venv_path / "bin"
        if not venv_bin_path.is_dir():
            log.warning(f"Expected venv bin path not found: {venv_bin_path}. Proceeding with empty env_tools list.")
            env_tools = set()
        else:
            log.debug(f"Scanning environment executables in: {venv_bin_path}")
            env_tools = get_executables_from_env(venv_bin_path)

        logger.info(f"Found {len(env_tools)} relevant executables in environment after filtering.")
    except FileNotFoundError as e:
        logger.error(str(e))
        raise ReconciliationError(str(e)) from e
    except Exception as e:
        msg = f"Unexpected error during environment or directory scan: {e}"
        logger.error(msg, exc_info=True)
        raise ReconciliationError(msg) from e

    # 3. Reconcile (Uses the parsed dictionaries directly)
    logger.debug(f"Reconciling with:")
    logger.debug(f"  Whitelist (Parsed): {whitelist}")
    logger.debug(f"  Blacklist (Parsed): {blacklist}")
    logger.debug(f"  Env Tools (filtered): {env_tools}")
    logger.debug(f"  Dir Tools: {dir_tools}")
    reconciliation_results = reconcile_tools(
        whitelist=whitelist,
        blacklist=blacklist,
        env_tools=env_tools,
        dir_tools=dir_tools,
    )
    logger.info("Tool reconciliation logic complete.")

    # 4. Analyze Results & Collect Messages
    managed_tools_set = {tool for tool, node in whitelist.items() if node.get("_explicit") or node.get("_all")}

    # 5. Analyze Results & Collect Messages
    managed_tools_for_processing = set()
    for tool, status in reconciliation_results.items():
        if status == ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR:
            msg = (
                f"ERROR: Tool '{tool}' has directory in tools/ but is BLACKLISTED. "
                f"Remove directory: {tool_defs_dir.relative_to(project_root_dir) / tool}. "
                f"Alternatively, run 'zlt tools sync --prune' to remove all such directories."
            )
            logger.error(msg)
            error_messages.append(msg)
            errors_found = True
        elif status == ToolStatus.ERROR_MISSING_WHITELISTED:
            msg = (
                f"ERROR: Tool '{tool}' is WHITELISTED but MISSING from tools/ directory. "
                f"Run 'zlt tools sync' or remove from whitelist."
            )
            logger.error(msg)
            error_messages.append(msg)
            errors_found = True
        elif status == ToolStatus.NEW_ENV_TOOL:
            msg = (
                f"ERROR: Tool '{tool}' found in environment but not managed (whitelist/blacklist). "
                f"Run 'zlt tools add-whitelist {tool}' or 'zlt tools add-blacklist {tool}'."
            )
            logger.error(msg)
            error_messages.append(msg)
            errors_found = True  # Treat new tools as errors requiring action
        elif status == ToolStatus.ERROR_ORPHAN_IN_TOOLS_DIR:
            msg = (
                f"WARNING: Orphan directory for '{tool}' found in tools/ but not managed. "
                f"Run 'zlt tools add-whitelist {tool}', 'zlt tools add-blacklist {tool}', "
                f"or remove directory (e.g., using 'zlt tools sync --prune')."
            )
            logger.warning(msg)
            warning_messages.append(msg)
        elif (
            status == ToolStatus.MANAGED_OK
            or status == ToolStatus.MANAGED_MISSING_ENV
            or status == ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR
        ):
            managed_tools_for_processing.add(tool)

    logger.info(f"Identified {len(managed_tools_for_processing)} tools considered effectively managed.")

    # Return results including error status and the parsed lists
    return (
        reconciliation_results,
        managed_tools_for_processing,
        whitelist,  # Return the parsed dict
        blacklist,  # Return the parsed dict
        error_messages,
        warning_messages,
        errors_found,
    )


def _print_reconciliation_summary(
    results: Dict[str, ToolStatus],
    warnings: List[str],
    errors: List[str],
    whitelist: ParsedHierarchy,  # Need parsed lists for detailed checks
    blacklist: ParsedHierarchy,
) -> None:
    """Prints a human-readable summary of the reconciliation results."""
    # Determine project root for relative paths - assumes CWD or passed context
    try:
        project_root = Path(".").resolve()  # Basic assumption
    except Exception:
        project_root = Path(".")  # Fallback

    tool_defs_dir = project_root / "src" / "zeroth_law" / "tools"

    # Print Errors first
    if errors:
        click.echo("\n--- Reconciliation Errors ---")
        for msg in errors:
            click.secho(msg, fg="red")

    # Print Warnings next
    if warnings:
        click.echo("\n--- Reconciliation Warnings ---")
        for msg in warnings:
            click.secho(msg, fg="yellow")

    # Print Detailed Status Table if no errors and no warnings, or always?
    # Let's print details unless suppressed by flags later
    click.echo("\n--- Tool Reconciliation Status ---")
    if not results:
        click.echo("No tools found or processed.")
        return

    # Prepare data for a simple table (could use rich.Table later)
    headers = ["Tool", "Source(s)", "Whitelist Status", "Blacklist Status", "Overall Status"]
    rows = []
    for tool, status in sorted(results.items()):
        # Determine source
        sources = []
        if (tool_defs_dir / tool).is_dir():
            sources.append("tools/")
        # Need env_tools list here to check environment source
        # Placeholder: assume env check happened before
        # if tool in env_tools: sources.append("env") # Needs env_tools context

        # Determine effective list status using the parsed hierarchies
        wl_effective_status = _get_effective_status(tool.split(":"), whitelist, blacklist)
        bl_effective_status = _get_effective_status(tool.split(":"), blacklist, whitelist)

        wl_status_str = str(wl_effective_status)
        bl_status_str = str(bl_effective_status)

        # Format overall status
        status_str = status.name
        color = (
            "green"
            if "OK" in status_str
            else ("yellow" if "WARNING" in status_str or "NEW" in status_str or "ORPHAN" in status_str else "red")
        )

        rows.append(
            [
                tool,
                ", ".join(sources) if sources else "-",
                wl_status_str,
                bl_status_str,
                click.style(status_str, fg=color),
            ]
        )

    # Basic print formatting (manual column widths)
    # TODO: Use tabulate or rich for better formatting
    col_widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = "-+- ".join("-" * w for w in col_widths)
    click.echo(header_line)
    click.echo(separator)
    for row in rows:
        # Handle styled last column
        styled_row = [str(item) for item in row[:-1]] + [row[-1]]
        line = " | ".join(f"{styled_row[i]:<{col_widths[i]}}" for i in range(len(headers)))
        click.echo(line)

    click.echo()
    if errors or warnings:
        click.echo("Reconciliation finished with issues.")
    else:
        click.echo("Reconciliation successful. All detected tools are consistent.")
