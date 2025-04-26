"""
CLI commands related to Git hook management for Zeroth Law.
"""

import logging
import click
import subprocess
from pathlib import Path

# from zeroth_law.git_utils import (
#     find_git_root, install_git_hook_script, restore_git_hooks
# )
# from zeroth_law.path_utils import find_project_root
from zeroth_law.common.git_utils import find_git_root, install_git_hook_script, restore_git_hooks
from zeroth_law.common.path_utils import find_project_root

log = logging.getLogger(__name__)

# Define commands as standalone functions decorated with click.command
# They will be added to the main group in cli.py


@click.command("install-git-hook")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,
    help="Path to the Git repository root (auto-detected if not specified).",
)
@click.pass_context  # Pass context to potentially access project_root later if needed
def install_git_hook(ctx: click.Context, git_root: str | None) -> None:
    """
    Installs the custom ZLT pre-commit hook for multi-project support.

    This replaces any existing pre-commit hook. The original hook (if any)
    is backed up to pre-commit.zl_backup. Use 'restore-git-hooks' to revert.
    """
    log.info("Attempting to install custom ZLT Git pre-commit hook...")
    # Re-find roots here for robustness, don't rely on ctx obj from main group
    project_root = find_project_root(start_path=Path.cwd())
    try:
        git_root_path = Path(git_root) if git_root else find_git_root(start_path=Path.cwd())
        if not git_root_path:
            raise click.ClickException(
                "Could not determine Git repository root. Specify with --git-root or run from within a repo."
            )

        # Ensure project_root is valid if needed by hook logic (not strictly needed by install_git_hook_script itself)
        if not project_root:
            log.warning("Could not determine project root. Hook functionality relying on project context might fail.")

        log.info(f"Using Git root: {git_root_path}")

        # Check for pre-commit framework config
        root_pre_commit_config = git_root_path / ".pre-commit-config.yaml"
        if root_pre_commit_config.exists():
            log.warning(
                f"Found existing {root_pre_commit_config}. The ZLT hook aims to work alongside "
                f"or dispatch to project-specific configs, but conflicts might occur."
            )
            # Consider adding more specific warnings or checks based on hook implementation

        hook_path = install_git_hook_script(git_root_path)  # Installs the ZLT dispatcher hook
        log.info(f"Custom ZLT pre-commit hook installed successfully at {hook_path}")
        click.echo(f"Successfully installed ZLT pre-commit hook in {git_root_path / '.git' / 'hooks'}")

    except (ValueError, OSError, click.ClickException) as e:
        log.error(f"Git hook installation failed: {e}", exc_info=isinstance(e, OSError))
        raise click.ClickException(f"Installation failed: {e}") from e
    except Exception as e:
        log.exception("An unexpected error occurred during git hook installation.", exc_info=e)
        raise click.ClickException("Unexpected installation error.") from e


@click.command("restore-git-hooks")
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
