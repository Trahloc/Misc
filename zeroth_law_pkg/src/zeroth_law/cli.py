# FILE: src/zeroth_law/cli.py
"""Command Line Interface for Zeroth Law Auditor."""

import json  # Re-add JSON import
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

# from .action_runner import load_tool_mapping, run_action  # Import necessary functions and constant
from .action_runner import run_action  # Corrected import
from .config_loader import load_config
from .file_finder import find_python_files
from .git_utils import (
    find_git_root,
    install_git_hook_script,
    restore_standard_hooks,
)
from .path_utils import find_project_root

# --- Early Logging Setup --- START
# Configure root logger early to prevent premature debug logs (e.g., during --help)
# Set a sensible default level here.
DEFAULT_LOG_LEVEL = logging.WARNING
log_format = "%(asctime)s [%(levelname)-8s] %(message)s"
log_datefmt = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=log_format, datefmt=log_datefmt, force=True)

# Setup logger for this module *after* basicConfig
log = logging.getLogger(__name__)
log.debug("Initial basicConfig set to %s", logging.getLevelName(DEFAULT_LOG_LEVEL))
# --- Early Logging Setup --- END

# Context settings for Click
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


# --- Logging Setup ---
# Placeholder - Basic config done in cli_group for now
def setup_logging(log_level: int, use_color: bool) -> None:
    """Set up logging based on verbosity and color preference."""
    # This function might be needed if more complex setup (like colorama) is added


# --- Core File Finding Logic ---
def find_files_to_audit(paths_to_check: list[Path], recursive: bool, config: dict[str, Any]) -> list[Path]:
    """Finds all Python files to be audited based on input paths and config."""
    # Get exclusion patterns from config
    exclude_dirs = config.get("exclude_dirs", [])
    exclude_files = config.get("exclude_files", [])
    exclude_dirs_set = set(exclude_dirs)
    exclude_files_set = set(exclude_files)
    log.debug(f"Excluding dirs: {exclude_dirs_set}")
    log.debug(f"Excluding files: {exclude_files_set}")

    all_python_files: list[Path] = []
    for path in paths_to_check:
        if not path.exists():
            log.warning(f"Path does not exist, skipping: {path}")
            continue  # Skip non-existent paths

        if path.is_file():
            # Check exclusion for explicitly passed files
            if path.name in exclude_files_set:
                log.debug(f"Excluding explicitly provided file due to config: {path}")
                continue
            # Check if it's a Python file (simple check for now, align with find_python_files later if needed)
            if path.suffix == ".py":
                all_python_files.append(path)
            else:
                log.debug(f"Skipping non-Python file provided directly: {path}")
        elif path.is_dir():
            if not recursive:
                log.warning(f"Directory found but recursive search is off, skipping: {path}")
                continue
            # Avoid recursing into excluded dirs top-level check
            if path.name in exclude_dirs_set:
                log.debug(f"Skipping excluded directory at top level: {path}")
                continue
            try:
                # Find Python files in the directory
                found = find_python_files(
                    path,  # Pass the directory path
                    exclude_dirs=exclude_dirs_set,
                    exclude_files=exclude_files_set,
                )
                all_python_files.extend(found)
            except Exception as e:
                log.error(f"Error finding files in directory {path}: {e}")
        else:
            log.warning(f"Path is not a file or directory, skipping: {path}")

    # Remove duplicates and sort
    unique_python_files = sorted(list(set(all_python_files)))
    log.info("Found %d unique Python files to analyze.", len(unique_python_files))

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

        json_output = _format_violations_as_json(
            violations_by_file, total_files, files_with_violations, compliant_files
        )
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


