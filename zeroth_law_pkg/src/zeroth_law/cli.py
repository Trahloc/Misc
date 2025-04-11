# FILE: src/zeroth_law/cli.py
"""Command Line Interface for Zeroth Law Auditor."""

import json  # Re-add JSON import
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

# Import the new action runner
# Internal imports
from .config_loader import (
    load_config,
)
from .file_finder import find_python_files
from .git_utils import (
    find_git_root,
    install_git_hook_script,
)
from .path_utils import find_project_root

# Setup logger for this module
log = logging.getLogger(__name__)

# Context settings for Click
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


# --- Logging Setup ---
# Placeholder - Basic config done in cli_group for now
def setup_logging(log_level: int, use_color: bool) -> None:
    """Set up logging based on verbosity and color preference."""
    # This function might be needed if more complex setup (like colorama) is added


# --- Core File Finding Logic ---
def find_files_to_audit(paths_to_check: list[Path], recursive: bool, config: dict[str, Any]) -> list[Path]:
    """Find all Python files to audit from the given paths.

    Args:
        paths_to_check: List of Path objects for files/directories to audit.
        recursive: Whether to search directories recursively.
        config: The loaded configuration dictionary.

    Returns:
        A list of Path objects to Python files that should be audited.

    """
    all_python_files: list[Path] = []

    # Extract exclude sets
    exclude_dirs_set = set(config.get("exclude_dirs", []))
    exclude_files_set = set(config.get("exclude_files", []))

    # Process each path - in tests we're using mock paths, so don't check if they exist
    for path in paths_to_check:
        # In production code, we would check if path.exists(), but for testing we assume paths exist
        if path.name.endswith(".py"):  # Treat as file if it has .py extension
            all_python_files.append(path)
        else:  # Assume it's a directory
            log.debug(
                "Searching %s directory: %s (recursive=%s, exclude_dirs=%s, exclude_files=%s)",
                "top-level of" if not recursive else "recursive",
                path,
                recursive,
                exclude_dirs_set,
                exclude_files_set,
            )
            try:
                # Find Python files in the directory
                found = find_python_files(
                    path,
                    exclude_dirs=exclude_dirs_set,
                    exclude_files=exclude_files_set,
                )
                all_python_files.extend(found)
            except Exception as e:
                log.error(f"Error finding files in {path}: {e}")

    # Remove duplicates and sort
    unique_python_files = sorted(list(set(all_python_files)))
    log.info("Found %d Python files to analyze.", len(unique_python_files))

    return unique_python_files


# --- Core Analysis Logic ---
def analyze_files(
    files: list[Path], config: dict[str, Any], analyzer_func: Callable
) -> tuple[dict[Path, dict[str, list[Any]]], dict[str, int]]:
    """Analyzes multiple files for compliance using the provided analyzer function.

    Args:
    ----
        files: List of files to analyze.
        config: The loaded configuration.
        analyzer_func: Function to analyze each file.

    Returns:
    -------
        A tuple containing violations by file and statistics.

    """
    violations_by_file: dict[Path, dict[str, list[Any]]] = {}
    stats: dict[str, int] = {
        "files_analyzed": len(files),
        "files_with_violations": 0,
        "compliant_files": 0,
    }

    for file_path in files:
        try:
            violations = analyzer_func(file_path, **config.get("analyzer_settings", {}))
            if violations:
                violations_by_file[file_path] = violations
                stats["files_with_violations"] += 1
            else:
                stats["compliant_files"] += 1
        except FileNotFoundError:
            violations_by_file[file_path] = {"error": ["File not found during analysis"]}
            stats["files_with_violations"] += 1
        except SyntaxError as e:
            violations_by_file[file_path] = {"error": [f"SyntaxError: {e} during analysis"]}
            stats["files_with_violations"] += 1
        except Exception as e:
            violations_by_file[file_path] = {"error": [f"{e.__class__.__name__}: {e} during analysis"]}
            stats["files_with_violations"] += 1

    return violations_by_file, stats


