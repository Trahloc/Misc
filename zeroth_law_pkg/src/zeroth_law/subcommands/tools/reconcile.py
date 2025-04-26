# FILE: src/zeroth_law/subcommands/tools/reconcile.py
"""Implements the 'zlt tools reconcile' subcommand."""

import click
import logging
import json as json_lib  # Alias to avoid conflict with option name
from pathlib import Path
from typing import Any, Dict, Set, Tuple

# Adjust imports - assuming these utils remain in dev_scripts for now
# TODO: Move these utilities to a more central location (e.g., common or tools_lib)
# from ...dev_scripts.config_reader import load_tool_lists_from_toml
# from ...dev_scripts.environment_scanner import get_executables_from_env
# from ...dev_scripts.tool_reconciler import ToolStatus, reconcile_tools
# from ...dev_scripts.tools_dir_scanner import get_tool_dirs

# --- Updated imports from lib/tooling --- #
# from ...dev_scripts.config_reader import load_tool_lists_from_toml # No longer needed, reads from ctx
from ...lib.tooling.environment_scanner import get_executables_from_env
from ...lib.tooling.tool_reconciler import ToolStatus, reconcile_tools
from ...lib.tooling.tools_dir_scanner import get_tool_dirs

log = logging.getLogger(__name__)


class ReconciliationError(Exception):
    """Custom exception for errors during tool reconciliation (used internally)."""

    pass


def _perform_reconciliation_logic(
    project_root_dir: Path,
    config_data: dict,  # Pass loaded config data
) -> Tuple[Dict[str, ToolStatus], Set[str], Set[str], list[str]]:
    """Internal logic, adapted from dev_scripts/reconciliation_logic.py."""
    logger = log  # Use module logger

    # <<<--- REMOVE DEBUG PRINT HERE --->>>
    # logger.warning(f"DEBUG _perform_reconciliation_logic: Received config_data = {config_data}")
    # <<<--- END REMOVE DEBUG PRINT --->>>

    logger.info("Performing tool discovery and reconciliation logic...")
    errors_found = False
    error_messages = []
    warning_messages = []

    tool_defs_dir = project_root_dir / "src" / "zeroth_law" / "tools"

    # 1. Read Config (adapted to use pre-loaded config_data)
    try:
        # Extract lists directly from the loaded config object
        managed_tools_config = config_data.get("managed-tools", {})  # Get directly from config_data
        whitelist = set(managed_tools_config.get("whitelist", []))
        blacklist = set(managed_tools_config.get("blacklist", []))
        logger.info(f"Whitelist: {whitelist}, Blacklist: {blacklist}")
    except Exception as e:
        msg = f"Failed to extract whitelist/blacklist from loaded config data: {e}"
        logger.error(msg)
        raise ReconciliationError(msg) from e

    # 2. Scan Environment & Tool Defs Dir
    try:
        if not tool_defs_dir.is_dir():
            raise FileNotFoundError(f"Tool definitions directory not found: {tool_defs_dir}")
        dir_tools = get_tool_dirs(tool_defs_dir)
        logger.info(f"Found {len(dir_tools)} tool definitions in {tool_defs_dir}.")
        env_tools = get_executables_from_env(whitelist, dir_tools)  # Pass whitelist for filtering
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
    managed_tools_for_processing = set()
    for tool, status in reconciliation_results.items():
        # Handle hierarchy - TODO: Implement tool:subcommand parsing if needed

        if status == ToolStatus.ERROR_BLACKLISTED_IN_TOOLS_DIR:
            msg = (
                f"ERROR: Tool '{tool}' has directory in tools/ but is BLACKLISTED. "
                f"Remove directory: {tool_defs_dir.relative_to(project_root_dir) / tool}"
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
                f"Run 'zlt tools add-whitelist {tool}', 'zlt tools add-blacklist {tool}', or remove directory."
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

    # Return results including error status
    return (
        reconciliation_results,
        managed_tools_for_processing,
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
        results, managed, blacklist, errors, warnings, has_errors = _perform_reconciliation_logic(
            project_root_dir=project_root, config_data=config
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
                "blacklist": sorted(list(blacklist)),
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
