"""
Helper implementation for the 'zlt install-git-hook' command.
"""

import structlog
import click
from pathlib import Path

# Correct relative import: Go up three levels to reach src/zeroth_law, then down to common
from ...common.git_utils import find_git_root, install_git_hook_script
from ...common.path_utils import find_project_root, ZLFProjectRootNotFoundError

log = structlog.get_logger()

# Define the enhanced hook script content
hook_script_content = """#!/usr/bin/env bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "[Zeroth Law Hook] Running enhanced multi-project pre-commit hook..."

GIT_ROOT=$(git rev-parse --show-toplevel)
if [ -z "$GIT_ROOT" ]; then
    echo "[Zeroth Law Hook] Error: Could not determine Git repository root." >&2
    exit 1
fi

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM HEAD)
if [ -z "$STAGED_FILES" ]; then
    echo "[Zeroth Law Hook] No staged files to check."
    exit 0
fi

readarray -t STAGED_FILES_ARRAY <<<"$STAGED_FILES"
declare -A project_configs_to_run # Key: path to .pre-commit-config.yaml, Value: list of files

# Determine which pre-commit configs are relevant for the staged files
for file_abs_path_git_root in "${STAGED_FILES_ARRAY[@]}"; do
    file_full_path="$GIT_ROOT/$file_abs_path_git_root"
    current_dir=$(dirname "$file_full_path")
    config_found_for_file=""

    # Traverse upwards to find the closest .pre-commit-config.yaml
    while [[ "$current_dir" != "/" && "$current_dir" != "." && "$current_dir" != "$GIT_ROOT/.." ]]; do
        if [ -f "$current_dir/.pre-commit-config.yaml" ]; then
            config_found_for_file="$current_dir/.pre-commit-config.yaml"
            break
        fi
        # If we reach GIT_ROOT and it has a config, that's the one.
        if [[ "$current_dir" == "$GIT_ROOT" && -f "$GIT_ROOT/.pre-commit-config.yaml" ]]; then
            config_found_for_file="$GIT_ROOT/.pre-commit-config.yaml"
            break
        fi
        # Stop if we are at GIT_ROOT and it has NO config, or if we go above GIT_ROOT
        if [[ "$current_dir" == "$GIT_ROOT" ]] || [[ ! "$current_dir" =~ ^"$GIT_ROOT" ]]; then
            break
        fi
        current_dir=$(dirname "$current_dir")
    done
    
    # If no specific config found, and GIT_ROOT has one, use that.
    if [[ -z "$config_found_for_file" && -f "$GIT_ROOT/.pre-commit-config.yaml" ]]; then
        config_found_for_file="$GIT_ROOT/.pre-commit-config.yaml"
    fi

    if [ -n "$config_found_for_file" ]; then
        project_configs_to_run["$config_found_for_file"]+="$file_full_path "
    else
        echo "[Zeroth Law Hook] Info: File '$file_abs_path_git_root' is not covered by any .pre-commit-config.yaml."
    fi
done

if [ ${#project_configs_to_run[@]} -eq 0 ]; then
    echo "[Zeroth Law Hook] No .pre-commit-config.yaml configurations cover the staged files. Skipping checks."
    exit 0
fi

# --- Execute pre-commit for each relevant config ---
exit_code=0
for config_file_path in "${!project_configs_to_run[@]}"; do
    config_dir=$(dirname "$config_file_path")
    files_for_this_config="${project_configs_to_run[$config_file_path]}"
    
    # Convert space-separated string of files to an array for pre-commit
    read -r -a files_array <<< "$files_for_this_config"

    echo "[Zeroth Law Hook] Processing config: $config_file_path"
    echo "[Zeroth Law Hook] Directory: $config_dir"
    # echo "[Zeroth Law Hook] Files: ${files_array[@]}" # Can be verbose

    # Change directory safely
    if ! pushd "$config_dir" > /dev/null; then
        echo "[Zeroth Law Hook] Error: Could not cd to $config_dir" >&2
        exit_code=1
        continue # Try next config if possible
    fi

    run_failed=false
    if [ -f "./pyproject.toml" ]; then
        echo "[Zeroth Law Hook] Python project detected (pyproject.toml found). Using 'uv run pre-commit ...'"
        if command -v uv >/dev/null 2>&1; then
            # Run uv with error handling
            if ! uv run -- pre-commit run --config ./.pre-commit-config.yaml --files "${files_array[@]}"; then
                echo "[Zeroth Law Hook] 'uv run pre-commit' failed for $config_file_path." >&2
                run_failed=true
            fi
        else
            echo "[Zeroth Law Hook] Warning: 'uv' command not found, but pyproject.toml exists in $config_dir." >&2
            echo "Attempting to run 'pre-commit' directly for $config_file_path..." >&2
            if command -v pre-commit >/dev/null 2&>1; then
                if ! pre-commit run --config ./.pre-commit-config.yaml --files "${files_array[@]}"; then
                     echo "[Zeroth Law Hook] 'pre-commit' (direct) failed for $config_file_path." >&2
                     run_failed=true
                fi
            else
                echo "[Zeroth Law Hook] Error: 'pre-commit' command not found directly in $config_dir for Python project. Cannot run checks." >&2
                run_failed=true # ZLF projects require checks
            fi
        fi
    else
        echo "[Zeroth Law Hook] Not a Python project (no pyproject.toml in $config_dir)."
        echo "Attempting to run 'pre-commit' directly for $config_file_path..."
        if command -v pre-commit >/dev/null 2>&1; then
            if ! pre-commit run --config ./.pre-commit-config.yaml --files "${files_array[@]}"; then
                 echo "[Zeroth Law Hook] 'pre-commit' (direct) failed for $config_file_path." >&2
                 run_failed=true
            fi
        else
            echo "[Zeroth Law Hook] Warning: 'pre-commit' command not found directly, and not a Python project in $config_dir." >&2
            echo "Skipping pre-commit checks for $config_file_path. To enable, install 'pre-commit' globally or make it a Python project." >&2
            # Do NOT set run_failed=true here; allow commit if pre-commit is not available for a non-Python project's config
        fi
    fi
    
    popd > /dev/null # Go back to original directory
    
    if $run_failed; then
        exit_code=1 # Record failure but continue processing other configs if needed
    else
         echo "[Zeroth Law Hook] Checks completed successfully for config: $config_file_path"
    fi
done

if [ $exit_code -eq 0 ]; then
    echo "[Zeroth Law Hook] All relevant pre-commit checks passed."
fi

exit $exit_code
"""


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
