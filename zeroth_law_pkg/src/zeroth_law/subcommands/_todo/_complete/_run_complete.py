"""Core logic for the 'zlt todo complete' command."""

import click
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

# Import the parser helper
from ._parser import _find_phase_section

log = structlog.get_logger()


def _run_complete_logic(
    project_root: Path,
    phase_header: str,
    confirmed: bool,
    report: str | None,
) -> int:
    """Handles the logic for completing and archiving a TODO phase.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    exit_code = 0
    todo_file = project_root / "TODO.md"
    archive_dir = project_root / "docs" / "todos"

    if not todo_file.exists():
        log.error(f"Error: Cannot find TODO.md at {todo_file}")
        return 1  # Indicate failure

    # Ensure archive directory exists
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Read TODO.md content
    try:
        lines = todo_file.read_text(encoding="utf-8").splitlines(keepends=True)
    except IOError as e:
        log.error(f"Error reading {todo_file}: {e}")
        return 1  # Indicate failure

    # Find the section
    try:
        start_idx, end_idx, section_lines = _find_phase_section(lines, phase_header)
    except ValueError as e:  # Handles duplicate header error
        log.error(str(e))
        return 1  # Indicate failure

    if start_idx is None or not section_lines:
        log.error(f"Error: Phase header not found or section empty: '{phase_header}'")
        return 1  # Indicate failure

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
            return 1  # Indicate failure

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
            return 1  # Indicate failure

        click.echo("Archive operation completed.")

    return exit_code  # Should be 0 if reached here
