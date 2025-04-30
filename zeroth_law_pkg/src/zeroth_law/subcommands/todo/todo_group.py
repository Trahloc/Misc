import click


@click.group("todo")
def todo_group():
    """Commands for managing the project TODO list."""
    pass


# Import and add subcommands here
from .complete import complete

todo_group.add_command(complete)
