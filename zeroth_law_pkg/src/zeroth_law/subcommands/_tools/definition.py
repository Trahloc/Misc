"""Facade for the 'zlt tools definition' subcommand group."""

import click

# Import command implementations from helpers
from ._definition._capability_cmds import add_capability, remove_capability
from ._definition._filetype_cmds import set_filetypes
from ._definition._mapping_cmds import map_option, unmap_option

# _paths.py and _io.py contain helpers used by the command implementations,
# they don't define commands themselves.


@click.group("definition")
def definition_group():
    """Commands for managing tool definition JSON files."""
    # Maybe add path loading to context here?
    pass


# Register commands
definition_group.add_command(add_capability)
definition_group.add_command(remove_capability)
definition_group.add_command(set_filetypes)
definition_group.add_command(map_option)
definition_group.add_command(unmap_option)

# --- REMOVED HELPER FUNCTIONS ---
# These were moved to helper modules (_paths.py, _io.py)
# def get_tool_def_path(tool_id: str) -> Path:
# ... etc ...
# def load_json_file(path: Path) -> dict | None:
# ... etc ...
# def write_json_file(path: Path, data: dict) -> bool:
# ... etc ...
