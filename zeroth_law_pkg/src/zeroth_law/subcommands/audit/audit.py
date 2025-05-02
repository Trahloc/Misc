# FILE: src/zeroth_law/subcommands/audit/audit.py
"""Facade for the 'zlt audit' command."""

import click
from pathlib import Path

# Import the core logic from the helper module
from ._audit._run_audit import _run_audit_logic

# We might need structlog here if the facade needs to log anything itself
import structlog

log = structlog.get_logger()


@click.command("audit")
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True, path_type=Path),
    required=False,
)
@click.option(
    "-R",
    "--recursive",
    is_flag=True,
    default=None,
    help="Recursively search directories for Python files.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output violations in JSON format.",
)
@click.pass_context
def audit(
    ctx: click.Context,
    paths: tuple[Path, ...],
    recursive: bool | None,
    output_json: bool,
) -> None:
    """Perform static analysis checks based on ZLF principles."""
    log.debug("Entering 'audit' command facade.")
    # Extract necessary info from context
    config = ctx.obj.get("config", {})
    # verbosity = ctx.obj.get("verbosity", 0) # Pass verbosity if needed by helper
    verbosity = 0  # Placeholder if not used
    project_root = ctx.obj.get("project_root")

    # Call the core logic function from the helper module
    exit_code = _run_audit_logic(
        config=config,
        verbosity=verbosity,
        project_root=project_root,
        paths_cli=paths,
        recursive_cli=recursive,
        output_json_cli=output_json,
    )

    # Exit with the code returned by the core logic
    ctx.exit(exit_code)