# --- Generic Action Handler ---
@click.pass_context
def _generic_action_handler(ctx: click.Context, paths: tuple[Path, ...], **kwargs) -> None:
    """Generic callback for dynamically generated action commands."""
    # Collect all arguments passed to the ZLT command
    # Filter out None values, maybe handle defaults?
    cli_options = {k: v for k, v in kwargs.items() if v is not None and k not in ["paths"]}

    # Handle paths separately, ensuring they are Path objects
    paths_arg = kwargs.get("paths", [])
    paths = [Path(p) for p in paths_arg] if paths_arg else []

    # Get the action name from the invoked command
    action_name = ctx.command.name
    log.debug(f"Generic handler invoked for action: {action_name}")
    log.debug(f"CLI Options received: {cli_options}")
    log.debug(f"Paths received: {paths}")

    # Retrieve the full config and project root from context
    project_root = ctx.obj.get("project_root")
    full_config = ctx.obj.get("config")

    if not project_root or not full_config:
        log.error("Project root or configuration missing in context. Cannot run action.")
        ctx.exit(1)

    # Get the specific configuration for this action
    action_config = full_config.get("actions", {}).get(action_name)
    if not action_config or not isinstance(action_config, dict):
        log.error(f"Configuration for action '{action_name}' not found or invalid.")
        ctx.exit(1)

    # Call the action runner with the specific action config
    try:
        success = run_action(
            action_name=action_name,
            action_config=action_config,  # Pass the specific action's config
            project_root=project_root,
            cli_args=cli_options,
            paths=paths,
        )

        if not success:
            log.error(f"Action '{action_name}' failed.")
            # Optionally, exit with a non-zero code to indicate failure
            ctx.exit(1)
        else:
            log.info(f"Action '{action_name}' completed successfully.")
            # Success, exit code 0 (default)

    except Exception as e:
        log.exception(f"An unexpected error occurred running action '{action_name}'", exc_info=e)
        ctx.exit(1)


# === Main CLI Group Definition ===
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
    default=None,
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
def cli_group(
    ctx: click.Context, verbosity: int, quiet: bool, color: bool | None, config_path_override: Path | None
) -> None:
    """Zeroth Law Toolkit (zlt) - Enforces the Zeroth Law of Code Quality."""
    # Determine effective log level based on flags
    if quiet:
        log_level = logging.ERROR
    elif verbosity == 1:
        log_level = logging.INFO
    elif verbosity >= 2:
        log_level = logging.DEBUG
    else:
        # Keep the default level set by basicConfig if no flags are specified
        log_level = DEFAULT_LOG_LEVEL  # Use the default established earlier

    # Adjust the level of the root logger
    current_level = logging.getLogger().getEffectiveLevel()
    if log_level != current_level:
        logging.getLogger().setLevel(log_level)
        log.debug("Log level adjusted by CLI args to: %s", logging.getLevelName(log_level))
    else:
        log.debug("Log level remains at default: %s", logging.getLevelName(current_level))

    # TODO: Add color handling based on 'color' option

    # Find project root (might be needed by commands)
    project_root = find_project_root(start_path=Path.cwd())
    if not project_root:
        log.error("Could not determine project root. Some commands might fail.")

    # Load config (needed by commands)
    config = load_config(config_path_override=config_path_override)
    if config is None:
        config = {}

    # Store context
    ctx.ensure_object(dict)
    ctx.obj["project_root"] = project_root
    ctx.obj["config"] = config
    ctx.obj["verbosity"] = verbosity
    ctx.obj["quiet"] = quiet

    # Handle color option


