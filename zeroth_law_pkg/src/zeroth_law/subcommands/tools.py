"""Main command group for 'zlt tools' subcommands."""

import click
import structlog
from pathlib import Path

# Import the function to find the project root
from ..common.path_utils import find_project_root, ZLFProjectRootNotFoundError

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

    # --- Add necessary paths to context for subcommands like 'definition' ---
    # Ensure ctx.obj exists
    ctx.ensure_object(dict)

    project_root = ctx.obj.get("project_root")
    if not project_root:
        try:
            # Attempt to find project root if not already in context
            project_root = find_project_root(start_path=Path.cwd())
            ctx.obj["project_root"] = project_root
            log.debug("Project root determined within tools_group", path=str(project_root))
        except ZLFProjectRootNotFoundError:
            log.warning("Project root could not be determined within tools_group. Some subcommands may fail.")
            # Don't fail here, let subcommands handle missing context if they need it.
            project_root = None  # Explicitly set to None if not found

    if project_root:
        # Derive other paths based on project_root
        zlt_root = project_root / "src" / "zeroth_law"
        ctx.obj["zlt_root"] = zlt_root  # Store zlt_root as well
        ctx.obj["tools_dir"] = zlt_root / "tools"
        ctx.obj["zlt_capabilities_path"] = zlt_root / "zlt_capabilities.json"
        ctx.obj["zlt_options_definitions_path"] = zlt_root / "zlt_options_definitions.json"
        log.debug("Added derived paths to context", obj_keys=list(ctx.obj.keys()))
    else:
        # Set paths to None or handle differently if root is required
        ctx.obj["zlt_root"] = None
        ctx.obj["tools_dir"] = None
        ctx.obj["zlt_capabilities_path"] = None
        ctx.obj["zlt_options_definitions_path"] = None
        log.warning("Project root not found, cannot set derived paths in context for tools group.")

    pass


# --- Subcommand Registration --- #
# Subcommands like reconcile, sync, add-whitelist will be imported and added here

# Import commands/groups from the _tools directory

# Import and add the reconcile command
from ._tools.reconcile import reconcile

# Import whitelist/blacklist command groups
from ._tools.whitelist import whitelist
from ._tools.blacklist import blacklist

# Import and add sync command
from ._tools.sync import sync

# Import the definition group
from ._tools.definition import definition_group

tools_group.add_command(reconcile)
tools_group.add_command(whitelist)
tools_group.add_command(blacklist)
tools_group.add_command(sync)
tools_group.add_command(definition_group)

# Example (will be added later):
# from .sync import sync
# tools_group.add_command(sync)
