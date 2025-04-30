# FILE: src/zeroth_law/subcommands/tools/reconcile.py
"""Implements the 'zlt tools reconcile' subcommand."""

import click
import structlog  # Replace logging with structlog
import json as json_lib  # Alias to avoid conflict with option name
from pathlib import Path
from typing import Any, Dict, Set, Tuple, List
from enum import Enum, auto

# TODO: [Implement Subcommand Blacklist] Reference TODO H.14 in TODO.md - This module needs to parse and apply subcommand specs from pyproject.toml.

# --- Updated imports from lib/tooling --- #
# from ...dev_scripts.config_reader import load_tool_lists_from_toml # No longer needed, reads from ctx
from ...lib.tooling.environment_scanner import get_executables_from_env
from ...lib.tooling.tool_reconciler import ToolStatus, reconcile_tools, _get_effective_status
from ...lib.tooling.tools_dir_scanner import get_tool_dirs

# Import type hint from new file
from ...common.hierarchical_utils import ParsedHierarchy

# Need config loading capability
from ...common.config_loader import load_config

log = structlog.get_logger()  # Use structlog


class ReconciliationError(Exception):
    """Custom exception for errors during tool reconciliation (used internally)."""

    pass


def _perform_reconciliation_logic(
    project_root_dir: Path,
    config_data: dict,  # Pass loaded config data
) -> Tuple[
    Dict[str, ToolStatus],
    Set[str],
    ParsedHierarchy,
    ParsedHierarchy,
    List[str],
    List[str],
    bool,
]:
    """Internal logic, adapted from dev_scripts/reconciliation_logic.py.

    Returns tuple:
        - reconciliation_results: Dict[tool_name, ToolStatus]
        - managed_tools_set: Set[str] (Top-level tools considered managed by whitelist)
        - parsed_whitelist: ParsedHierarchy
        - parsed_blacklist: ParsedHierarchy
        - error_messages: List[str]
        - warning_messages: List[str]
        - has_errors: bool
    """
    logger = log  # Use module logger

    # <<<--- REMOVE DEBUG PRINT HERE --->>>
    # logger.warning(f"DEBUG _perform_reconciliation_logic: Received config_data = {config_data}")
    # <<<--- END REMOVE DEBUG PRINT --->>>

    logger.info("Performing tool discovery and reconciliation logic...")
    errors_found = False
    error_messages = []
    warning_messages = []

    tool_defs_dir = project_root_dir / "src" / "zeroth_law" / "tools"

    # 1. Read Config (use the PARSED dictionaries from config_data)
    try:
        # Extract parsed dictionaries directly from the loaded config object
        managed_tools_config = config_data.get("managed-tools", {})
        # These are now expected to be Dict[str, Set[str]]
        whitelist: Dict[str, Set[str]] = managed_tools_config.get("whitelist", {})
        blacklist: Dict[str, Set[str]] = managed_tools_config.get("blacklist", {})
        logger.info(f"Whitelist (parsed): {whitelist}, Blacklist (parsed): {blacklist}")
    except Exception as e:
        # Keep this error handling, although type issues should be less likely now
        msg = f"Failed to extract parsed whitelist/blacklist from loaded config data: {e}"
        logger.error(msg)
        raise ReconciliationError(msg) from e

    # 2. Scan Environment & Tool Defs Dir
    try:
        if not tool_defs_dir.is_dir():
            raise FileNotFoundError(f"Tool definitions directory not found: {tool_defs_dir}")
        dir_tools = get_tool_dirs(tool_defs_dir)
        logger.info(f"Found {len(dir_tools)} tool definitions in {tool_defs_dir}.")
        # Pass the KEYS of the whitelist dict for filtering env tools
        env_tools = get_executables_from_env(set(whitelist.keys()), dir_tools)
        logger.info(f"Found {len(env_tools)} relevant executables in environment after filtering.")
    except FileNotFoundError as e:
        logger.error(str(e))
        raise ReconciliationError(str(e)) from e
    except Exception as e:
        msg = f"Unexpected error during environment or directory scan: {e}"
        logger.error(msg, exc_info=True)
        raise ReconciliationError(msg) from e

    # 3. Reconcile
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
    logger.info("Tool reconciliation logic complete.")

    # 4. Analyze Results & Collect Messages
    managed_tools_set = {  # Derive top-level managed tools from whitelist
        tool for tool, node in whitelist.items() if node.get("_explicit") or node.get("_all")
    }

    # 4. Perform Reconciliation
    try:
        reconciliation_results: Dict[str, ToolStatus] = reconcile_tools(
            discovered_env_tools=env_tools,
            discovered_tools_dir_tools=dir_tools,
            whitelist=whitelist,
            blacklist=blacklist,
        )
    except ReconciliationError as e:
        msg = f"Reconciliation failed: {e}"
        logger.error(msg)
        raise ReconciliationError(msg) from e

    # 5. Analyze Results & Collect Messages
    managed_tools_for_processing = set()
    for tool, status in reconciliation_results.items():
        # Handle hierarchy - TODO: Implement tool:subcommand parsing if needed

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
            # Note: Orphans are warnings, not errors blocking processing
        elif (
            status == ToolStatus.MANAGED_OK
            or status == ToolStatus.MANAGED_MISSING_ENV
            or status == ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR
        ):
            managed_tools_for_processing.add(tool)
            # Optionally log info about managed tools
            # logger.debug(f"Managed tool identified: {tool} (Status: {status.name})")
        # else: # Handle any unexpected statuses
        #    logger.warning(f"Unexpected reconciliation status for {tool}: {status.name}")

    logger.info(f"Identified {len(managed_tools_for_processing)} tools considered effectively managed.")

    # Return results including error status and the parsed blacklist
    return (
        reconciliation_results,
        managed_tools_for_processing,
        whitelist,
        blacklist,
        error_messages,
        warning_messages,
        errors_found,
    )


