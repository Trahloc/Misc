# FILE: src/zeroth_law/cli.py
"""Command Line Interface for Zeroth Law Auditor."""

import logging
import os
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

# Internal imports
from .config_loader import DEFAULT_CONFIG, TomlDecodeError, find_pyproject_toml, load_config
from .file_finder import find_python_files
from .git_utils import generate_custom_hook_script

# Setup logger for this module
log = logging.getLogger(__name__)

# Context settings for Click
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


# --- Logging Setup ---
# Placeholder - Basic config done in cli_group for now
def setup_logging(log_level: int, use_color: bool) -> None:
    """Set up logging based on verbosity and color preference."""
    # This function might be needed if more complex setup (like colorama) is added


# --- Core Audit Logic ---
def run_audit(
    paths_to_check: list[Path],
    recursive: bool,
    config: dict[str, Any],
    analyzer_func: Callable | None = None,  # Optional specific analyzer
) -> bool:
    """Runs the compliance audit on the specified files/directories.

    Args:
    ----
        paths_to_check: List of Path objects for files/directories to audit.
        recursive: Whether to search directories recursively.
        config: The loaded configuration dictionary.
        analyzer_func: The function to use for analyzing each file.
                     Defaults to analyze_file_compliance.

    Returns:
    -------
        True if violations were found, False otherwise.

    """
    violations_by_file: dict[Path, dict[str, list[Any]]] = {}
    files_analyzed = 0
    files_with_violations = 0
    compliant_files = 0

    if analyzer_func is None:
        # Import locally to avoid potential circular dependencies
        from .analyzer.python.analyzer import analyze_file_compliance

        analyzer_func = analyze_file_compliance

    log.info("Starting audit on paths: %s (Recursive: %s)", paths_to_check, recursive)

    # Process paths: find all Python files first
    all_python_files: list[Path] = []
    for path in paths_to_check:
        if path.is_file() and path.name.endswith(".py"):
            all_python_files.append(path)
        elif path.is_dir():
            # Use exclude_dirs and exclude_files from config, converting to sets
            exclude_dirs_set = set(config.get("exclude_dirs", []))
            exclude_files_set = set(config.get("exclude_files", []))
            log.debug(
                "Searching %s directory: %s (recursive=%s, exclude_dirs=%s, exclude_files=%s)",
                "top-level of" if not recursive else "recursive",
                path,
                recursive,
                exclude_dirs_set,
                exclude_files_set,
            )
            try:
                # Pass sets to find_python_files
                found = find_python_files(
                    path,
                    exclude_dirs=exclude_dirs_set,
                    exclude_files=exclude_files_set,
                )
                all_python_files.extend(found)
            except Exception as e:
                log.error(f"Error finding files in {path}: {e}")
        else:
            log.warning(f"Skipping non-Python file or non-directory: {path}")

    # Remove duplicates if paths overlapped
    unique_python_files = sorted(list(set(all_python_files)))
    files_analyzed = len(unique_python_files)
    log.info("Found %d Python files to analyze.", files_analyzed)

    # Analyze each file
    for py_file in unique_python_files:
        log.debug("Analyzing: %s", py_file)
        try:
            violations = analyzer_func(
                py_file,
                max_complexity=config.get("max_complexity", DEFAULT_CONFIG["max_complexity"]),
                max_params=config.get("max_parameters", DEFAULT_CONFIG["max_parameters"]),
                max_statements=config.get("max_statements", DEFAULT_CONFIG["max_statements"]),
                max_lines=config.get("max_lines", DEFAULT_CONFIG["max_lines"]),
                ignore_rules=config.get("ignore_rules", DEFAULT_CONFIG["ignore_rules"]),
            )
            if violations:
                violations_by_file[py_file] = violations
                log.warning(" -> Violations found in %s: %s", py_file.name, list(violations.keys()))
                files_with_violations += 1
            else:
                compliant_files += 1
                log.debug(" -> No violations found in %s", py_file.name)

        except FileNotFoundError:
            log.error("File not found during analysis: %s", py_file)
            violations_by_file[py_file] = {"error": ["File not found during analysis"]}
            files_with_violations += 1
        except SyntaxError as e:
            log.error("Syntax error in file: %s - %s", py_file, e)
            violations_by_file[py_file] = {"error": [f"SyntaxError: {e}"]}
            files_with_violations += 1
        except Exception as e:
            log.exception(f"Unexpected error analyzing {py_file}", exc_info=e)
            violations_by_file[py_file] = {"error": [f"Unexpected analysis error: {e}"]}
            files_with_violations += 1

    # --- Log Summary --- #
    log.warning("-" * 40)
    log.warning("Audit Summary:")
    log.info(" Total files analyzed: %d", files_analyzed)
    if files_with_violations > 0:
        log.warning(" Files with violations: %d", files_with_violations)
    if compliant_files > 0:
        log.info(" Compliant files: %d", compliant_files)
    log.warning("-" * 40)

    # --- Log Detailed Violations --- #
    if violations_by_file:
        log.warning("\nDetailed Violations:")
        for file_path, violations in sorted(violations_by_file.items()):
            rel_path = file_path
            try:
                # Attempt to get relative path, fallback to original if error
                rel_path = file_path.relative_to(Path.cwd())
            except ValueError:
                pass  # Keep original absolute path
            log.warning("\nFile: %s", rel_path)
            for category, issues in sorted(violations.items()):
                log.warning("  %s:", category.capitalize())
                if not issues:
                    log.warning("    (No specific issues listed for this category)")
                    continue
                for issue in issues:
                    # Format issue nicely (handle tuples vs strings)
                    if isinstance(issue, tuple):
                        issue_str = ", ".join(map(str, issue))
                        log.warning("    - (%s)", issue_str)
                    elif isinstance(issue, str):
                        log.warning("    - %s", issue)
                    else:
                        log.warning("    - %s", str(issue))

    return files_with_violations > 0


