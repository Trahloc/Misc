"""Helper function for the 'zlt tools whitelist add' command."""

# pylint: disable=R0801 # Boilerplate similarity

import click
import structlog
from pathlib import Path
from typing import Tuple

# Adjust import path for list_utils
from ..list_utils import modify_tool_list

log = structlog.get_logger()


@click.command("add")  # Keep the command name
@click.argument("tool_items", nargs=-1, required=True)
@click.option(
    "--all",
    "apply_all",
    is_flag=True,
    help="Apply the action recursively to all subcommands (e.g., 'tool:*').",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force add: remove conflicting entry from blacklist if present.",
)
@click.pass_context
def add_whitelist(ctx: click.Context, tool_items: Tuple[str, ...], apply_all: bool, force: bool):
    """Add tools or subcommands to the whitelist."""
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined.")
        ctx.exit(1)

    log.info(
        f"Adding to whitelist: {tool_items} (All: {apply_all}, Force: {force})",
        items=tool_items,
        all=apply_all,
        force=force,
    )
    modified = modify_tool_list(
        project_root=project_root,
        tool_items_to_modify=tool_items,
        target_list_name="whitelist",
        action="add",
        apply_all=apply_all,
        force=force,
    )
    if modified:
        log.info("Whitelist successfully modified.")
    else:
        log.info("Whitelist not modified (item might already exist or conflict). Check logs.")
