#!/usr/bin/env python3 # Keep shebang?
"""Implements the 'zlt todo complete' subcommand."""

import click
import re
import sys
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

# Determine paths relative to the project root (assuming CLI context provides it)
# This might need adjustment depending on how project_root is passed via ctx
# PROJECT_ROOT = Path(__file__).parent.parent.parent.parent # Adjust based on final location
# TODO_FILE = PROJECT_ROOT / "TODO.md"
# ARCHIVE_DIR = PROJECT_ROOT / "docs" / "todos"

log = structlog.get_logger()

# --- Helper Function (from script) ---


def find_phase_section(lines: list[str], phase_header: str) -> tuple[int | None, int | None, list[str]]:
    """Finds the start and end line indices and content of a phase section."""
    start_index = None
    end_index = None
    header_found = False
    normalized_target_header = phase_header.strip()
    phase_regex = re.compile(r"^## \*\*(Phase [A-Z]: .+)\*\*$")  # Regex for *any* phase header

    for i, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line == normalized_target_header:
            if header_found:
                raise ValueError(f"Error: Duplicate phase header found: '{phase_header}'")
            start_index = i
            header_found = True
            continue

        if header_found:
            if phase_regex.match(stripped_line):
                end_index = i
                break

    if start_index is None:
        return None, None, []

    if end_index is None:
        end_index = len(lines)

    section_content = lines[start_index:end_index]
    return start_index, end_index, section_content


# --- Click Command Definition ---


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
    project_root = ctx.obj.get("project_root")
    if not project_root:
        log.error("Project root could not be determined. Cannot manage TODO.md.")
        ctx.exit(1)

    todo_file = project_root / "TODO.md"
    archive_dir = project_root / "docs" / "todos"

    if not todo_file.exists():
        log.error(f"Error: Cannot find TODO.md at {todo_file}")
        ctx.exit(1)

    # Ensure archive directory exists
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Read TODO.md content
    try:
        lines = todo_file.read_text(encoding="utf-8").splitlines(keepends=True)
    except IOError as e:
        log.error(f"Error reading {todo_file}: {e}")
        ctx.exit(1)

    # Find the section
    try:
        start_idx, end_idx, section_lines = find_phase_section(lines, phase_header)
    except ValueError as e:  # Handles duplicate header error
        log.error(str(e))
        ctx.exit(1)

    if start_idx is None or not section_lines:
        log.error(f"Error: Phase header not found or section empty: '{phase_header}'")
        ctx.exit(1)

    # Generate archive filename
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    archive_filename = archive_dir / f"completed-{timestamp}.md"

    # Perform dry run or actual archive
    if not confirmed:
        if report:
            log.warning("The --report option is ignored when --confirmed is not used.")
        click.echo("--- DRY RUN --- (No changes will be made)")
        click.echo(f"Phase Header: {phase_header}")
        click.echo(f"Detected Section: Lines {start_idx + 1} to {end_idx}")
        click.echo(f"Archive File: {archive_filename}")
        click.echo("Section Content To Be Moved:")
        click.echo("------------------------------")
        click.echo("".join(section_lines).strip())
        click.echo("------------------------------")
        click.echo("\nRun with --confirmed flag to perform the archive.")
    else:
        click.echo(f"--- EXECUTING ARCHIVE --- ")
        click.echo(f"Phase Header: {phase_header}")
        click.echo(f"Moving section (Lines {start_idx + 1}-{end_idx}) to {archive_filename}")
        if report:
            click.echo(f"Prepending Executive Summary to archived content.")

        # Prepare content to write (potentially prepend report)
        content_to_archive = []
        if report:
            # Add report directly as Markdown
            content_to_archive.append("Executive Summary:\n")
            content_to_archive.append("------------------\n")
            report_lines = report.strip().splitlines()
            content_to_archive.extend(f"{line}\n" for line in report_lines)
            content_to_archive.append("\n")  # Blank line before separator
            content_to_archive.append("--- \n")  # Separator
            content_to_archive.append("\n")  # Blank line after separator

        content_to_archive.extend(section_lines)

        # 1. Write to archive file (overwrite or create)
        try:
            # Use 'w' mode to create/overwrite the specific timestamped file
            with open(archive_filename, "w", encoding="utf-8") as af:
                af.writelines(content_to_archive)
                # Ensure trailing newline if last line didn't have one
                if content_to_archive and not content_to_archive[-1].endswith("\n"):
                    af.write("\n")
            log.info(f"Successfully wrote archive to {archive_filename}")
        except IOError as e:
            log.error(f"Error writing to archive file {archive_filename}: {e}")
            ctx.exit(1)

        # 2. Remove from original lines
        remaining_lines = lines[:start_idx] + lines[end_idx:]

        # 3. Write modified TODO.md back
        try:
            with open(todo_file, "w", encoding="utf-8") as f:
                f.writelines(remaining_lines)
            log.info(f"Successfully updated {todo_file}")
        except IOError as e:
            log.error(f"Error writing updated {todo_file}: {e}")
            log.warning("Archive file was created, but TODO.md update failed.")
            ctx.exit(1)

        click.echo("Archive operation completed.")
