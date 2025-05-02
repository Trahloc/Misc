"""Facade for the 'zlt todo' subcommand group."""

import click


@click.group("todo")
def todo_group():
    """Commands for managing the project TODO list."""
    pass


# Import and add subcommands here (from _todo helpers)
from ._todo.complete import complete # Adjusted import path

todo_group.add_command(complete)
