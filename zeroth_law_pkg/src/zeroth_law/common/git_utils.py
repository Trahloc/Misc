# FILE: src/zeroth_law/git_utils.py
"""Utilities for interacting with Git repositories."""

import subprocess
import structlog
from pathlib import Path
import stat
import importlib.resources

log = structlog.get_logger()


def find_git_root(start_path: Path) -> Path:
    """Find the Git repository root from a given path.

    Uses `git rev-parse --show-toplevel` to find the root directory.

    Args:
    ----
        start_path: The path to start searching from.

    Returns:
    -------
        The absolute path to the Git repository root.

    Raises:
    ------
        ValueError: If the path is not within a Git repository or other error occurs.

    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            cwd=start_path,
        )
        return Path(result.stdout.strip())
    except FileNotFoundError as e:
        raise ValueError("Git command not found") from e  # TRY003 simplified
    except subprocess.CalledProcessError as e:
        raise ValueError("Not a Git repository or git command failed") from e  # TRY003 simplified
    except Exception as e:
        raise ValueError(f"Error finding Git root: {e}") from e  # TRY003 simplified


def get_staged_files(git_root: Path) -> list[Path]:
    """Gets the list of staged files relative to the Git root.

    Uses `git diff --cached --name-only --diff-filter=ACM`.
    Filters for Added, Copied, Modified files.

    Args:
    ----
        git_root: The absolute path to the Git repository root.

    Returns:
    -------
        A list of relative Path objects for staged files, or an empty list.

    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
            cwd=git_root,
            errors="ignore",
        )
        return [Path(line) for line in result.stdout.strip().splitlines() if line]
    except FileNotFoundError:
        log.error("'git' command not found. Is Git installed and in PATH?")
        return []
    except subprocess.CalledProcessError as e:
        log.error(f"'git diff' failed: {e.stderr.strip()}")
        return []
    except Exception as e:
        log.exception(f"Unexpected error getting staged files from {git_root}: {e}")
        return []


def identify_project_roots_from_files(staged_files: list[Path], git_root: Path) -> set[Path]:
    """Identifies the unique project root directories for a list of staged files.

    A project root is defined as a direct subdirectory of the git_root that
    contains a `.pre-commit-config.yaml` file.

    Args:
    ----
        staged_files: A list of file paths relative to the git_root.
        git_root: The absolute path to the Git repository root.

    Returns:
    -------
        A set of unique project root directory names (relative Path objects)
        that contain staged files.

    """
    project_dirs = set()
    for file_path in staged_files:
        try:
            if len(file_path.parts) > 1:
                project_dir_name = file_path.parts[0]
                project_dir_path = git_root / project_dir_name
                if project_dir_path.is_dir() and (project_dir_path / ".pre-commit-config.yaml").is_file():
                    project_dirs.add(Path(project_dir_name))
        except IndexError:
            log.warning(f"Could not process path components for: {file_path}")
            continue
    return project_dirs


def generate_custom_hook_script() -> str:
    """Generates the content for the custom multi-project pre-commit hook script
    by reading it from a dedicated file.

    Returns:
    -------
        The content of the hook script as a string.

    Raises:
    ------
        FileNotFoundError: If the hook script file cannot be found.
    """
    try:
        # Determine the path to the script file relative to this module
        # Use importlib.resources for robust path finding within the package
        script_path = importlib.resources.files("zeroth_law.common.hook_scripts").joinpath("pre-commit-hook.sh")
        with script_path.open("r", encoding="utf-8") as f:
            script_content = f.read()
        return script_content.strip()
    except FileNotFoundError as e:
        log.error(
            "Hook script file not found! Check package data.",
            path=script_path,
            exc_info=True,
        )
        raise FileNotFoundError("Could not find the pre-commit hook script file.") from e
    except Exception as e:
        log.exception("Unexpected error reading hook script file.", exc_info=True)
        raise RuntimeError("Failed to read hook script content.") from e