@click.command("reconcile")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output reconciliation status in JSON format.",
)
@click.pass_context
def reconcile(ctx: click.Context, output_json: bool) -> None:
    """Compares config, environment, and tool definitions to report discrepancies."""
    config = ctx.obj["config"]
    project_root = ctx.obj.get("project_root")
    log.info("Starting tool reconciliation command...")
    exit_code = 0

    if not project_root:
        log.error("Project root could not be determined. Cannot perform reconciliation.")
        ctx.exit(1)

    try:
        # Receive the parsed blacklist dict here
        results, managed, parsed_whitelist, parsed_blacklist, errors, warnings, has_errors = (
            _perform_reconciliation_logic(project_root_dir=project_root, config_data=config)
        )

        if output_json:
            # Prepare JSON output
            output_data = {
                "status": "ERROR" if has_errors else ("WARNING" if warnings else "OK"),
                "summary": {
                    "managed_tools_count": len(managed),
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                },
                "errors": errors,
                "warnings": warnings,
                "details": {tool: status.name for tool, status in results.items()},
                "managed_tools": sorted(list(managed)),
                # Convert parsed blacklist back to list format for JSON output if needed, or output the dict?
                # Let's output the dict for clarity, matching the internal state.
                "whitelist": {k: sorted(list(v)) for k, v in parsed_whitelist.items()},  # Sort subcommands
                "blacklist": {k: sorted(list(v)) for k, v in parsed_blacklist.items()},  # Sort subcommands
            }
            print(json_lib.dumps(output_data, indent=2))
        else:
            # Prepare Text output
            print("--- Tool Reconciliation Report ---")
            if not errors and not warnings:
                print("Status: OK")
                print(f"All checks passed. {len(managed)} managed tools identified.")
            else:
                print(f"Status: {'ERROR' if has_errors else 'WARNING'}")
                if errors:
                    print(f"\nErrors ({len(errors)}):")
                    for msg in errors:
                        print(f"- {msg}")
                if warnings:
                    print(f"\nWarnings ({len(warnings)}):")
                    for msg in warnings:
                        print(f"- {msg}")

            print(f"\nSummary: Managed Tools: {len(managed)}, Errors: {len(errors)}, Warnings: {len(warnings)}")
            # Optionally print detailed status for all tools if verbosity is high
            # if ctx.obj["verbosity"] > 1:
            #    print("\nDetailed Status:")
            #    for tool, status in sorted(results.items()):
            #        print(f"- {tool}: {status.name}")

            _print_reconciliation_summary(results, warnings, errors, parsed_whitelist, parsed_blacklist)

        if has_errors:
            exit_code = 1  # Exit with error if critical issues found
        elif warnings:
            exit_code = 0  # Exit with success even if only warnings (for now)

    except ReconciliationError as e:
        log.error(f"Reconciliation failed: {e}")
        exit_code = 2
    except Exception as e:
        log.exception("An unexpected error occurred during the reconcile command.")
        exit_code = 3

    ctx.exit(exit_code)


