"""Commands for managing capabilities in tool definitions."""

import click
import structlog
from pathlib import Path

# Import shared helpers from the same directory
from ._paths import _get_tool_def_path
from ._io import _load_json_file, _write_json_file, _load_tool_definition_or_abort

log = structlog.get_logger()

# These should probably load paths from context or config, not assume globals
# ZLT_CAPABILITIES_PATH = Path("src/zeroth_law/zlt_capabilities.json") # Placeholder


@click.command("add-capability")
@click.argument("tool_id")
@click.argument("capability_name")
@click.pass_context  # Get paths from context
def add_capability(ctx: click.Context, tool_id: str, capability_name: str):
    """Adds a capability to a tool definition's metadata."""
    log.info("Attempting to add capability...", tool=tool_id, capability=capability_name)
    # Get paths from context (excluding tools_dir, handled by helper)
    zlt_capabilities_path = ctx.obj.get("zlt_capabilities_path")
    if not zlt_capabilities_path:
        click.echo(
            "Error: Could not determine required paths (zlt_capabilities_path) from context.",
            err=True,
        )
        raise click.Abort()

    # 1. Load capabilities definition for validation
    valid_capabilities = _load_json_file(zlt_capabilities_path)
    if valid_capabilities is None:
        click.echo(
            f"Error: Could not load capability definitions from {zlt_capabilities_path}",
            err=True,
        )
        raise click.Abort()
    if capability_name not in valid_capabilities:
        click.echo(
            f"Error: Capability '{capability_name}' is not a valid capability defined in {zlt_capabilities_path}.",
            err=True,
        )
        click.echo(f"Valid capabilities are: {', '.join(valid_capabilities.keys())}")
        raise click.Abort()

    # 2. Load target tool definition using helper
    tool_data = _load_tool_definition_or_abort(ctx, tool_id)
    # Get the path for logging/error messages if needed (helper doesn't return it)
    tools_dir = ctx.obj.get("tools_dir")  # Re-get tools_dir for path construction if needed
    tool_json_path = _get_tool_def_path(tool_id, tools_dir) if tools_dir else Path(f"UNKNOWN_PATH/{tool_id}.json")

    # 3. Modify data structure
    metadata = tool_data.setdefault("metadata", {})
    capabilities_list = metadata.setdefault("provides_capabilities", [])

    if not isinstance(capabilities_list, list):
        click.echo(
            f"Error: 'metadata.provides_capabilities' in {tool_json_path} is not a list.",
            err=True,
        )
        raise click.Abort()

    if capability_name in capabilities_list:
        click.echo(f"Info: Capability '{capability_name}' already exists for tool '{tool_id}'. No changes made.")
        return  # Idempotent success

    capabilities_list.append(capability_name)
    # Sort for consistency, although order isn't strictly significant
    capabilities_list.sort()

    # 4. Write updated data back
    if _write_json_file(tool_json_path, tool_data):
        click.echo(f"Successfully added capability '{capability_name}' to tool '{tool_id}' definition.")
        log.info("Capability added successfully.", tool=tool_id, capability=capability_name)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error(
            "Failed to write updated definition.",
            tool=tool_id,
            path=str(tool_json_path),
        )
        raise click.Abort()


@click.command("remove-capability")
@click.argument("tool_id")
@click.argument("capability_name")
@click.pass_context  # Get paths from context
def remove_capability(ctx: click.Context, tool_id: str, capability_name: str):
    """Removes a capability from a tool definition's metadata."""
    log.info("Attempting to remove capability...", tool=tool_id, capability=capability_name)
    # tools_dir = ctx.obj.get("tools_dir") # REMOVED
    # if not tools_dir: # REMOVED
    #     click.echo("Error: Could not determine tools_dir from context.", err=True) # REMOVED
    #     raise click.Abort() # REMOVED

    # No need to validate against capabilities file for removal

    # 1. Load target tool definition using helper
    tool_data = _load_tool_definition_or_abort(ctx, tool_id)
    # Get the path for logging/error messages if needed
    tools_dir = ctx.obj.get("tools_dir")
    tool_json_path = _get_tool_def_path(tool_id, tools_dir) if tools_dir else Path(f"UNKNOWN_PATH/{tool_id}.json")

    # 2. Modify data structure
    metadata = tool_data.get("metadata")
    if not metadata or not isinstance(metadata, dict):
        click.echo(
            f"Error: 'metadata' object missing or invalid in {tool_json_path}. Cannot remove capability.",
            err=True,
        )
        raise click.Abort()

    capabilities_list = metadata.get("provides_capabilities")
    if not isinstance(capabilities_list, list):
        # If key exists but isn't a list, or if key doesn't exist, the capability isn't there anyway.
        click.echo(
            f"Info: Capability '{capability_name}' not found for tool '{tool_id}' (or capabilities list invalid/missing). No changes made."
        )
        return  # Idempotent success

    if capability_name not in capabilities_list:
        click.echo(f"Info: Capability '{capability_name}' not found for tool '{tool_id}'. No changes made.")
        return  # Idempotent success

    try:
        capabilities_list.remove(capability_name)
        # Sort for consistency
        capabilities_list.sort()
    except ValueError:  # Should not happen due to check above, but be safe
        click.echo(
            f"Info: Capability '{capability_name}' not found for tool '{tool_id}' during removal attempt. No changes made."
        )
        return

    # 3. Write updated data back
    if _write_json_file(tool_json_path, tool_data):
        click.echo(f"Successfully removed capability '{capability_name}' from tool '{tool_id}' definition.")
        log.info("Capability removed successfully.", tool=tool_id, capability=capability_name)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error(
            "Failed to write updated definition.",
            tool=tool_id,
            path=str(tool_json_path),
        )
        raise click.Abort()
