"""Implements the 'zlt tools whitelist' subcommand."""

import click
import structlog
from pathlib import Path
import tomlkit
from typing import Tuple

# TODO: [Implement Subcommand Blacklist] Reference TODO H.14 in TODO.md - This module needs to handle parsing/writing the tool:sub1,sub2 syntax.

# Import the shared utility functions
from .list_utils import modify_tool_list, list_tool_list

log = structlog.get_logger()


@click.group("whitelist")
def whitelist():
    """Manage the tool whitelist in pyproject.toml."""
    pass


@whitelist.command("add")
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
    # initial_list = list_tool_list(project_root, "whitelist") # Get initial state
    modified = modify_tool_list(
        project_root=project_root,
        tool_items_to_modify=tool_items,
        target_list_name="whitelist",
        action="add",
        apply_all=apply_all,
        force=force,
    )
    if modified:
        # final_list = list_tool_list(project_root, "whitelist") # Get final state
        # print_list_changes("Whitelist", initial_list, final_list) # REMOVED CALL
        log.info("Whitelist successfully modified.")
    else:
        log.info("Whitelist not modified (item might already exist or conflict). Check logs.")


@whitelist.command("remove")
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
    # initial_list = list_tool_list(project_root, "whitelist") # Get initial state
    modified = modify_tool_list(
        project_root=project_root,
        tool_items_to_modify=tool_items,
        target_list_name="whitelist",
        action="remove",
        apply_all=apply_all,
        force=False,  # Force not applicable for remove
    )
    if modified:
        # final_list = list_tool_list(project_root, "whitelist") # Get final state
        # print_list_changes("Whitelist", initial_list, final_list) # REMOVED CALL
        log.info("Whitelist successfully modified.")
    else:
        log.info("Whitelist not modified (item might not exist). Check logs.")