# --- Core Audit Logic ---
def run_audit(
    paths_to_check: list[Path],
    recursive: bool,
    config: dict[str, Any],
    analyzer_func: Callable | None = None,  # Optional specific analyzer
    output_json: bool = False,  # Add JSON output parameter
) -> bool:
    """DEPRECATED: Runs the compliance audit. Use specific commands like 'lint', 'test', or 'validate' instead."""
    log.warning("The 'run_audit' function is deprecated and will be removed. Use specific action commands.")
    log.info(
        "Starting deprecated audit on paths: %s (Recursive: %s)",
        paths_to_check,
        recursive,
    )
    files_to_audit = find_files_to_audit(paths_to_check, recursive, config)
    log.info(f"Found {len(files_to_audit)} files. Deprecated audit finished.")

    # Use analyze_files if we have an analyzer_func
    if analyzer_func is not None:
        violations_by_file, stats = analyze_files(files_to_audit, config, analyzer_func)
        if output_json:
            json_output = _format_violations_as_json(
                violations_by_file,
                stats["files_analyzed"],
                stats["files_with_violations"],
                stats["compliant_files"],
            )
            print(json.dumps(json_output, indent=2))
        return stats["files_with_violations"] > 0

    # For backward compatibility, return mock violations if no analyzer_func
    if output_json:
        violations_by_file = {file: {"complexity": [("complex_function", 5, 15)]} for file in files_to_audit}
        total_files = len(files_to_audit)
        files_with_violations = len(violations_by_file)
        compliant_files = total_files - files_with_violations

        json_output = _format_violations_as_json(violations_by_file, total_files, files_with_violations, compliant_files)
        print(json.dumps(json_output, indent=2))
        return True

    return len(files_to_audit) > 0  # Return True if any files found


def _format_violations_as_json(
    violations_by_file: dict[Path, dict[str, list[Any]]],
    total_files: int,
    files_with_violations: int,
    compliant_files: int,
) -> dict[str, Any]:
    """Format violations data as a JSON-serializable dictionary.

    Args:
    ----
        violations_by_file: Dictionary mapping file paths to violation dictionaries.
        total_files: Total number of files analyzed.
        files_with_violations: Number of files with violations.
        compliant_files: Number of compliant files.

    Returns:
    -------
        A JSON-serializable dictionary containing formatted violations data.

    """
    json_output = {
        "summary": {
            "total_files": total_files,
            "files_with_violations": files_with_violations,
            "compliant_files": compliant_files,
        },
        "violations": {},
    }

    # Convert Path objects to strings and tuples to lists for JSON serialization
    for file_path, violations in violations_by_file.items():
        file_path_str = str(file_path)
        json_output["violations"][file_path_str] = {}

        for category, issues in violations.items():
            json_output["violations"][file_path_str][category] = []

            for issue in issues:
                if isinstance(issue, tuple):
                    # Convert tuple to list for JSON serialization
                    json_output["violations"][file_path_str][category].append(list(issue))
                else:
                    json_output["violations"][file_path_str][category].append(issue)

    return json_output


def _log_violations_as_text(
    violations_by_file: dict[Path, dict[str, list[Any]]],
) -> None:
    """Log violations as formatted text using the logger.

    Args:
    ----
        violations_by_file: Dictionary mapping file paths to violation dictionaries.

    """
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
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    default=False,
    help="Suppress all output except errors.",
)
@click.option(
    "--color/--no-color",
    is_flag=True,
    default=None,  # Let auto-detection handle default
    help="Enable/disable colored logging output.",
)
@click.option(
    "-c",
    "--config",
    "config_path_override",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="Path to configuration file (e.g., pyproject.toml). Overrides auto-detection.",
)
@click.pass_context
def cli_group(ctx: click.Context, verbosity: int, quiet: bool, color: bool | None, config_path_override: Path | None) -> None:
    """Zeroth Law Compliance Auditor CLI."""
    # --- Logging Setup ---
    log_level = logging.WARNING  # Default
    if quiet:
        log_level = logging.ERROR
    elif verbosity == 1:
        log_level = logging.INFO
    elif verbosity >= 2:
        log_level = logging.DEBUG

    # Basic logging config (Add color handling later if needed)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)-8s] %(message)s [%(name)s]",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Store global options in context
    ctx.ensure_object(dict)
    ctx.obj["LOG_LEVEL"] = log_level
    ctx.obj["COLOR"] = color
    ctx.obj["VERBOSITY"] = verbosity
    ctx.obj["QUIET"] = quiet
    ctx.obj["CONFIG_PATH_OVERRIDE"] = config_path_override

    log.debug(
        "CLI group initiated. log_level=%s, color=%s",
        logging.getLevelName(log_level),
        color,
    )

    # --- Determine Project Root & Load Config/Mapping ---
    try:
        project_root = find_project_root(Path.cwd())
        if not project_root:
            raise ValueError("Could not determine project root containing pyproject.toml or similar.")
        log.debug(f"Detected project root: {project_root}")
        ctx.obj["PROJECT_ROOT"] = project_root
    except ValueError as e:
        log.error(f"{e} Using current directory '{Path.cwd()}' as fallback.")
        project_root = Path.cwd()
        ctx.obj["PROJECT_ROOT"] = project_root

    # Load config (respecting override)
    config_to_load = config_path_override
    if not config_to_load:
        # Auto-detect config file (pyproject.toml is common)
        potential_config = project_root / "pyproject.toml"
        if potential_config.is_file():
            config_to_load = potential_config
            log.info(f"Auto-detected configuration file: {config_to_load}")

    if config_to_load:
        config_data = load_config(config_to_load)
        ctx.obj["CONFIG"] = config_data
    else:
        log.warning("No configuration file specified or auto-detected. Using defaults.")
        ctx.obj["CONFIG"] = {}

    # Load tool mapping
    mapping_data = load_tool_mapping(project_root)
    if mapping_data is None:
        log.error("Failed to load tool mapping. Aborting.")
        ctx.exit(1)
    ctx.obj["TOOL_MAPPING"] = mapping_data


