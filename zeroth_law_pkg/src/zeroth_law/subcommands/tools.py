"""Main command group for 'zlt tools' subcommands."""

import click
import structlog
from pathlib import Path
import sys  # Add sys import
from typing import Optional
import os  # Add import needed for default

# Import the function to find the project root
from ..common.path_utils import find_project_root, ZLFProjectRootNotFoundError

log = structlog.get_logger()  # Restore logger

# Propagate CONTEXT_SETTINGS potentially?
# from ...cli import CONTEXT_SETTINGS


@click.group("tools")
@click.option(
    "--max-workers",
    type=int,
    default=None,  # Default handled later if None
    help="Maximum number of parallel workers for baseline generation.",
    show_default="CPU count",  # Indicate dynamic default
)
@click.pass_context
def tools_group(ctx: click.Context, max_workers: Optional[int]) -> None:
    """Group for managing tool definitions, baselines, and environment synchronization."""
    log.debug("Entering tools command group", ctx_obj_keys=list(ctx.obj.keys()))  # Restore log call
    # print(f"DEBUG [tools_group]: Entering tools command group. ctx_obj_keys={list(ctx.obj.keys())}", file=sys.stderr)
    # sys.stderr.flush()
    # Ensure project root is available, needed for most tool operations
    project_root = ctx.obj.get("PROJECT_ROOT")
    if not project_root:
        log.error("Project root not found in context, cannot proceed with tools commands.")  # Restore log call
        # print("ERROR [tools_group]: Project root not found in context, cannot proceed.", file=sys.stderr)
        # sys.stderr.flush()
        ctx.exit(1)

    # Calculate and store derived paths if needed by subcommands
    zlt_root = project_root / "src" / "zeroth_law"
    tools_dir = zlt_root / "tools"
    zlt_capabilities_path = zlt_root / "schemas" / "zlt_capabilities.json"
    zlt_options_definitions_path = zlt_root / "zlt_options_definitions.json"

    ctx.obj["project_root"] = project_root  # Use consistent key
    ctx.obj["zlt_root"] = zlt_root
    ctx.obj["tools_dir"] = tools_dir
    ctx.obj["zlt_capabilities_path"] = zlt_capabilities_path
    ctx.obj["zlt_options_definitions_path"] = zlt_options_definitions_path

    # Store max_workers in context, defaulting if not provided
    actual_max_workers = max_workers if max_workers is not None else os.cpu_count()
    ctx.obj["MAX_WORKERS"] = actual_max_workers

    log.debug("Added derived paths and max_workers to context", obj_keys=list(ctx.obj.keys()))  # Restore log call
    # print(f"DEBUG [tools_group]: Added derived paths to context. obj_keys={list(ctx.obj.keys())}", file=sys.stderr)
    # sys.stderr.flush()


# --- Subcommand Registration --- #
# Subcommands like reconcile, sync, add-whitelist will be imported and added here

# Import commands/groups from the _tools directory

# Import individual tool commands/groups from the _tools directory
from ._tools.sync import sync as sync_command
from ._tools.reconcile import reconcile as reconcile_command
from ._tools.definition import definition_group
from ._tools.whitelist import whitelist as whitelist_group
from ._tools.blacklist import blacklist as blacklist_group

tools_group.add_command(sync_command)
tools_group.add_command(reconcile_command)
tools_group.add_command(definition_group)
tools_group.add_command(whitelist_group)
tools_group.add_command(blacklist_group)

# Example (will be added later):
# from .sync import sync
# tools_group.add_command(sync)
