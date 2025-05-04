# FILE: src/zeroth_law/subcommands/_tools/reconcile.py
"""Facade for the 'zlt tools reconcile' subcommand."""

import click
import structlog
import json as json_lib  # Alias to avoid conflict with option name
from pathlib import Path
import sys

# Import the core logic helpers
from ._reconcile._logic import (
    _perform_reconciliation_logic,
    _print_reconciliation_summary,
    ReconciliationError,  # Keep exception import if needed by facade
    ToolStatus,  # Import Enum if needed by facade (unlikely)
)

log = structlog.get_logger()


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
    log.debug("Entering 'tools reconcile' command facade.")
    # Correctly retrieve context data using uppercase keys
    config = ctx.obj.get("CONFIG_DATA")
    project_root = ctx.obj.get("PROJECT_ROOT")

    if not project_root:
        log.error("Project root not found in context. Cannot perform reconciliation.")
        ctx.exit(1)
    # Check if config is None OR an empty dictionary (if load_config failed gracefully)
    if not config:
        log.error("Configuration data not found or empty in context. Cannot perform reconciliation.")
        ctx.exit(1)

    exit_code = 0
    try:
        # Run the core logic
        log.debug("Calling _perform_reconciliation_logic...")
        results, managed, parsed_whitelist, parsed_blacklist, errors, warnings, has_errors = (
            _perform_reconciliation_logic(project_root_dir=project_root, config_data=config)
        )
        log.debug("Returned from _perform_reconciliation_logic.")

        # Handle output based on flags
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
            }
            print(json_lib.dumps(output_data, indent=2))
        else:
            # Print human-readable summary
            # Note: _print_reconciliation_summary likely uses click.echo/secho, not our prints
            _print_reconciliation_summary(
                results=results,
                warnings=warnings,
                errors=errors,
                whitelist=parsed_whitelist,
                blacklist=parsed_blacklist,
            )

        # Set exit code based on errors
        if has_errors:
            exit_code = 1
        elif warnings:
            pass

    except ReconciliationError as e:
        log.error(f"Reconciliation failed: {e}")
        exit_code = 1
    except Exception as e:
        log.exception("An unexpected error occurred during reconciliation.")
        exit_code = 2

    ctx.exit(exit_code)