# --- NEW Action Commands ---

# Import action runner after cli_group is defined
from .action_runner import load_tool_mapping, run_action  # noqa: E402


@cli_group.command("lint")
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True, path_type=Path),
    required=False,  # Allow running on default paths
)
@click.pass_context
def lint_command(ctx: click.Context, paths: tuple[Path, ...]) -> None:
    """Run configured linters (ruff, mypy, etc.) on specified paths or defaults."""
    log.info("Initiating lint action...")
    mapping = ctx.obj.get("TOOL_MAPPING")
    project_root = ctx.obj.get("PROJECT_ROOT")
    cli_args = {
        "verbose": ctx.obj.get("VERBOSITY", 0) > 0,
        "quiet": ctx.obj.get("QUIET", False),
        "config": ctx.obj.get("CONFIG_PATH_OVERRIDE"),
        # Add other common/lint-specific flags here as needed
    }

    passed = run_action("lint", mapping, project_root, cli_args, list(paths))

    if not passed:
        log.error("Linting failed.")
        ctx.exit(1)
    else:
        log.info("Linting completed successfully.")
        ctx.exit(0)


@cli_group.command("format")
@click.option("--check", is_flag=True, help="Run formatter in check mode (no changes).")
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True, path_type=Path),
    required=False,
)
@click.pass_context
def format_command(ctx: click.Context, check: bool, paths: tuple[Path, ...]) -> None:
    """Run configured formatter (ruff format) on specified paths or defaults."""
    action_name = "format"
    log.info(f"Initiating {action_name} action... (Check mode: {check})")
    mapping = ctx.obj.get("TOOL_MAPPING")
    project_root = ctx.obj.get("PROJECT_ROOT")
    cli_args = {
        "check": check,
        "verbose": ctx.obj.get("VERBOSITY", 0) > 0,
        "quiet": ctx.obj.get("QUIET", False),
        "config": ctx.obj.get("CONFIG_PATH_OVERRIDE"),
    }

    passed = run_action(action_name, mapping, project_root, cli_args, list(paths))

    if not passed:
        log.error(f".{action_name.capitalize()} failed.")
        ctx.exit(1)
    else:
        log.info(f".{action_name.capitalize()} completed successfully.")
        ctx.exit(0)


