"""Core logic for the 'zlt tools reconcile' command."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Set, Tuple, List
from enum import Enum, auto
import sys  # Add sys import
import structlog  # Restore import

# Import dependencies from lib/tooling and common utils
from ....lib.tooling.environment_scanner import get_executables_from_env
from ....lib.tooling.tool_reconciler import (
    ToolStatus,
    reconcile_tools,
    _get_effective_status,
    _check_for_conflicts,
)
from ....lib.tooling.tools_dir_scanner import get_tool_dirs, scan_for_command_sequences
from ....common.hierarchical_utils import ParsedHierarchy, parse_to_nested_dict
from ....common.hierarchical_utils import ParsedHierarchy as HierarchicalListData  # Correct import + Alias
# No config loader needed here, expects processed config

logger = structlog.get_logger()  # Restore logger


# Keep exception local if only used here
class ReconciliationError(Exception):
    """Custom exception for errors during tool reconciliation (used internally)."""

    pass


def _perform_reconciliation_logic(
    project_root_dir: Path,
    config_data: Dict[str, Any],
) -> Tuple[
    Dict[str, ToolStatus],
    Set[str],
    HierarchicalListData,  # Return parsed whitelist
    HierarchicalListData,  # Return parsed blacklist
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
    # print("DEBUG [_logic]: Entering _perform_reconciliation_logic", file=sys.stderr)
    # sys.stderr.flush()
    logger.debug("Entering _perform_reconciliation_logic")  # Restore logger

    errors_found = False
    error_messages = []
    warning_messages = []

    # Construct paths
    tool_defs_dir = project_root_dir / "src" / "zeroth_law" / "tools"
    venv_bin_path = project_root_dir / ".venv" / "bin"

    # 1. Get PRE-PARSED Config data
    # print("DEBUG [_logic]: Parsing whitelist/blacklist from config_data", file=sys.stderr)
    # sys.stderr.flush()
    logger.debug("Parsing whitelist/blacklist from config_data")  # Restore logger
    whitelist_data = config_data.get("managed_tools", {}).get("whitelist", [])
    blacklist_data = config_data.get("managed_tools", {}).get("blacklist", [])
    try:
        whitelist = parse_to_nested_dict(whitelist_data)
        blacklist = parse_to_nested_dict(blacklist_data)
    except ValueError as e:
        msg = f"Failed to retrieve or validate parsed whitelist/blacklist from config_data: {e}"
        # print(msg, file=sys.stderr)
        logger.error(msg, error=e)  # Restore logger
        raise ReconciliationError(msg) from e
    # print(f"DEBUG [_logic]: Parsed whitelist (top-level keys): {list(whitelist.keys())}", file=sys.stderr)
    # print(f"DEBUG [_logic]: Parsed blacklist (top-level keys): {list(blacklist.keys())}", file=sys.stderr)
    # sys.stderr.flush()
    logger.debug(
        "Parsed lists", whitelist_keys=list(whitelist.keys()), blacklist_keys=list(blacklist.keys())
    )  # Restore logger

    # 2. Scan Tool Definitions Directory for SEQUENCES
    # print("DEBUG [_logic]: Scanning tool definitions directory for sequences...", file=sys.stderr)
    # sys.stderr.flush()
    logger.debug("Scanning tool definitions directory for sequences", path=str(tool_defs_dir))  # Restore logger
    defined_sequences: Set[Tuple[str, ...]] = set()  # Initialize
    try:
        if not tool_defs_dir.is_dir():
            raise FileNotFoundError(f"Tool definitions directory not found: {tool_defs_dir}")
        # --- Scan for sequences --- #
        # print(f"DEBUG [_logic]: Calling scan_for_command_sequences({tool_defs_dir})...", file=sys.stderr)
        # sys.stderr.flush()
        logger.debug("Calling scan_for_command_sequences", path=str(tool_defs_dir))  # Restore logger
        seq_scan_start = time.monotonic()
        # Convert list of tuples to set of tuples
        defined_sequences = set(scan_for_command_sequences(tool_defs_dir))
        seq_scan_duration = time.monotonic() - seq_scan_start
        # print(f"INFO [_logic]: scan_for_command_sequences took {seq_scan_duration:.4f} seconds", file=sys.stderr)
        # sys.stderr.flush()
        logger.info(
            "scan_for_command_sequences complete", duration=f"{seq_scan_duration:.4f}s", count=len(defined_sequences)
        )  # Restore logger
        # print(f"INFO [_logic]: Found {len(defined_sequences)} defined command sequences in {tool_defs_dir}.", file=sys.stderr)
        # print(f"DEBUG [_logic]: Defined sequences: {defined_sequences}", file=sys.stderr) # Potentially large output
        # sys.stderr.flush()

        # Optional: Check for unexpected dirs (using get_tool_dirs if still needed for warnings)
        dir_tools = get_tool_dirs(tool_defs_dir)  # Need to call this if we want the warning
        whitelist_top_level_tools = set(whitelist.keys())
        discovered_unexpected_dirs = dir_tools - whitelist_top_level_tools
        if discovered_unexpected_dirs:
            warning_messages.append(
                f"Found unexpected tool definition directories not in whitelist: {sorted(list(discovered_unexpected_dirs))}"
            )
            logger.warning(
                "Found unexpected tool definition directories", unexpected=sorted(list(discovered_unexpected_dirs))
            )  # Log warning

    except FileNotFoundError as e:
        # print(f"ERROR [_logic]: {str(e)}", file=sys.stderr)
        # sys.stderr.flush()
        logger.error("Tool definitions directory not found", path=str(tool_defs_dir), error=str(e))  # Restore logger
        errors_found = True
    except OSError as e:
        # print(f"ERROR [_logic]: Error scanning tool definitions directory {tool_defs_dir}: {e}", file=sys.stderr)
        # sys.stderr.flush()
        logger.error(
            "Error scanning tool definitions directory", path=str(tool_defs_dir), error=str(e)
        )  # Restore logger
        errors_found = True

    # 3. Scan Environment (e.g., .venv/bin)
    # print("DEBUG [_logic]: Scanning environment executables...", file=sys.stderr)
    # sys.stderr.flush()
    logger.debug("Scanning environment executables", path=str(venv_bin_path))  # Restore logger
    env_tools: Set[str] = set()
    try:
        if not venv_bin_path or not venv_bin_path.is_dir():
            # print(f"WARNING [_logic]: Expected venv bin path not found or not a directory: {venv_bin_path}. Proceeding with empty env_tools list.", file=sys.stderr)
            # sys.stderr.flush()
            logger.warning("Venv bin path not found or not a directory", path=str(venv_bin_path))  # Restore logger
            env_tools = set()
        else:
            # print(f"DEBUG [_logic]: Scanning environment executables in: {venv_bin_path}", file=sys.stderr)
            # sys.stderr.flush()
            # print(f"DEBUG [_logic]: Calling get_executables_from_env({venv_bin_path})...", file=sys.stderr)
            # sys.stderr.flush()
            logger.debug("Calling get_executables_from_env", path=str(venv_bin_path))  # Restore logger
            env_scan_start = time.monotonic()
            # Pass config_data to the scanner
            # env_tools = get_executables_from_env(venv_bin_path, config_data=config_data)
            env_tools = get_executables_from_env(venv_bin_path)  # Revert: remove config_data
            env_scan_duration = time.monotonic() - env_scan_start
            # print(f"INFO [_logic]: get_executables_from_env took {env_scan_duration:.4f} seconds", file=sys.stderr)
            # sys.stderr.flush()
            logger.info(
                "get_executables_from_env complete", duration=f"{env_scan_duration:.4f}s", count=len(env_tools)
            )  # Restore logger
        # print(f"INFO [_logic]: Found {len(env_tools)} relevant executables in environment after filtering. Tools: {sorted(list(env_tools))}", file=sys.stderr)
        # sys.stderr.flush()
        logger.debug("Environment scan results", count=len(env_tools), tools=sorted(list(env_tools)))  # Restore logger
    except FileNotFoundError as e:
        # print(f"ERROR [_logic]: Error constructing venv path (check project root): {e}", file=sys.stderr)
        # sys.stderr.flush()
        logger.error("Error determining venv path", error=str(e))  # Restore logger
        errors_found = True
    except OSError as e:
        # print(f"ERROR [_logic]: Error scanning environment bin directory: {e}", file=sys.stderr)
        # sys.stderr.flush()
        logger.error(
            "Error scanning environment bin directory", path=str(venv_bin_path), error=str(e)
        )  # Restore logger
        errors_found = True

    # 4. Reconcile (Uses the parsed dictionaries and scanned data)
    # print("DEBUG [_logic]: Reconciling with:", file=sys.stderr)
    # print(f"DEBUG [_logic]:   Whitelist (Parsed Keys): {list(whitelist.keys())}", file=sys.stderr)
    # print(f"DEBUG [_logic]:   Blacklist (Parsed Keys): {list(blacklist.keys())}", file=sys.stderr)
    # print(f"DEBUG [_logic]:   Env Tools ({len(env_tools)}): {sorted(list(env_tools))}", file=sys.stderr)
    # print(f"DEBUG [_logic]:   Defined Sequences ({len(defined_sequences)}): {defined_sequences}", file=sys.stderr)
    # sys.stderr.flush()
    logger.debug(
        "Performing reconciliation",
        whitelist_keys=list(whitelist.keys()),
        blacklist_keys=list(blacklist.keys()),
        env_count=len(env_tools),
        seq_count=len(defined_sequences),
    )  # Restore logger
    reconciliation_results = reconcile_tools(
        whitelist=whitelist,
        blacklist=blacklist,
        env_tools=env_tools,
        defined_sequences=defined_sequences,  # Pass the correct argument
        # dir_tools=dir_tools, # Incorrect argument
    )
    # print("INFO [_logic]: Tool reconciliation logic complete.", file=sys.stderr)
    # sys.stderr.flush()
    logger.info("Tool reconciliation complete", results_count=len(reconciliation_results))  # Restore logger

    # 5. Analyze Results & Collect Messages
    managed_tools_set = {tool for tool, node in whitelist.items() if node.get("_explicit") or node.get("_all")}
    managed_tools_for_processing = set()
    for tool, status in reconciliation_results.items():
        if status == ToolStatus.ERROR_BLACKLISTED_HAS_DEFS:
            msg = (
                f"ERROR: Tool '{tool}' has definitions but is BLACKLISTED. "
                f"Remove definitions from: {tool_defs_dir.relative_to(project_root_dir) / tool}. "
            )
            # print(msg, file=sys.stderr)
            logger.error(msg, tool=tool)  # Restore logger
            error_messages.append(msg)
            errors_found = True
        elif status == ToolStatus.ERROR_MISSING_WHITELISTED:
            msg = f"ERROR: Tool '{tool}' is WHITELISTED but MISSING from environment and definitions. "
            # print(msg, file=sys.stderr)
            logger.error(msg, tool=tool)  # Restore logger
            error_messages.append(msg)
            errors_found = True
        elif status == ToolStatus.ERROR_ORPHAN_IN_ENV:
            msg = (
                f"ERROR: Tool '{tool}' found in environment but not managed (whitelist/blacklist). "
                f"Run 'zlt tools add-whitelist {tool}' or 'zlt tools add-blacklist {tool}'."
            )
            # print(msg, file=sys.stderr)
            logger.error(msg, tool=tool)  # Restore logger
            error_messages.append(msg)
            errors_found = True
        elif status == ToolStatus.ERROR_ORPHAN_HAS_DEFS:
            msg = (
                f"WARNING: Orphan definitions for '{tool}' found in tools/ but not managed. "
                f"Run 'zlt tools add-whitelist {tool}', 'zlt tools add-blacklist {tool}', "
            )
            # print(msg, file=sys.stderr)
            logger.warning(msg, tool=tool)  # Restore logger
            warning_messages.append(msg)
        elif status == ToolStatus.MANAGED_OK:
            managed_tools_for_processing.add(tool)
        elif status == ToolStatus.MANAGED_MISSING_ENV:
            msg = f"Managed tool '{tool}' has definitions but is missing from environment."
            logger.warning(msg, tool=tool)  # Restore logger
            warning_messages.append(msg)
            managed_tools_for_processing.add(tool)  # Still process it
        elif status == ToolStatus.WHITELISTED_NO_DEFS:
            msg = f"Managed tool '{tool}' is in environment but has no definitions."
            logger.warning(msg, tool=tool)  # Restore logger
            warning_messages.append(msg)
            managed_tools_for_processing.add(tool)  # Still process it
        elif status == ToolStatus.BLACKLISTED_IN_ENV:
            pass
        elif status == ToolStatus.UNEXPECTED_STATE:
            msg = f"Tool '{tool}' encountered an unexpected reconciliation state."
            logger.error(msg, tool=tool)  # Restore logger
            error_messages.append(msg)
            errors_found = True

    # print(f"INFO [_logic]: Identified {len(managed_tools_for_processing)} tools considered effectively managed.", file=sys.stderr)
    # sys.stderr.flush()
    logger.info(
        "Identified managed tools for further processing", count=len(managed_tools_for_processing)
    )  # Restore logger

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
    whitelist: HierarchicalListData,  # Need parsed lists for detailed checks
    blacklist: HierarchicalListData,
) -> None:
    """Prints a human-readable summary of the reconciliation results."""
    # Use structlog for messages, click for final table output
    logger = structlog.get_logger("print_summary")
    try:
        import click
    except ImportError:
        logger.error("Click is required for printing reconciliation summary.")
        # Fallback or raise?
        return

    # Determine project root for relative paths - assumes CWD or passed context
    try:
        project_root = Path(".").resolve()  # Basic assumption
    except Exception:
        project_root = Path(".")  # Fallback

    tool_defs_dir = project_root / "src" / "zeroth_law" / "tools"

    # Print Errors first
    if errors:
        # print("\n--- Reconciliation Errors ---", file=sys.stderr)
        click.echo(click.style("\n--- Reconciliation Errors ---", fg="red", bold=True))
        for msg in errors:
            # print(msg, file=sys.stderr)
            click.secho(msg, fg="red")

    # Print Warnings next
    if warnings:
        # print("\n--- Reconciliation Warnings ---", file=sys.stderr)
        click.echo(click.style("\n--- Reconciliation Warnings ---", fg="yellow", bold=True))
        for msg in warnings:
            # print(msg, file=sys.stderr)
            click.secho(msg, fg="yellow")

    # Print Detailed Status Table if no errors and no warnings, or always?
    # Let's print details unless suppressed by flags later
    # print("\n--- Tool Reconciliation Status ---", file=sys.stderr)
    click.echo(click.style("\n--- Tool Reconciliation Status ---", bold=True))
    if not results:
        # print("No tools found or processed.", file=sys.stderr)
        click.echo("No tools found or processed.")
        return

    # Prepare data for a simple table (could use rich.Table later)
    headers = ["Tool", "Source(s)", "Whitelist Status", "Blacklist Status", "Overall Status"]
    rows = []
    # Need env_tools and defined_sequences here to show sources accurately
    # THIS FUNCTION NEEDS MORE CONTEXT - PASS ENV_TOOLS & DEFINED_SEQUENCES
    # For now, source calculation is omitted/placeholder
    env_tools_placeholder = set()  # Placeholder
    defined_sequences_placeholder = set()  # Placeholder

    for tool, status in sorted(results.items()):
        # Determine source
        sources = []
        # Check if any sequence starts with this tool name
        if any(seq[0] == tool for seq in defined_sequences_placeholder if seq):
            sources.append("defs")
        if tool in env_tools_placeholder:
            sources.append("env")

        # Determine effective list status using the parsed hierarchies
        # Note: _get_effective_status expects list path, using just [tool] for top-level
        wl_effective_status = _get_effective_status([tool], whitelist, blacklist)
        bl_effective_status = _get_effective_status([tool], blacklist, whitelist)

        wl_status_str = str(wl_effective_status)
        bl_status_str = str(bl_effective_status)

        # Format overall status
        status_str = status.name
        color = (
            "green"
            if "OK" in status_str
            else (
                "yellow"
                if "WARNING" in status_str
                or "NEW" in status_str
                or "ORPHAN" in status_str
                or "MISSING" in status_str
                or "NO_DEFS" in status_str
                else "red"
            )
        )
        # Style with click if available, otherwise just use the string
        styled_status = click.style(status_str, fg=color)

        rows.append(
            [
                tool,
                ", ".join(sources) if sources else "-",  # Source calculation is placeholder
                wl_status_str,
                bl_status_str,
                styled_status,
            ]
        )

    # Calculate widths based on plain strings first
    plain_rows = []
    for r in rows:
        # Use getattr to safely get unstyled version or fallback to str()
        plain_last_col = getattr(r[4], "unstyled", str(r[4]))
        plain_rows.append([str(r[0]), str(r[1]), str(r[2]), str(r[3]), plain_last_col])
    col_widths = [max(len(str(r[i])) for r in [headers] + plain_rows) for i in range(len(headers))]

    header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in col_widths)  # Adjusted separator slightly
    # print(header_line, file=sys.stderr)
    # print(separator, file=sys.stderr)
    click.echo(header_line)
    click.echo(separator)
    for i, row in enumerate(rows):
        # Print the row using original (potentially styled) elements and plain widths
        # Click/Rich handles the alignment correctly with ANSI codes present.
        line = " | ".join(f"{str(row[j]):<{col_widths[j]}}" for j in range(len(headers)))
        click.echo(line)

    # print(file=sys.stderr)
    click.echo()
    if errors or warnings:
        # print("Reconciliation finished with issues.", file=sys.stderr)
        click.secho("Reconciliation finished with issues.", fg=("red" if errors else "yellow"))
    else:
        # print("Reconciliation successful. All detected tools are consistent.", file=sys.stderr)
        click.secho("Reconciliation successful. All detected tools are consistent.", fg="green")
