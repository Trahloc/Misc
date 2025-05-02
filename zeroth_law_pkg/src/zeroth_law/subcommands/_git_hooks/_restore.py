"""
Helper implementation for the 'zlt restore-git-hooks' command.
"""

import structlog
import click
from pathlib import Path

# Adjust imports for moved utils
from ..common.git_utils import find_git_root, restore_git_hooks
# No path_utils needed here

log = structlog.get_logger()


@click.command("restore-git-hooks")  # Keep command name for registration
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,
    help="Path to the Git repository root (auto-detected if not specified).",
)
@click.pass_context  # Pass context for consistency, though not strictly needed here
def restore_git_hooks(ctx: click.Context, git_root: str | None) -> None:
    """
    Restores standard pre-commit hooks backed up by ZLT, removing the dispatcher.

    Looks for '.zl_backup' files in the hooks directory and restores them.
    """
    log.info("Attempting to restore standard Git hooks...")
    try:
        git_root_path = Path(git_root) if git_root else find_git_root(start_path=Path.cwd())
        if not git_root_path:
            raise click.ClickException(
                "Could not determine Git repository root. Specify with --git-root or run from within a repo."
            )

        log.debug(f"Using Git repository root: {git_root_path}")
        restored_count, error_count = restore_git_hooks(git_root_path)

        if restored_count > 0:
            log.info(f"Successfully restored {restored_count} standard Git hooks.")
            click.echo(f"Successfully restored {restored_count} Git hooks.")
        else:
            log.info("No standard Git hooks found to restore (or errors occurred).")
            click.echo("No standard Git hooks found to restore.")

        if error_count > 0:
            log.error(f"Encountered {error_count} errors during hook restoration.")
            # Raise exception to signal failure to Click
            raise click.ClickException(f"Encountered {error_count} errors during restoration.")

    except (ValueError, OSError, click.ClickException) as e:
        log.error(f"Git hook restoration failed: {e}", exc_info=isinstance(e, OSError))
        raise click.ClickException(f"Restoration failed: {e}") from e
    except Exception as e:
        log.exception("An unexpected error occurred during git hook restoration.", exc_info=e)
        raise click.ClickException("Unexpected restoration error.") from e
