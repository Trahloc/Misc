"""JSON I/O helpers for tool definitions."""

import json
import structlog
from pathlib import Path
import click  # Needed for click.Abort

# Import path helper
from ._paths import _get_tool_def_path

log = structlog.get_logger()


def _load_json_file(path: Path) -> dict | None:
    """Loads JSON data from a file, handling errors."""
    if not path.is_file():
        log.error("file_not_found", path=str(path))
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error("json_decode_error", path=str(path), error=str(e))
        return None
    except OSError as e:
        log.error("file_read_error", path=str(path), error=str(e))
        return None
    except Exception as e:
        log.exception("unexpected_json_load_error", path=str(path), error=str(e))
        return None


def _write_json_file(path: Path, data: dict) -> bool:
    """Writes data to a JSON file with standard formatting."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        log.debug("json_write_success", path=str(path))
        return True
    except OSError as e:
        log.error("file_write_error", path=str(path), error=str(e))
        return False
    except Exception as e:
        log.exception("unexpected_json_write_error", path=str(path), error=str(e))
        return False


def _load_tool_definition_or_abort(ctx: click.Context, tool_id: str) -> dict:
    """Gets tools_dir from context, finds path, loads JSON, and aborts on error."""
    tools_dir = ctx.obj.get("tools_dir")
    if not tools_dir:
        click.echo("Error: Could not determine tools_dir from context.", err=True)
        raise click.Abort()

    tool_json_path = _get_tool_def_path(tool_id, tools_dir)
    tool_data = _load_json_file(tool_json_path)
    if tool_data is None:
        click.echo(f"Error: Could not load tool definition for '{tool_id}' from {tool_json_path}", err=True)
        raise click.Abort()
    return tool_data
