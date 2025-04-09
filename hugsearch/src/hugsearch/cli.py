"""
# PURPOSE: Command line interface for hugsearch, enabling scripted usage

## INTERFACES:
- search(): Main search command with filtering options
- refresh(): Manual refresh command for models/users/searches
- follow(): Command to follow a creator
- unfollow(): Command to unfollow a creator

## DEPENDENCIES:
- click: CLI framework
- rich: Output formatting
"""

import asyncio
import click
from rich.console import Console
from rich.table import Table
from . import database
from . import scheduler
from .config import get_config
from .cli_args import configure_logging
from .commands import version, check

console = Console()


def run_async(coro):
    """Wrapper to run async functions in click commands"""
    return asyncio.get_event_loop().run_until_complete(coro)


@click.group()
@click.version_option()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (e.g., -v for INFO, -vv for DEBUG).",
    is_eager=True,
)
@click.pass_context
def cli(ctx, verbose):
    """Local Hugging Face model search with caching"""
    ctx.ensure_object(dict)
    ctx.obj["logger"] = configure_logging(verbose)
    # Store verbose level in context for subcommands
    ctx.obj["verbose"] = verbose


# Add commands from the commands directory
cli.add_command(version.command)
cli.add_command(check.command)


@cli.command()
@click.argument("query")
@click.option(
    "--case-sensitive", "-c", is_flag=True, help="Enable case-sensitive search"
)
@click.option("--exact", "-e", is_flag=True, help="Require exact matches")
@click.option("--json", "-j", is_flag=True, help="Output results in JSON format")
@click.option("--filter", "-f", multiple=True, help='Add filters (e.g., -f "tags=gpt")')
def search(query: str, case_sensitive: bool, exact: bool, json: bool, filter: tuple):
    """Search for models in the local cache"""
    # Parse filters
    filters = {}
    for f in filter:
        if "=" in f:
            key, value = f.split("=", 1)
            filters[key.strip()] = value.strip()

    # Perform search
    results = run_async(
        database.search_models(
            get_config().db_path,
            query,
            case_sensitive=case_sensitive,
            exact_match=exact,
            filters=filters,
        )
    )

    if json:
        import json as json_lib

        click.echo(json_lib.dumps(results, indent=2))
    else:
        table = Table(show_header=True)
        table.add_column("Name")
        table.add_column("Author")
        table.add_column("Downloads")
        table.add_column("Last Updated")

        for result in results:
            table.add_row(
                result["name"],
                result["author"],
                str(result.get("downloads", "N/A")),
                result["last_modified"],
            )

        console.print(table)


@cli.command()
@click.argument("items", nargs=-1)
@click.option(
    "--type",
    "-t",
    type=click.Choice(["model", "user", "search"]),
    default="model",
    help="Type of items to refresh",
)
def refresh(items: tuple, type: str):
    """Manually refresh specific models, users, or searches"""
    sched = run_async(scheduler.create_scheduler(get_config().db_path))
    run_async(sched.refresh_models(list(items), type))
    click.echo(f"Refreshed {len(items)} {type}(s)")


@cli.command()
@click.argument("creator")
def follow(creator: str):
    """Follow a creator to get automatic updates"""

    async def _follow():
        async with database.get_connection(get_config().db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO followed_creators (author, last_checked) VALUES (?, ?)",
                (creator, "1970-01-01T00:00:00"),  # Force immediate update
            )
            await db.commit()

        # Trigger immediate refresh of creator's models
        sched = await scheduler.create_scheduler(get_config().db_path)
        await sched.refresh_models([creator], "user")
        await sched.stop()

    run_async(_follow())
    click.echo(f"Now following {creator}")


@cli.command()
@click.argument("creator")
def unfollow(creator: str):
    """Stop following a creator"""

    async def _unfollow():
        async with database.get_connection(get_config().db_path) as db:
            await db.execute(
                "DELETE FROM followed_creators WHERE author = ?", (creator,)
            )
            await db.commit()

    run_async(_unfollow())
    click.echo(f"Unfollowed {creator}")


def main():
    """Entry point for CLI"""
    cli(obj={})


if __name__ == "__main__":
    main()