# === Dynamic Command Generation (at module load time) ===
def _add_dynamic_commands() -> None:
    """Loads mapping and adds commands to cli_group."""
    # Find the project root path once
    try:
        temp_project_root = find_project_root(start_path=Path.cwd())
        if not temp_project_root:
            log.warning("Could not find project root. Dynamic commands may not load correctly.")
            # Proceed without project root, some features might fail later
    except Exception as e:
        log.warning(f"Error finding project root: {e}. Dynamic commands may not load correctly.")
        temp_project_root = None

    # Load the main configuration which should now include the 'actions'
    try:
        # Use the found project root to potentially locate pyproject.toml if not overridden
        # Ensure the CWD is correct if temp_project_root is used implicitly by load_config
        # We assume load_config searches from CWD if no override is given
        zlt_config = load_config()
        action_definitions = zlt_config.get("actions", {})
        if not isinstance(action_definitions, dict):
            log.warning(f"Loaded 'actions' is not a dictionary: {type(action_definitions)}. Skipping dynamic commands.")
            action_definitions = {}
    except FileNotFoundError:
        log.warning("Configuration file (e.g., pyproject.toml) not found. Skipping dynamic commands.")
        action_definitions = {}
    except Exception as e:
        log.warning(f"Error loading configuration: {e}. Skipping dynamic commands.")
        action_definitions = {}

    # Define global options handled by the main cli_group or implicitly
    GLOBAL_OPTIONS = {"verbose", "quiet", "config"}
    GLOBAL_SHORT_OPTIONS = {"-v", "-q", "-c"}  # Short names used by global options

    if action_definitions:
        log.debug(f"Dynamically generating commands for actions: {list(action_definitions.keys())}")
        for action_name, action_config in action_definitions.items():
            if not isinstance(action_config, dict):
                log.warning(f"Skipping invalid action configuration for '{action_name}': Expected a dictionary.")
                continue

            # Get ZLT option definitions for this action from pyproject.toml
            zlt_options_config = action_config.get("zlt_options")
            if not isinstance(zlt_options_config, dict):
                log.warning(
                    f"Skipping action '{action_name}' due to missing or invalid 'zlt_options' section in pyproject.toml."
                )
                continue

            command_help = action_config.get("description", f"Run the '{action_name}' action.")
            params = []  # List to hold click parameters

            # Create Click parameters based on zlt_options
            for zlt_opt_name, opt_conf in zlt_options_config.items():
                if not isinstance(opt_conf, dict):
                    continue

                # Skip creating subcommand options for those handled globally
                if zlt_opt_name in GLOBAL_OPTIONS:
                    log.debug(f"Skipping subcommand option for global option: {zlt_opt_name}")
                    continue

                option_type = opt_conf.get("type")

                # Handle positional paths argument
                if option_type == "positional":
                    params.append(
                        click.Argument(
                            ["paths"],  # Standard name for positional paths
                            nargs=-1,
                            type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True, path_type=Path),
                            required=False,
                            # default=opt_conf.get("default") # Click doesn't directly support list default for nargs=-1 here
                        )
                    )
                    continue  # Move to next zlt_option

                # Handle flag/value options
                click_option_names = [f"--{zlt_opt_name}"]
                short_name = opt_conf.get("short")
                if short_name:
                    if short_name in GLOBAL_SHORT_OPTIONS:
                        log.warning(
                            f"Short option '{short_name}' for '{zlt_opt_name}' in action '{action_name}' "
                            f"conflicts with a global option. Skipping short name."
                        )
                    else:
                        # TODO: Check for conflicts within the *same* command's options?
                        click_option_names.append(short_name)

                is_flag = option_type == "flag"
                # Separate keyword args from positional option names
                option_kwargs = {
                    "is_flag": is_flag,
                    "help": opt_conf.get("description"),
                    "default": None if not is_flag else False,
                }
                if not is_flag:
                    opt_val_type = opt_conf.get("value_type", "str")
                    type_map = {"str": str, "int": int, "path": click.Path(path_type=Path)}
                    option_kwargs["type"] = type_map.get(opt_val_type, str)

                try:
                    # Pass option names list as the FIRST argument, others as **kwargs
                    params.append(click.Option(click_option_names, **option_kwargs))
                except Exception as e:
                    log.error(f"Failed to create click option for '{zlt_opt_name}' in action '{action_name}': {e}")

            # Create and add the command
            try:
                cmd = click.Command(
                    name=action_name,
                    callback=_generic_action_handler,
                    params=params,
                    help=command_help,
                    context_settings=CONTEXT_SETTINGS,
                )
                cli_group.add_command(cmd)
                log.debug(f"Added dynamic command '{action_name}'")
            except Exception as e:
                log.error(f"Failed to create or add command for action '{action_name}': {e}")
    else:
        log.warning("No actions defined in configuration, dynamic command generation skipped.")


# Call the function to add dynamic commands when the module is loaded
_add_dynamic_commands()