def _print_reconciliation_summary(
    results: Dict[str, ToolStatus],
    warnings: List[str],
    errors: List[str],
    whitelist: ParsedHierarchy,  # Need parsed lists for detailed checks
    blacklist: ParsedHierarchy,
) -> None:
    """Prints a formatted summary of the reconciliation results."""
    log.info("--- Tool Reconciliation Summary ---")

    status_groups: Dict[ToolStatus, List[str]] = {status: [] for status in ToolStatus}
    for tool, status in sorted(results.items()):
        status_groups[status].append(tool)

    if status_groups[ToolStatus.MANAGED_OK]:
        log.info("Managed & OK:", tools=status_groups[ToolStatus.MANAGED_OK])
    if status_groups[ToolStatus.MANAGED_MISSING_ENV]:
        log.warning(
            "Managed but MISSING from environment (install required?):",
            tools=status_groups[ToolStatus.MANAGED_MISSING_ENV],
        )
    if status_groups[ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR]:
        log.warning(
            "Whitelisted & in env, but MISSING baseline definition (run 'zlt tools sync'?):",
            tools=status_groups[ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR],
        )
    if status_groups[ToolStatus.BLACKLISTED_IN_ENV]:
        log.warning("Blacklisted but FOUND in environment:", tools=status_groups[ToolStatus.BLACKLISTED_IN_ENV])
    if status_groups[ToolStatus.NEW_ENV_TOOL]:
        log.info("New tools FOUND in environment (unmanaged):", tools=status_groups[ToolStatus.NEW_ENV_TOOL])
    # Add reporting for other statuses as needed, e.g., UNMANAGED_IN_TOOLS_DIR
    if status_groups[ToolStatus.UNMANAGED_IN_TOOLS_DIR]:
        log.info(
            "Unmanaged tools found ONLY in tools dir (prune candidates?):",
            tools=status_groups[ToolStatus.UNMANAGED_IN_TOOLS_DIR],
        )

    # Print specific warnings and errors
    for warning in warnings:
        log.warning(warning)
    for error in errors:
        log.error(error)

    # --- Add Conflict Check --- #
    has_conflicts = _check_for_conflicts(whitelist, blacklist)
    if has_conflicts:
        log.error(
            "Configuration Error: Found items listed in BOTH whitelist and blacklist simultaneously!",
            check="pyproject.toml",
        )

    log.info("--- End Summary ---")


def _check_for_conflicts(whitelist: ParsedHierarchy, blacklist: ParsedHierarchy, path: List[str] = None) -> bool:
    """Recursively checks for direct conflicts (same item in both lists)."""
    if path is None:
        path = []
    has_conflict = False

    # Check nodes at the current level
    current_whitelist_keys = {k for k in whitelist if not k.startswith("_")}
    current_blacklist_keys = {k for k in blacklist if not k.startswith("_")}
    common_keys = current_whitelist_keys.intersection(current_blacklist_keys)

    for key in common_keys:
        wl_node = whitelist[key]
        bl_node = blacklist[key]
        current_path_str = ":".join(path + [key])

        # Conflict if both are explicitly listed or both have :*
        wl_explicit = wl_node.get("_explicit", False)
        bl_explicit = bl_node.get("_explicit", False)
        wl_all = wl_node.get("_all", False)
        bl_all = bl_node.get("_all", False)

        if (wl_explicit and bl_explicit) or (wl_all and bl_all):
            log.error(f"Conflict detected: '{current_path_str}' found in both whitelist and blacklist.")
            has_conflict = True

        # Recursively check children
        wl_children = {k: v for k, v in wl_node.items() if not k.startswith("_") and isinstance(v, dict)}
        bl_children = {k: v for k, v in bl_node.items() if not k.startswith("_") and isinstance(v, dict)}
        if wl_children or bl_children:  # Only recurse if there are children in either
            if _check_for_conflicts(wl_children, bl_children, path + [key]):
                has_conflict = True  # Propagate conflict upwards

    return has_conflict
