"""Helper function for the 'zlt tools whitelist remove' command."""

# pylint: disable=R0801 # Boilerplate similarity

import click
import structlog
from pathlib import Path
from typing import Tuple

# Adjust import path for list_utils
from ..list_utils import modify_tool_list

log = structlog.get_logger()


@click.command("remove")  # Keep the command name
@click.argument("tool_items", nargs=-1, required=True)
@click.option(
    "--all",
    "apply_all",
    is_flag=True,
    help="Apply the action recursively to all subcommands (e.g., 'tool:*').",
)
@click.pass_context
def remove_whitelist(ctx: click.Context, tool_items: Tuple[str, ...], apply_all: bool):
    """Remove tools or subcommands from the whitelist."""
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined.")
        ctx.exit(1)

    log.info(f"Removing from whitelist: {tool_items} (All: {apply_all})", items=tool_items, all=apply_all)
    modified = modify_tool_list(
        project_root=project_root,
        tool_items_to_modify=tool_items,
        target_list_name="whitelist",
        action="remove",
        apply_all=apply_all,
        force=False,  # Force not applicable for remove
    )
    if modified:
        log.info("Whitelist successfully modified.")
    else:
        log.info("Whitelist not modified (item might not exist). Check logs.")