def install_git_hook_script(git_root: Path) -> Path:
    """Install the custom multi-project pre-commit hook script.

    Args:
    ----
        git_root: The absolute path to the Git repository root.

    Returns:
    -------
        The Path to the installed hook file.

    Raises:
    ------
        ValueError: If the path is not a Git repository or hook installation fails.

    """
    dot_git_path = git_root / ".git"
    if not dot_git_path.is_dir():
        raise ValueError("Not a Git repository root")  # TRY003 simplified

    hooks_dir = dot_git_path / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_file_path = hooks_dir / "pre-commit"

    try:
        script_content = generate_custom_hook_script()
        hook_file_path.write_text(script_content)
        current_permissions = hook_file_path.stat().st_mode
        hook_file_path.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        log.info(f"Successfully installed custom pre-commit hook to: {hook_file_path}")
    except OSError as e:
        raise ValueError("Failed hook write/chmod") from e  # TRY003 simplified
    except Exception as e:
        raise ValueError(f"Unexpected error installing hook: {e}") from e  # TRY003 simplified
    else:
        return hook_file_path


def restore_git_hooks(git_root: Path) -> bool:
    """Restore standard pre-commit hooks, overwriting the custom hook.

    Runs `pre-commit install` in the Git root.

    Args:
    ----
        git_root: The absolute path to the Git repository root.

    Returns:
    -------
        True if successful, False otherwise.

    Raises:
    ------
        ValueError: If pre-commit command fails or other errors occur.

    """
    try:
        log.info(f"Attempting to restore standard pre-commit hooks in: {git_root}")
        result = subprocess.run(
            ["pre-commit", "install"],
            text=True,
            check=True,
            capture_output=True,  # Explicitly capture stdout/stderr
            cwd=git_root,
        )
    except FileNotFoundError as e:
        raise ValueError("'pre-commit' command not found") from e  # TRY003 simplified
    except subprocess.CalledProcessError as e:
        # Log detailed error information using captured output
        error_message = (
            f"'pre-commit install' failed (Exit Code: {e.returncode}):\\n"
            f"--- captured stdout ---\\n{e.stdout}\\n"
            f"--- captured stderr ---\\n{e.stderr}"
        )
        log.error(error_message)
        raise ValueError("pre-commit install failed") from e  # Re-raise as ValueError
    except Exception as e:
        raise ValueError(f"Unexpected error restoring hooks: {e}") from e  # TRY003 simplified
    else:
        log.info("Successfully restored standard pre-commit hooks.")
        # Optionally log successful output if needed
        # log.debug(f"pre-commit install stdout:\\n{result.stdout}")
        # log.debug(f"pre-commit install stderr:\\n{result.stderr}")
        return True


def restore_standard_hooks(git_root_path: Path) -> None:
    """
    Restores standard pre-commit hooks in the specified Git repository root.

    Args:
        git_root_path: Path to the Git repository root.

    Raises:
        ValueError: If 'pre-commit install' fails or if pre-commit is not installed.
    """
    log.info(f"Attempting to restore standard pre-commit hooks in: {git_root_path}")

    # Attempt to run 'pre-commit install' in the git root
    try:
        result = subprocess.run(
            ["pre-commit", "install"],
            cwd=git_root_path,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        log.info("Successfully ran 'pre-commit install' to restore hooks.")
        log.debug("pre-commit install output:\n%s", result.stdout)
    except FileNotFoundError:
        err_msg = "'pre-commit' command not found. Cannot restore hooks automatically."
        log.error(err_msg)
        log.error("Please install pre-commit and run 'pre-commit install' manually in the git root.")
        raise ValueError(err_msg)
    except subprocess.CalledProcessError as e:
        err_msg = f"'pre-commit install' failed (Exit Code: {e.returncode})"
        log.error(err_msg)
        log.error("--- stderr ---")
        log.error(e.stderr)
        log.error("Please check your pre-commit setup and try running manually.")
        raise ValueError(err_msg) from e


# Add other utility functions here
# Test comment for pre-commit hook