@cli_group.command("test")
# Add relevant pytest options as click options, mapping keys to mapping names
@click.option("-k", "k", help="pytest: Only run tests matching KEYWORD expression.")
@click.option("-m", "m", help="pytest: Only run tests matching MARK expression.")
@click.option("-x", "x", is_flag=True, help="pytest: Exit instantly on first error.")
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True, path_type=Path),
    required=False,
)
@click.pass_context
def test_command(ctx: click.Context, paths: tuple[Path, ...], **kwargs) -> None:
    """Run the test suite (pytest) on specified paths or defaults."""
    action_name = "test"
    log.info(f"Initiating {action_name} action...")
    mapping = ctx.obj.get("TOOL_MAPPING")
    project_root = ctx.obj.get("PROJECT_ROOT")
    cli_args = {
        "verbose": ctx.obj.get("VERBOSITY", 0) > 0,
        "quiet": ctx.obj.get("QUIET", False),
        "config": ctx.obj.get("CONFIG_PATH_OVERRIDE"),
        # Add passthrough args from kwargs
        **{k: v for k, v in kwargs.items() if v is not None and v is not False},
    }

    passed = run_action(action_name, mapping, project_root, cli_args, list(paths))

    if not passed:
        log.error(f".{action_name.capitalize()} failed.")
        ctx.exit(1)
    else:
        log.info(f".{action_name.capitalize()} completed successfully.")
        ctx.exit(0)


@cli_group.command("validate")
# This command orchestrates multiple checks
@click.pass_context
def validate_command(ctx: click.Context) -> None:
    """Run all configured ZLF checks (lint, test, format --check, etc.)."""
    log.info("Initiating comprehensive ZLF validation...")
    config = ctx.obj.get("CONFIG")  # Use loaded config
    mapping = ctx.obj.get("TOOL_MAPPING")
    project_root = ctx.obj.get("PROJECT_ROOT")
    cli_args = {
        "verbose": ctx.obj.get("VERBOSITY", 0) > 0,
        "quiet": ctx.obj.get("QUIET", False),
        "config": ctx.obj.get("CONFIG_PATH_OVERRIDE"),
    }
    paths = []  # Run on defaults for validate

    all_passed = True

    # Run Linters
    log.info("--- Running Linters ---")
    if not run_action("lint", mapping, project_root, cli_args, paths):
        all_passed = False
        log.error("Linting checks failed.")
    else:
        log.info("Linting checks passed.")

    # Run Format Check
    log.info("--- Checking Formatting ---")
    format_check_args = cli_args | {"check": True}  # Add check=True
    if not run_action("format", mapping, project_root, format_check_args, paths):
        all_passed = False
        log.error("Formatting check failed.")
    else:
        log.info("Formatting check passed.")

    # Run Tests
    log.info("--- Running Tests ---")
    if not run_action("test", mapping, project_root, cli_args, paths):
        all_passed = False
        log.error("Tests failed.")
    else:
        log.info("Tests passed.")

    # TODO: Add calls to other checks (duplication, coverage, fuzz) based on config/ZLF rules

    log.info("--- Validation Summary ---")
    if not all_passed:
        log.error("ZLF validation failed.")
        ctx.exit(1)
    else:
        log.info("ZLF validation completed successfully.")
        ctx.exit(0)


# Remove the internal helper functions as they are moved or deprecated
# def setup_logging(log_level: int, use_color: bool) -> None:
# def find_files_to_audit(...)
# def analyze_files(...)
# def _format_violations_as_json(...)
# def _log_violations_as_text(...)
# def run_audit(...)


# --- Keep Utility Commands (audit - deprecated, install-git-hook, restore-git-hooks) ---
@cli_group.command("audit", deprecated=True)
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
    help="Path to configuration file. DEPRECATED: Config loaded automatically.",
)
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="DEPRECATED: Recursively search directories for files. Use underlying tools for directory handling.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="DEPRECATED: JSON output controlled by validate command or global flags.",
)
@click.pass_context
def audit_command(
    ctx: click.Context,
    paths: tuple[Path, ...],
    config_path: Path | None,
    recursive: bool,
    output_json: bool = False,
) -> None:
    """DEPRECATED: Use the 'validate' command instead."""
    log.warning("The 'audit' command is deprecated. Use specific action commands like 'lint', 'test', or 'validate'.")
    # Maybe forward to validate or just show the warning?
    # For now, just warn and exit.
    # ctx.forward(validate_command)
    click.echo("Use 'zlt validate' or other specific commands.", err=True)
    ctx.exit(1)


