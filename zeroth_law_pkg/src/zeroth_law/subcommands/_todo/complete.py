"""Facade for the 'zlt todo complete' subcommand."""

import click
import structlog
from pathlib import Path

# Import the core logic helper (adjust path)
from ._complete._run_complete import _run_complete_logic

log = structlog.get_logger()


@click.command("complete")
@click.argument("phase_header", type=str)
@click.option("--confirmed", is_flag=True, help="Perform the archive operation. Without this flag, performs a dry run.")
@click.option(
    "--report",
    type=str,
    default=None,
    help="Executive Summary string (Markdown format) to prepend to the archived phase content. Used only with --confirmed.",
)
@click.pass_context
def complete(ctx: click.Context, phase_header: str, confirmed: bool, report: str | None):
    """Archives a completed phase section from TODO.md to docs/todos/.

    Finds the section starting with the exact PHASE_HEADER markdown line
    (e.g., '## **Phase H: Tool Management Subcommand (`zlt tools`)**')
    and moves it to a timestamped file.

    When using --confirmed, a --report <summary> option can be provided
    to prepend an AI-generated Executive Summary (Markdown) to the archived content.
    """
    log.debug("Entering 'todo complete' command facade.")
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined. Cannot manage TODO.md.")
        ctx.exit(1)

    # Call the helper logic
    exit_code = _run_complete_logic(
        project_root=project_root,
        phase_header=phase_header,
        confirmed=confirmed,
        report=report,
    )

    ctx.exit(exit_code)
