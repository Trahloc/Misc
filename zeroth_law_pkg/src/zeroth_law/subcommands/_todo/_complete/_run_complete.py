"""Core logic for the 'zlt todo complete' command."""

import click
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Optional

# Removed import from empty parser: from ._parser import _find_phase_section

log = structlog.get_logger()


# --- Re-implemented Phase Parsing Logic ---
def _find_phase_section(lines: List[str], phase_header: str) -> Tuple[Optional[int], Optional[int], List[str]]:
    """Finds the start and end lines of a section identified by its exact header.

    Args:
        lines: List of lines from the TODO.md file (with trailing newlines).
        phase_header: The exact markdown header line (e.g., "## **Phase H: ...**").

    Returns:
        A tuple (start_index, end_index, section_lines).
        start_index: The index of the phase_header line (or None if not found).
        end_index: The index of the *next* header line (or len(lines) if phase_header is the last section).
        section_lines: A list of lines belonging to the section (including the header).

    Raises:
        ValueError: If the phase_header is found multiple times.
    """
    start_idx: Optional[int] = None
    found_indices: List[int] = []

    # First pass: Find all occurrences of the exact header
    for i, line in enumerate(lines):
        if line.strip() == phase_header.strip():
            found_indices.append(i)

    if not found_indices:
        return None, None, []  # Header not found
    if len(found_indices) > 1:
        raise ValueError(
            f"Error: Duplicate phase header found: '{phase_header}'. "
            f"Found at lines: {[idx + 1 for idx in found_indices]}"
        )

    start_idx = found_indices[0]

    # Second pass: Find the next header (starting with '# ') after start_idx
    end_idx: int = len(lines)  # Default to end of file
    for i in range(start_idx + 1, len(lines)):
        # Look for any line starting with '#' followed by a space, indicating a new markdown header
        if lines[i].strip().startswith("# "):
            end_idx = i
            break

    section_lines = lines[start_idx:end_idx]
    return start_idx, end_idx, section_lines


# --- Main Command Logic ---
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
        # Keep ends needed for accurate line removal later
        lines = todo_file.read_text(encoding="utf-8").splitlines(keepends=True)
    except IOError as e:
        log.error(f"Error reading {todo_file}: {e}")
        return 1  # Indicate failure

    # Find the section using the re-implemented function
    try:
        start_idx, end_idx, section_lines = _find_phase_section(lines, phase_header)
    except ValueError as e:  # Handles duplicate header error
        log.error(str(e))
        return 1  # Indicate failure

    # Check if start_idx is None (header not found) OR if end_idx is None (shouldn't happen with current logic but check anyway)
    # Also check if section_lines is empty which implies header was found but no lines followed
    if start_idx is None or end_idx is None or not section_lines:
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
        # Use end_idx directly as it's exclusive index; add 1 to start_idx for 1-based display
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
        # Use end_idx directly; add 1 to start_idx for display
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

        # 2. Remove from original lines using the correct indices
        remaining_lines = lines[:start_idx] + lines[end_idx:]  # Use end_idx directly

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


# <<< ZEROTH LAW FOOTER >>>
