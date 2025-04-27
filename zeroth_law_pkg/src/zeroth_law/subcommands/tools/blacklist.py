"""Implements the 'zlt tools add-blacklist' and 'remove-blacklist' subcommands."""

import click
import logging
from pathlib import Path

# Import the shared helper (or define locally if preferred)
# Assuming it will be moved to a shared location later
from .whitelist import _modify_tool_list

log = logging.getLogger(__name__)


@click.command("add-blacklist")
@click.argument("tool_names", nargs=-1, required=True)
@click.option(
    "--all",
    "apply_all",
    is_flag=True,
    help="Apply action to the tool and all its subcommands (removes from whitelist).",
)
@click.pass_context
def add_blacklist(ctx: click.Context, tool_names: tuple[str, ...], apply_all: bool) -> None:
    """Adds one or more tools/subcommands to the managed tools blacklist."""
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined. Cannot modify configuration.")
        ctx.exit(1)

    log.info(f"Attempting to add to blacklist: {tool_names} (All: {apply_all})")
    try:
        _modify_tool_list(project_root, tool_names, "blacklist", "add", apply_all)
        log.info("Blacklist modification successful (logic pending implementation).")
    except Exception as e:
        log.error(f"Failed to modify blacklist: {e}", exc_info=True)
        ctx.exit(1)


@click.command("remove-blacklist")
@click.argument("tool_names", nargs=-1, required=True)
@click.option(
    "--all",
    "apply_all",
    is_flag=True,
    help="Apply action to the tool and all its subcommands.",
)
@click.pass_context
def remove_blacklist(ctx: click.Context, tool_names: tuple[str, ...], apply_all: bool) -> None:
    """Removes one or more tools/subcommands from the managed tools blacklist."""
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined. Cannot modify configuration.")
        ctx.exit(1)

    log.info(f"Attempting to remove from blacklist: {tool_names} (All: {apply_all})")
    try:
        _modify_tool_list(project_root, tool_names, "blacklist", "remove", apply_all)
        log.info("Blacklist removal successful (logic pending implementation).")
    except Exception as e:
        log.error(f"Failed to remove from blacklist: {e}", exc_info=True)
        ctx.exit(1)
