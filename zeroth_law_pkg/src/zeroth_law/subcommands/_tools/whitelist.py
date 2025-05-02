"""Facade for the 'zlt tools whitelist' command group."""

import click

# Import the command implementations from the helper directory
from ._whitelist._add import add_whitelist
from ._whitelist._remove import remove_whitelist


@click.group("whitelist")
def whitelist():
    """Manage the tool whitelist in pyproject.toml."""
    pass


# Register the commands with the group
whitelist.add_command(add_whitelist)
whitelist.add_command(remove_whitelist)
