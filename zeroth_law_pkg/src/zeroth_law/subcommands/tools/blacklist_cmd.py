"""Implements the 'zlt tools blacklist' subcommand."""

import click
import structlog
from pathlib import Path
from typing import Tuple

# TODO: [Implement Subcommand Blacklist] Reference TODO H.14 in TODO.md - This module needs to handle parsing/writing the tool:sub1,sub2 syntax.

# Import the shared utility functions
from .list_utils import modify_tool_list, list_tool_list, print_list_changes

log = structlog.get_logger()


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
@click.option(
    "--force",
    is_flag=True,
    help="Force adding the item even if it exists in the whitelist (removes from whitelist).",
)
@click.argument("tool_names", nargs=-1)
@click.pass_context
def blacklist(
    ctx: click.Context,
    action_add: bool,
    action_remove: bool,
    apply_all: bool,
    force: bool,
    tool_names: tuple[str, ...],
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
    use_force = force

    log.info(f"Attempting to {action} blacklist: {tool_names} (All: {apply_all})")
    try:
        modified = modify_tool_list(
            project_root=project_root,
            tool_items_to_modify=tool_names,
            target_list_name="blacklist",
            action=action,
            apply_all=apply_all,
            force=use_force,
        )
        if modified:
            log.info("Blacklist modification successful.")
            # Print final list for confirmation
            final_list = list_tool_list(project_root, "blacklist")
            log.info("Current blacklist:", items=final_list if final_list else "[EMPTY]")
        else:
            log.info("Blacklist was not modified (no changes needed or conflict detected without --force).")
    except FileNotFoundError as e:
        log.error(f"Error: {e}")
        ctx.exit(1)
    except ValueError as e:
        log.error(f"Error processing configuration: {e}")
        ctx.exit(1)
    except Exception as e:
        log.exception("An unexpected error occurred.")
        ctx.exit(1)
