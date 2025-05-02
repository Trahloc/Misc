"""Commands for managing filetypes in tool definitions."""

import click
import structlog
from pathlib import Path

# Import shared helpers from the same directory
from ._paths import _get_tool_def_path
from ._io import _load_json_file, _write_json_file

log = structlog.get_logger()


@click.command("set-filetypes")
@click.argument("tool_id")
@click.argument("extensions", nargs=-1)  # Accepts one or more extensions
@click.pass_context  # Get paths from context
def set_filetypes(ctx: click.Context, tool_id: str, extensions: tuple[str]):
    """Sets (overwrites) the supported filetypes for a tool definition."""
    log.info("Attempting to set filetypes...", tool=tool_id, filetypes=list(extensions))
    tools_dir = ctx.obj.get("tools_dir")
    if not tools_dir:
        click.echo("Error: Could not determine tools_dir from context.", err=True)
        raise click.Abort()

    if not extensions:
        click.echo("Error: At least one file extension (e.g., '.py' or '*') must be provided.", err=True)
        raise click.Abort()

    # Basic validation: ensure extensions start with a dot or are "*"
    validated_extensions = []
    for ext in extensions:
        if ext == "*":
            validated_extensions.append("*")
        elif ext.startswith(".") and len(ext) > 1:
            validated_extensions.append(ext.lower())  # Store lowercase
        else:
            click.echo(
                f"Error: Invalid file extension format '{ext}'. Must start with '.' (e.g., '.py') or be '*'", err=True
            )
            raise click.Abort()

    # Remove duplicates and sort
    unique_sorted_extensions = sorted(list(set(validated_extensions)))

    # 1. Load target tool definition
    tool_json_path = _get_tool_def_path(tool_id, tools_dir)
    tool_data = _load_json_file(tool_json_path)
    if tool_data is None:
        click.echo(f"Error: Could not load tool definition for '{tool_id}' from {tool_json_path}", err=True)
        raise click.Abort()

    # 2. Modify data structure (overwrite existing)
    metadata = tool_data.setdefault("metadata", {})
    metadata["supported_filetypes"] = unique_sorted_extensions

    # 3. Write updated data back
    if _write_json_file(tool_json_path, tool_data):
        click.echo(f"Successfully set filetypes for tool '{tool_id}' definition to: {unique_sorted_extensions}")
        log.info("Filetypes set successfully.", tool=tool_id, filetypes=unique_sorted_extensions)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error("Failed to write updated definition.", tool=tool_id, path=str(tool_json_path))
        raise click.Abort()