# --- CLI Group and Global Options ---
@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(package_name="zeroth-law", prog_name="zeroth-law")
@click.option(
    "-v",
    "--verbose",
    "verbosity",
    count=True,
    default=0,
    help="Increase verbosity: -v for INFO, -vv for DEBUG.",
    type=click.IntRange(0, 2),
)
@click.option("-q", "--quiet", is_flag=True, default=False, help="Suppress all output except errors.")
@click.option(
    "--color/--no-color",
    is_flag=True,
    help="Enable colored logging output.",  # Placeholder, color not implemented yet
)
@click.pass_context
def cli_group(ctx: click.Context, verbosity: int, quiet: bool, color: bool) -> None:
    """Zeroth Law Compliance Auditor CLI."""
    log_level = logging.WARNING  # Default
    if quiet:
        log_level = logging.ERROR
    elif verbosity == 1:
        log_level = logging.INFO
    elif verbosity >= 2:
        log_level = logging.DEBUG

    # Basic logging config
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)-8s] %(message)s [%(name)s]",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Store config in context
    ctx.ensure_object(dict)
    ctx.obj["LOG_LEVEL"] = log_level
    ctx.obj["COLOR"] = color

    log.debug(
        "CLI group initiated. log_level=%s, color=%s",
        logging.getLevelName(log_level),
        color,
    )


# --- Audit Command ---
@cli_group.command("audit")
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True, path_type=Path),
    default=None,
)
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path),
    help="Path to configuration file (e.g., pyproject.toml). Overrides default search.",
)
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recursively search directories for Python files.",
)
@click.pass_context
def audit_command(ctx: click.Context, paths: tuple[Path, ...], config_path: Path | None, recursive: bool) -> None:
    """Perform Zeroth Law compliance audit on specified Python files or directories."""
    # Get log level and color from context
    log_level = ctx.obj.get("LOG_LEVEL", logging.WARNING)
    use_color = ctx.obj.get("COLOR", False)  # Placeholder, not used yet

    log.debug(
        "Audit command called. paths=%s config=%s recursive=%s log_level=%s color=%s",
        paths,
        config_path,
        recursive,
        logging.getLevelName(log_level),
        use_color,
    )

    effective_paths = list(paths) if paths else [Path.cwd()]

    # --- Configuration Loading ---
    try:
        cfg = load_config(config_path)
        log.info("Using configuration: %s", cfg)
    except FileNotFoundError as e:
        log.error(f"Configuration file error: {e}")
        ctx.exit(1)
    except TomlDecodeError as e:
        log.error(f"Configuration file error: {e}")
        ctx.exit(1)
    except Exception as e:
        log.exception(f"Unexpected error loading configuration: {e}", exc_info=e)
        ctx.exit(1)

    # --- Run Audit ---
    try:
        violations_found = run_audit(
            paths_to_check=effective_paths,  # Correct parameter name used here
            config=cfg,
            recursive=recursive,
        )
    except Exception as e:
        # Catch unexpected errors during the audit itself
        log.exception(f"Unexpected error during audit process: {e}", exc_info=e)
        ctx.exit(1)

    if violations_found:
        log.warning("Project has compliance violations.")
        ctx.exit(1)
    else:
        log.warning("Project is compliant!")
        ctx.exit(0)


