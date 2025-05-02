"""
Helper implementation for the 'zlt install-git-hook' command.
"""

import structlog
import click
from pathlib import Path

# Adjust imports for moved utils
from ..common.git_utils import find_git_root, install_git_hook_script
from ..common.path_utils import find_project_root

log = structlog.get_logger()


@click.command("install-git-hook")  # Keep command name for registration
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,
    help="Path to the Git repository root (auto-detected if not specified).",
)
@click.pass_context
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
