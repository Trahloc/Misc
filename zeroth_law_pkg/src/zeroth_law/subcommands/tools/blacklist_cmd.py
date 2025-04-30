"""Implements the 'zlt tools blacklist' subcommand."""

import click
import structlog
from pathlib import Path
from typing import Tuple

# TODO: [Implement Subcommand Blacklist] Reference TODO H.14 in TODO.md - This module needs to handle parsing/writing the tool:sub1,sub2 syntax.

# Import the shared utility functions
from .list_utils import modify_tool_list, list_tool_list

log = structlog.get_logger()


@click.group("blacklist")
def blacklist():
    """Manage the tool blacklist in pyproject.toml."""
    pass


@blacklist.command("add")
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
    help="Force add: remove conflicting entry from whitelist if present.",
)
@click.pass_context
def add_blacklist(ctx: click.Context, tool_items: Tuple[str, ...], apply_all: bool, force: bool):
    """Add tools or subcommands to the blacklist."""
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined.")
        ctx.exit(1)

    log.info(
        f"Adding to blacklist: {tool_items} (All: {apply_all}, Force: {force})",
        items=tool_items,
        all=apply_all,
        force=force,
    )
    # initial_list = list_tool_list(project_root, "blacklist")
    modified = modify_tool_list(
        project_root=project_root,
        tool_items_to_modify=tool_items,
        target_list_name="blacklist",
        action="add",
        apply_all=apply_all,
        force=force,
    )
    if modified:
        # final_list = list_tool_list(project_root, "blacklist")
        # print_list_changes("Blacklist", initial_list, final_list) # REMOVED CALL
        log.info("Blacklist successfully modified.")
    else:
        log.info("Blacklist not modified (item might already exist or conflict). Check logs.")


@blacklist.command("remove")
@click.argument("tool_items", nargs=-1, required=True)
@click.option(
    "--all",
    "apply_all",
    is_flag=True,
    help="Apply the action recursively to all subcommands (e.g., 'tool:*').",
)
@click.pass_context
def remove_blacklist(ctx: click.Context, tool_items: Tuple[str, ...], apply_all: bool):
    """Remove tools or subcommands from the blacklist."""
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined.")
        ctx.exit(1)

    log.info(f"Removing from blacklist: {tool_items} (All: {apply_all})", items=tool_items, all=apply_all)
    # initial_list = list_tool_list(project_root, "blacklist")
    modified = modify_tool_list(
        project_root=project_root,
        tool_items_to_modify=tool_items,
        target_list_name="blacklist",
        action="remove",
        apply_all=apply_all,
        force=False,  # Force not applicable for remove
    )
    if modified:
        # final_list = list_tool_list(project_root, "blacklist")
        # print_list_changes("Blacklist", initial_list, final_list) # REMOVED CALL
        log.info("Blacklist successfully modified.")
    else:
        log.info("Blacklist not modified (item might not exist). Check logs.")