# --- Install Git Hook Command ---
@cli_group.command("install-git-hook")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="Path to the Git repository root.",
    show_default=True,
)
@click.pass_context
def install_git_hook(ctx: click.Context, git_root: str) -> None:
    """Install the custom multi-project pre-commit hook script."""
    log_level = ctx.obj.get("LOG_LEVEL", logging.INFO)  # Default to INFO for this cmd
    use_color = ctx.obj.get("COLOR", False)
    # Re-setup logging if needed based on context (or assume basicConfig is sufficient)
    logging.getLogger().setLevel(log_level)

    log.debug("Install git hook command called", git_root=git_root)
    git_root_path = Path(git_root).resolve()

    dot_git_path = git_root_path / ".git"
    if not dot_git_path.is_dir():
        log.error(f"Target directory '{git_root_path}' is not a valid Git repository root.")
        click.echo(f"Error: Directory '{git_root_path}' does not contain a .git directory.", err=True)
        ctx.exit(1)

    hooks_dir = dot_git_path / "hooks"
    hook_file_path = hooks_dir / "pre-commit"

    try:
        script_content = generate_custom_hook_script()
    except Exception as e:
        log.exception(f"Failed to generate custom hook script content: {e}")
        click.echo(f"Error: Failed to generate hook script: {e}", err=True)
        ctx.exit(1)

    try:
        hooks_dir.mkdir(exist_ok=True)
        with hook_file_path.open("w", encoding="utf-8") as f:
            f.write(script_content)
        log.info("Custom hook script written successfully.", path=str(hook_file_path))
        # Make executable
        hook_file_path.chmod(hook_file_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        log.info("Set execute permissions on hook script.", path=str(hook_file_path))

    except OSError as e:
        log.exception(f"Failed to write or chmod pre-commit hook script at path '{hook_file_path}': {e}")
        click.echo(f"Error: Could not write/chmod hook file to '{hook_file_path}': {e}", err=True)
        ctx.exit(1)

    click.echo(f"Successfully installed Zeroth Law custom pre-commit hook to: {hook_file_path}")

    # Check for root pre-commit config and warn if found
    root_config_path = git_root_path / ".pre-commit-config.yaml"
    if root_config_path.is_file():
        log.warning("Root pre-commit config found during custom hook installation.")
        click.echo("-" * 20, err=True)
        click.echo("WARNING: Found '.pre-commit-config.yaml' at the Git root.", err=True)
        click.echo("         The Zeroth Law custom multi-project hook has been installed.", err=True)
        click.echo("         This hook prioritizes project-specific configs in subdirectories.", err=True)
        click.echo("         If this repository IS NOT intended as a multi-project monorepo,", err=True)
        click.echo("         you should restore the standard pre-commit hook behavior.", err=True)
        click.echo("         Consider running: zeroth-law restore-git-hooks", err=True)
        click.echo("-" * 20, err=True)


# --- Restore Git Hooks Command ---
@cli_group.command("restore-git-hooks")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="Path to the Git repository root.",
    show_default=True,
)
@click.pass_context
def restore_git_hooks(ctx: click.Context, git_root: str) -> None:
    """Restore the default pre-commit hook script using 'pre-commit install'."""
    log_level = ctx.obj.get("LOG_LEVEL", logging.INFO)  # Default to INFO
    use_color = ctx.obj.get("COLOR", False)
    logging.getLogger().setLevel(log_level)

    log.debug("Restore git hooks command called", git_root=git_root)
    git_root_path = Path(git_root).resolve()

    dot_git_path = git_root_path / ".git"
    if not dot_git_path.is_dir():
        log.error(f"Target directory '{git_root_path}' is not a valid Git repository root.")
        click.echo(f"Error: Directory '{git_root_path}' does not contain a .git directory.", err=True)
        ctx.exit(1)

    log.info(f"Attempting to restore default hooks using 'pre-commit install' in CWD '{git_root_path}'...")
    try:
        result = subprocess.run(
            ["pre-commit", "install"],  # Run pre-commit install
            capture_output=True,
            text=True,
            check=True,
            cwd=git_root_path,  # Run in the specified git root
        )
        log.info("pre-commit install completed successfully.", stdout=result.stdout.strip())
        click.echo("Default pre-commit hooks restored successfully.")
        if result.stdout.strip():
            click.echo(result.stdout.strip())

    except FileNotFoundError:
        log.error("'pre-commit' command not found. Is pre-commit installed and in PATH?")
        click.echo("Error: 'pre-commit' command not found. Is it installed?", err=True)
        ctx.exit(1)
    except subprocess.CalledProcessError as e:
        log.error(f"'pre-commit install' command failed. Return Code: {e.returncode}. Stderr: {e.stderr.strip() if e.stderr else 'N/A'}")
        click.echo(f"Error restoring default hooks: {e}", err=True)
        if e.stderr:
            click.echo(f"Stderr: {e.stderr.strip()}", err=True)
        ctx.exit(1)
    except Exception as e:
        log.exception(f"Unexpected error restoring git hooks in {git_root_path}", exc_info=e)
        click.echo(f"An unexpected error occurred: {e}", err=True)
        ctx.exit(1)


if __name__ == "__main__":
    cli_group()

# <<< ZEROTH LAW FOOTER >>>
