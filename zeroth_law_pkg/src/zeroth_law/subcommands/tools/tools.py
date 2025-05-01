"""Main command group for 'zlt tools' subcommands."""

import click
import structlog
from pathlib import Path

log = structlog.get_logger()

# Propagate CONTEXT_SETTINGS potentially?
# from ...cli import CONTEXT_SETTINGS


@click.group("tools")
@click.pass_context
def tools_group(ctx: click.Context) -> None:
    """Group for managing tool definitions, baselines, and configurations."""
    # This group function itself doesn't do anything but acts as an entry point
    # for the subcommands we will add later (reconcile, sync, etc.).
    # We don't strictly NEED to do anything with ctx here, but passing it
    # ensures it propagates down to subcommands that use @pass_context.
    log.debug("Entering tools command group", ctx_obj_keys=list(ctx.obj.keys()) if ctx.obj else [])
    pass


# --- Subcommand Registration --- #
# Subcommands like reconcile, sync, add-whitelist will be imported and added here

# Import and add the reconcile command
from .reconcile import reconcile

# Import whitelist/blacklist commands
# from .whitelist import add_whitelist, remove_whitelist # Removed old imports
# from .blacklist import add_blacklist, remove_blacklist # Removed old imports
from .whitelist_cmd import whitelist  # Import new command
from .blacklist_cmd import blacklist  # Import new command

# Import and add sync command
from .sync import sync

# Import the definition group from its new location
from .definition import definition_group

tools_group.add_command(reconcile)
# tools_group.add_command(add_whitelist) # Removed old registration
# tools_group.add_command(remove_whitelist) # Removed old registration
# tools_group.add_command(add_blacklist) # Removed old registration
# tools_group.add_command(remove_blacklist) # Removed old registration
tools_group.add_command(whitelist)  # Add new command
tools_group.add_command(blacklist)  # Add new command
tools_group.add_command(sync)

# Register the definition group under tools
tools_group.add_command(definition_group)

# Example (will be added later):
# from .sync import sync
# tools_group.add_command(sync)
