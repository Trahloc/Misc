"""Implements the 'zlt tools whitelist' subcommand."""

import click
import structlog
from pathlib import Path
import tomlkit
from typing import Tuple

# TODO: [Implement Subcommand Blacklist] Reference TODO H.14 in TODO.md - This module needs to handle parsing/writing the tool:sub1,sub2 syntax.

# Import the shared utility functions
from .list_utils import modify_tool_list, list_tool_list, print_list_changes

log = structlog.get_logger()


@click.command("whitelist")
@click.option(
    "--add",
    "action_add",
    is_flag=True,
    help="Add the specified tool(s)/subcommand(s) to the whitelist.",
)
@click.option(
    "--remove",
    "action_remove",
    is_flag=True,
    help="Remove the specified tool(s)/subcommand(s) from the whitelist.",
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
    help="Force adding the item even if it exists in the blacklist (removes from blacklist).",
)
@click.argument("tool_names", nargs=-1)
@click.pass_context
def whitelist(
    ctx: click.Context,
    action_add: bool,
    action_remove: bool,
    apply_all: bool,
    force: bool,
    tool_names: tuple[str, ...],
) -> None:
    """Manage or list the managed tools whitelist in pyproject.toml.

    If neither --add nor --remove is specified, lists the current whitelist.
    """
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined. Cannot manage whitelist.")
        ctx.exit(1)

    if action_add and action_remove:
        log.error("Options --add and --remove are mutually exclusive.")
        ctx.exit(1)

    if (action_add or action_remove) and not tool_names:
        log.error("Tool name(s) must be provided when using --add or --remove.")
        ctx.exit(1)

    if not action_add and not action_remove:
        # Default action: List the current whitelist
        if tool_names:
            log.warning("Tool names provided without --add or --remove will be ignored.")
        current_whitelist = list_tool_list(project_root, "whitelist")
        if not current_whitelist:
            print("Whitelist is currently empty.")
        else:
            print("Current Whitelist:")
            for item in current_whitelist:
                print(f"- {item}")
        ctx.exit(0)

    # Determine action
    action = "add" if action_add else "remove"
    use_force = force

    log.info(f"Attempting to {action} whitelist: {tool_names} (All: {apply_all})")
    try:
        modified = modify_tool_list(
            project_root=project_root,
            tool_items_to_modify=tool_names,
            target_list_name="whitelist",
            action=action,
            apply_all=apply_all,
            force=use_force,
        )
        if modified:
            log.info("Whitelist modification successful.")
            # Print final list for confirmation
            final_list = list_tool_list(project_root, "whitelist")
            log.info("Current whitelist:", items=final_list if final_list else "[EMPTY]")
        else:
            log.info("Whitelist was not modified (no changes needed or conflict detected without --force).")
    except FileNotFoundError as e:
        log.error(f"Error: {e}")
        ctx.exit(1)
    except ValueError as e:
        log.error(f"Error processing configuration: {e}")
        ctx.exit(1)
    except Exception as e:
        log.exception("An unexpected error occurred.")
        ctx.exit(1)
