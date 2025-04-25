# FILE: src/zeroth_law/cli.py
"""Command Line Interface for Zeroth Law Auditor."""

import json
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, List

import click

from zeroth_law.action_runner import run_action
from zeroth_law.common.config_loader import load_config
from zeroth_law.file_processor import find_files_to_audit, process_files
from zeroth_law.exceptions import ConfigError, GitError
from zeroth_law import __version__ as zlt_version  # Get version from __init__
from zeroth_law.logging_utils import setup_logging, log_invocation
from zeroth_law.common.git_utils import find_git_root, get_staged_files, identify_project_roots_from_files
from zeroth_law.common.path_utils import find_project_root

# Add import for analysis functions
from zeroth_law.analysis_runner import (
    analyze_files,
    format_violations_as_json,
    log_violations_as_text,
    run_all_checks,
)

# Import the dynamic command function
from zeroth_law.dynamic_commands import add_dynamic_commands

# Import the Git hook commands
from zeroth_law.commands.git_hooks import install_git_hook, restore_git_hooks

# Import the new Audit command
from zeroth_law.commands.audit.audit import audit

# Import the pre-commit analyzer
from zeroth_law.analyzers.precommit_analyzer import analyze_precommit_config

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
# def find_files_to_audit(paths_to_check: list[Path], recursive: bool, config: dict[str, Any]) -> list[Path]:
#    ...


# --- Core Analysis Logic ---
# def analyze_files(...): ...
# def _format_violations_as_json(...): ...
# def _log_violations_as_text(...): ...


# --- Core Audit Logic --- (DEPRECATED)
def run_audit(
    paths_to_check: list[Path],
    recursive: bool,
    config: dict[str, Any],
    analyzer_func: Callable | None = None,
    output_json: bool = False,
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

    if analyzer_func is not None:
        # Calls should now use imported functions
        violations_by_file, stats = analyze_files(files_to_audit, config, analyzer_func)
        if output_json:
            json_output = format_violations_as_json(  # Renamed from _format_violations_as_json
                violations_by_file,
                stats["files_analyzed"],
                stats["files_with_violations"],
                stats["compliant_files"],
            )
            print(json.dumps(json_output, indent=2))
        else:
            # Optionally log text violations if not outputting JSON
            if stats["files_with_violations"] > 0:
                log_violations_as_text(violations_by_file)
        return stats["files_with_violations"] > 0

    # Backward compatibility mock violation output
    if output_json:
        violations_by_file = {file: {"complexity": [("complex_function", 5, 15)]} for file in files_to_audit}
        total_files = len(files_to_audit)
        files_with_violations = len(violations_by_file)
        compliant_files = total_files - files_with_violations

        json_output = format_violations_as_json(  # Renamed from _format_violations_as_json
            violations_by_file, total_files, files_with_violations, compliant_files
        )
        print(json.dumps(json_output, indent=2))
        return True  # Assume violation if outputting JSON for compat

    return len(files_to_audit) > 0


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
        log.warning("No valid configuration found. Dynamic commands may not be available.")
        config = {}  # Use empty config if none found

    # Store context
    ctx.ensure_object(dict)
    ctx.obj["project_root"] = project_root
    ctx.obj["config"] = config
    ctx.obj["verbosity"] = verbosity
    ctx.obj["quiet"] = quiet

    # === Add Commands AFTER config is loaded ===
    # Add dynamic commands based on the loaded config
    # Pass the group instance from the context and the loaded config
    if isinstance(ctx.command, click.Group):
        # Ensure config is passed to add_dynamic_commands
        add_dynamic_commands(cli_group=ctx.command, config=config)
    else:
        log.error("Internal error: Context command is not a Group, cannot add dynamic commands.")

    # Static commands are added below at module level


# === Utility Commands (Defined *after* cli_group is created) ===
# @cli_group.command("install-git-hook") ... def install_git_hook(...): ...
# @cli_group.command("restore-git-hooks") ... def restore_git_hooks(...): ...


# --- Add Commands to Group ---
# Call moved inside cli_group function
# add_dynamic_commands(cli_group)

# Add the static Git hook commands (Keep here, added to the group object directly)
cli_group.add_command(install_git_hook)
cli_group.add_command(restore_git_hooks)
# Add the audit command
cli_group.add_command(audit)


# === Standalone Audit Command (Phase 2/3 Goal) ===
# @cli_group.command("audit")
# @click.argument(
#     "paths",
# ... (Remove the entire audit function definition here) ...
#         exit_code = 2 # Use a different exit code for unexpected errors
#
#     # Finally, exit with the determined code
#     ctx.exit(exit_code)


# --- Main Execution Guard ---
if __name__ == "__main__":  # pragma: no cover
    cli_group()


# <<< ZEROTH LAW FOOTER >>>
