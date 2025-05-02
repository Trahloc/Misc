"""Commands for managing option mappings in tool definitions."""

import click
import structlog
from pathlib import Path

# Import shared helpers from the same directory
from ._paths import _get_tool_def_path
from ._io import _load_json_file, _write_json_file, _load_tool_definition_or_abort

log = structlog.get_logger()

# Assume paths are passed via context
# ZLT_OPTIONS_DEFINITIONS_PATH = Path("src/zeroth_law/zlt_options_definitions.json") # Placeholder


@click.command("map-option")
@click.argument("tool_id")
@click.argument("tool_option_name")
@click.argument("zlt_option_name")
@click.pass_context  # Get paths from context
def map_option(ctx: click.Context, tool_id: str, tool_option_name: str, zlt_option_name: str):
    """Maps a tool's option/argument TOOL_OPTION_NAME to a canonical ZLT option ZLT_OPTION_NAME for tool TOOL_ID."""
    log.info("Attempting to map option...", tool=tool_id, tool_option=tool_option_name, zlt_option=zlt_option_name)
    zlt_options_path = ctx.obj.get("zlt_options_definitions_path")
    if not zlt_options_path:
        click.echo("Error: Could not determine required paths (zlt_options_definitions_path) from context.", err=True)
        raise click.Abort()

    # 1. Load ZLT options definition for validation
    valid_zlt_options = _load_json_file(zlt_options_path)
    if valid_zlt_options is None:
        click.echo(f"Error: Could not load ZLT option definitions from {zlt_options_path}", err=True)
        raise click.Abort()
    if zlt_option_name not in valid_zlt_options:
        click.echo(
            f"Error: ZLT option '{zlt_option_name}' is not defined in {zlt_options_path}.",
            err=True,
        )
        click.echo(f"Valid ZLT options are: {', '.join(valid_zlt_options.keys())}")
        raise click.Abort()

    # 2. Load target tool definition using helper
    tool_data = _load_tool_definition_or_abort(ctx, tool_id)
    tools_dir = ctx.obj.get("tools_dir")
    tool_json_path = _get_tool_def_path(tool_id, tools_dir) if tools_dir else Path(f"UNKNOWN_PATH/{tool_id}.json")

    # 3. Find the tool option (in 'options' or 'arguments')
    option_found = False
    target_option_dict = None
    for key in ["options", "arguments"]:
        if key in tool_data and isinstance(tool_data[key], list):
            for option_dict in tool_data[key]:
                if isinstance(option_dict, dict) and tool_option_name in option_dict.get("cli_names", []):
                    option_found = True
                    target_option_dict = option_dict
                    break
            if option_found:
                break

    if not option_found or target_option_dict is None:
        click.echo(
            f"Error: Tool option/argument '{tool_option_name}' not found in definition {tool_json_path}", err=True
        )
        raise click.Abort()

    # 4. Add/Update the mapping
    option_map = target_option_dict.setdefault("maps_to_zlt", {})
    if not isinstance(option_map, dict):
        click.echo(
            f"Error: 'maps_to_zlt' for option '{tool_option_name}' in {tool_json_path} is not a dictionary.", err=True
        )
        raise click.Abort()

    # Check if already mapped to something else
    current_mapping = option_map.get("option_name")
    if current_mapping and current_mapping != zlt_option_name:
        click.echo(
            f"Warning: Tool option '{tool_option_name}' was previously mapped to '{current_mapping}'. Overwriting with '{zlt_option_name}'."
        )

    # TODO: Add transformation logic if needed later
    option_map["option_name"] = zlt_option_name

    # 5. Write updated data back
    if _write_json_file(tool_json_path, tool_data):
        click.echo(f"Successfully mapped '{tool_option_name}' to ZLT option '{zlt_option_name}' for tool '{tool_id}'.")
        log.info("Option mapped successfully.", tool=tool_id, tool_option=tool_option_name, zlt_option=zlt_option_name)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error("Failed to write updated definition.", tool=tool_id, path=str(tool_json_path))
        raise click.Abort()


@click.command("unmap-option")
@click.argument("tool_id")
@click.argument("tool_option_name")
@click.pass_context  # Get paths from context
def unmap_option(ctx: click.Context, tool_id: str, tool_option_name: str):
    """Removes any ZLT option mapping for a tool's option/argument TOOL_OPTION_NAME."""
    log.info("Attempting to unmap option...", tool=tool_id, tool_option=tool_option_name)
    tool_data = _load_tool_definition_or_abort(ctx, tool_id)
    tools_dir = ctx.obj.get("tools_dir")
    tool_json_path = _get_tool_def_path(tool_id, tools_dir) if tools_dir else Path(f"UNKNOWN_PATH/{tool_id}.json")

    # 2. Find the tool option and remove mapping if it exists
    option_found = False
    mapping_removed = False
    for key in ["options", "arguments"]:
        if key in tool_data and isinstance(tool_data[key], list):
            for option_dict in tool_data[key]:
                if isinstance(option_dict, dict) and tool_option_name in option_dict.get("cli_names", []):
                    option_found = True
                    if "maps_to_zlt" in option_dict:
                        del option_dict["maps_to_zlt"]
                        mapping_removed = True
                    break
            if option_found:
                break

    if not option_found:
        click.echo(
            f"Error: Tool option/argument '{tool_option_name}' not found in definition {tool_json_path}", err=True
        )
        raise click.Abort()

    if not mapping_removed:
        click.echo(f"Info: Tool option '{tool_option_name}' for tool '{tool_id}' had no ZLT mapping. No changes made.")
        return  # Idempotent success

    # 3. Write updated data back
    if _write_json_file(tool_json_path, tool_data):
        click.echo(f"Successfully unmapped ZLT option for '{tool_option_name}' for tool '{tool_id}'.")
        log.info("Option unmapped successfully.", tool=tool_id, tool_option=tool_option_name)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error("Failed to write updated definition.", tool=tool_id, path=str(tool_json_path))
        raise click.Abort()