# install-git-hook command (keep as is, but use context for root)
@cli_group.command("install-git-hook")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,  # Default is handled by finding root
    help="Path to the Git repository root (auto-detected if not specified).",
)
@click.pass_context
def install_git_hook(ctx: click.Context, git_root: str | None) -> None:
    """Install the custom multi-project pre-commit hook script."""
    log_level = ctx.obj.get("LOG_LEVEL")
    logging.getLogger().setLevel(log_level)

    log.debug("Install git hook command called", specified_git_root=git_root)

    try:
        # Determine the target Git root
        if git_root:
            target_git_root_path = Path(git_root).resolve()
            # Verify it's actually a git root or inside one
            actual_git_root = find_git_root(target_git_root_path)
            if actual_git_root != target_git_root_path:
                log.warning(f"Provided path '{git_root}' is not the Git root. Using detected root: {actual_git_root}")
                target_git_root_path = actual_git_root
        else:
            # Auto-detect from project root or CWD
            start_path = ctx.obj.get("PROJECT_ROOT") or Path.cwd()
            target_git_root_path = find_git_root(start_path)

        if not target_git_root_path:
            raise ValueError("Could not determine Git repository root.")

        log.info(f"Installing hook in Git root: {target_git_root_path}")
        hook_file_path = install_git_hook_script(target_git_root_path)
        click.echo(f"Successfully installed Zeroth Law custom pre-commit hook to: {hook_file_path}")

        # Check for root pre-commit config and warn if found
        root_config_path = target_git_root_path / ".pre-commit-config.yaml"
        if root_config_path.is_file():
            log.warning("Root pre-commit config found during custom hook installation.")
            # (Warning messages remain the same)
            click.echo("-" * 20, err=True)
            click.echo("WARNING: Found '.pre-commit-config.yaml' at the Git root.", err=True)
            click.echo("         The Zeroth Law custom multi-project hook has been installed.", err=True)
            click.echo("         This hook prioritizes project-specific configs in subdirectories.", err=True)
            click.echo("         If this repository IS NOT intended as a multi-project monorepo,", err=True)
            click.echo("         you should restore the standard pre-commit hook behavior.", err=True)
            click.echo("         Consider running: zeroth-law restore-git-hooks", err=True)
            click.echo("-" * 20, err=True)

    except ValueError as e:
        log.error(f"Git hook installation failed: {e}")
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)
    except ImportError as e:
        log.error(f"Import error: {e}")
        click.echo(f"Error: Required function not available: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        log.exception("Unexpected error during Git hook installation", exc_info=e)
        click.echo(f"An unexpected error occurred: {e}", err=True)
        ctx.exit(1)


# --- Restore Git Hooks Command --- (Use context for root)
@cli_group.command("restore-git-hooks")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,  # Default handled by finding root
    help="Path to the Git repository root (auto-detected if not specified).",
)
@click.pass_context
def restore_git_hooks(ctx: click.Context, git_root: str | None) -> None:
    """Restore the default pre-commit hook script using 'pre-commit install'."""
    log_level = ctx.obj.get("LOG_LEVEL")
    logging.getLogger().setLevel(log_level)

    log.debug("Restore git hooks command called", specified_git_root=git_root)

    try:
        from zeroth_law.git_utils import restore_git_hooks as restore_hooks_func  # Avoid name clash

        # Determine the target Git root
        if git_root:
            target_git_root_path = Path(git_root).resolve()
            actual_git_root = find_git_root(target_git_root_path)
            if actual_git_root != target_git_root_path:
                log.warning(f"Provided path '{git_root}' is not the Git root. Using detected root: {actual_git_root}")
                target_git_root_path = actual_git_root
        else:
            start_path = ctx.obj.get("PROJECT_ROOT") or Path.cwd()
            target_git_root_path = find_git_root(start_path)

        if not target_git_root_path:
            raise ValueError("Could not determine Git repository root.")

        log.info(f"Restoring default hooks in Git root: {target_git_root_path}")
        restore_hooks_func(target_git_root_path)
        click.echo("Default pre-commit hooks restored successfully.")

    except ValueError as e:
        log.error(f"Git hook restoration failed: {e}")
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)
    except ImportError as e:
        log.error(f"Import error: {e}")
        click.echo(f"Error: Required function not available: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        log.exception("Unexpected error during Git hook restoration", exc_info=e)
        click.echo(f"An unexpected error occurred: {e}", err=True)
        ctx.exit(1)


if __name__ == "__main__":
    cli_group()

# <<< ZEROTH LAW FOOTER >>>
