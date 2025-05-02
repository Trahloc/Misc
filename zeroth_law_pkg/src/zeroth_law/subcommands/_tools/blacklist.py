"""Facade for the 'zlt tools blacklist' command group."""

import click

# Import the command implementations from the helper directory
from ._blacklist._add import add_blacklist
from ._blacklist._remove import remove_blacklist


@click.group("blacklist")
def blacklist():
    """Manage the tool blacklist in pyproject.toml."""
    pass


# Register the commands with the group
blacklist.add_command(add_blacklist)
blacklist.add_command(remove_blacklist)
