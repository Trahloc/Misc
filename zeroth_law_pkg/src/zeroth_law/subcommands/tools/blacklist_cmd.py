"""Implements the 'zlt tools blacklist' subcommand."""

import click
import logging

# Import the shared utility functions
from .list_utils import modify_tool_list, list_tool_list

log = logging.getLogger(__name__)


@click.command("blacklist")
@click.option(
    "--add",
    "action_add",
    is_flag=True,
    help="Add the specified tool(s)/subcommand(s) to the blacklist.",
)
@click.option(
    "--remove",
    "action_remove",
    is_flag=True,
    help="Remove the specified tool(s)/subcommand(s) from the blacklist.",
)
@click.option(
    "--all",
    "apply_all",
    is_flag=True,
    help="When adding/removing, also apply to children/parents in the opposing list.",
)
@click.argument("tool_names", nargs=-1)
@click.pass_context
def blacklist(
    ctx: click.Context, action_add: bool, action_remove: bool, apply_all: bool, tool_names: tuple[str, ...]
) -> None:
    """Manage or list the managed tools blacklist in pyproject.toml.

    If neither --add nor --remove is specified, lists the current blacklist.
    """
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined. Cannot manage blacklist.")
        ctx.exit(1)

    if action_add and action_remove:
        log.error("Options --add and --remove are mutually exclusive.")
        ctx.exit(1)

    if (action_add or action_remove) and not tool_names:
        log.error("Tool name(s) must be provided when using --add or --remove.")
        ctx.exit(1)

    if not action_add and not action_remove:
        # Default action: List the current blacklist
        if tool_names:
            log.warning("Tool names provided without --add or --remove will be ignored.")
        current_blacklist = list_tool_list(project_root, "blacklist")
        if not current_blacklist:
            print("Blacklist is currently empty.")
        else:
            print("Current Blacklist:")
            for item in current_blacklist:
                print(f"- {item}")
        ctx.exit(0)

    # Determine action
    action = "add" if action_add else "remove"

    log.info(f"Attempting to {action} blacklist: {tool_names} (All: {apply_all})")
    try:
        modified = modify_tool_list(project_root, tool_names, "blacklist", action, apply_all)
        if modified:
            log.info("Blacklist modification successful.")
        else:
            log.info("No changes were made to the blacklist.")
    except Exception as e:
        log.error(
            f"Failed to modify blacklist: {e}", exc_info=ctx.obj.get("verbosity", 0) > 1
        )  # Show traceback if verbose
        ctx.exit(1)