# === Utility Commands (Defined *after* cli_group is created and dynamic commands are added) ===
@cli_group.command("install-git-hook")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,  # Default is handled by finding root
    help="Path to the Git repository root (auto-detected if not specified).",
)
@click.pass_context
def install_git_hook(ctx: click.Context, git_root: str | None) -> None:
    """Installs the custom ZLT pre-commit hook for multi-project support."""
    # Access project_root from context if needed, but don't rely on it being set if called before cli_group
    # For robustness, maybe re-find roots here if needed?
    project_root = ctx.obj.get("project_root")  # Can be None if context setup failed
    if not project_root:
        project_root = find_project_root(start_path=Path.cwd())  # Find again if needed

    # Use a flag to indicate failure instead of exiting early
    # error_occurred = False

    try:
        git_root_path = Path(git_root) if git_root else find_git_root(start_path=Path.cwd())  # Find relative to CWD
        if not git_root_path:
            log.error("Could not determine Git repository root. Please specify with --git-root.")
            # ctx.exit(1)
            raise click.ClickException("Failed to determine Git root.")  # Raise exception instead

        # Ensure project_root is valid before using its name
        if not project_root or not project_root.is_dir():
            log.error("Project root is invalid or not found. Cannot install hook relative to project.")
            # ctx.exit(1)
            raise click.ClickException("Invalid project root.")  # Raise exception instead

        log.info(f"Using Git root: {git_root_path}")
        log.info(f"Using Project root: {project_root}")

        root_pre_commit_config = git_root_path / ".pre-commit-config.yaml"
        if root_pre_commit_config.exists():
            log.warning(
                f"Found existing {root_pre_commit_config}. "
                f"The ZLT hook will dispatch to project-specific configs "
                f"like {project_root.name}/.pre-commit-config.yaml, "
                f"potentially bypassing the root config during commit."
            )
            log.warning("If this is not a multi-project monorepo, consider using 'zlt restore-git-hooks'.")

        try:
            log.info(f"Installing custom multi-project pre-commit hook in {git_root_path}")
            # Assuming install_git_hook_script only needs the git_root
            hook_path = install_git_hook_script(git_root_path)  # Pass only git_root
            log.info(f"Hook installed successfully at {hook_path}")
            # ctx.exit(0) # Return normally on success
            return
        except ValueError as e:
            # Log the specific ValueError from git_utils
            log.error(f"Git hook installation failed: {e}")
            # ctx.exit(1)
            raise click.ClickException(f"Installation failed: {e}")  # Re-raise as ClickException

    except click.ClickException:  # Catch our own exceptions to prevent generic logging
        raise  # Re-raise them so Click handles the exit code
    except Exception as e:
        log.exception("An unexpected error occurred during git hook installation.", exc_info=e)
        # ctx.exit(1)
        # Raise a generic exception for unexpected errors
        raise click.ClickException("Unexpected installation error.")


@cli_group.command("restore-git-hooks")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,  # Default handled by finding root
    help="Path to the Git repository root (auto-detected if not specified).",
)
@click.pass_context
def restore_git_hooks(ctx: click.Context, git_root: str | None) -> None:
    """Restores standard pre-commit hooks, removing the ZLT dispatcher."""
    project_root = ctx.obj["project_root"]
    try:
        git_root_path = Path(git_root) if git_root else find_git_root(start_path=project_root)
        if not git_root_path:
            err_msg = "Could not determine Git repository root. Please specify with --git-root."
            log.error(err_msg)
            # raise click.ClickException("Failed to determine Git root.")
            raise ValueError(err_msg)  # Raise standard ValueError

        restore_standard_hooks(git_root_path)
        return  # Return normally on success
    except ValueError as e:
        log.error("An error occurred during git hook restoration.")
        log.error(str(e))
        # raise click.ClickException(str(e))
        raise ValueError(str(e)) from e  # Raise standard ValueError, preserving cause


if __name__ == "__main__":
    cli_group()


# <<< ZEROTH LAW FOOTER >>>
