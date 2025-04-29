# FILE: src/zeroth_law/cli.py
"""Command Line Interface for Zeroth Law Auditor."""

import json
import structlog
import sys
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, List, Optional
from importlib.metadata import version, PackageNotFoundError

import click

from zeroth_law.action_runner import run_action
from zeroth_law.common.config_loader import load_config
from zeroth_law.file_processor import find_files_to_audit
from zeroth_law.common.git_utils import (
    find_git_root,
    get_staged_files,
    identify_project_roots_from_files,
)
from zeroth_law.common.path_utils import find_project_root

# Add import for analysis functions
from zeroth_law.analysis_runner import (
    analyze_files,
    format_violations_as_json,
    log_violations_as_text,
    run_all_checks,
)

# Import the dynamic command function
# from zeroth_law.dynamic_commands import add_dynamic_commands # Might remove if not used

# Import the Git hook commands
from .subcommands.git_hooks import install_git_hook, restore_git_hooks

# Import the new Audit command
from .subcommands.audit.audit import audit

# Import the pre-commit analyzer
from zeroth_law.analyzers.precommit_analyzer import analyze_precommit_config

# Import the new tools group
from .subcommands.tools.tools import tools_group

# Import the new definition group
# from .subcommands.definition.definition import definition_group # <-- REMOVE THIS IMPORT

# --- Early Structlog Setup --- START
# Configure structlog early with basic console output
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Use ConsoleRenderer for initial setup, might be adjusted later based on flags
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Define default log level equivalent (using structlog levels implicitly handled by filtering later)
DEFAULT_LOG_LEVEL_NAME = "warning"  # Use names for clarity

# Get the logger using structlog
log = structlog.get_logger()
log.debug("Initial structlog configuration applied.")
# --- Early Structlog Setup --- END

# --- Determine Version ---
try:
    zlt_version = version("zeroth-law")
except PackageNotFoundError:
    zlt_version = "unknown"  # Fallback if package is not installed properly

# Context settings for Click
CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "ignore_unknown_options": True,
    "allow_interspersed_args": False,
}

# --- Path to dynamic options definitions ---
OPTIONS_DEF_PATH = Path(__file__).parent / "zlt_options_definitions.json"


# --- Helper to load option definitions ---
def load_zlt_option_definitions() -> Dict[str, Dict[str, Any]]:
    """Loads the canonical ZLT option definitions from JSON."""
    if not OPTIONS_DEF_PATH.is_file():
        log.error(f"ZLT options definition file not found: {OPTIONS_DEF_PATH}")
        return {}
    try:
        with open(OPTIONS_DEF_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error(f"Error decoding ZLT options definitions file {OPTIONS_DEF_PATH}: {e}")
        return {}
    except Exception as e:
        log.exception(f"Unexpected error loading ZLT options definitions {OPTIONS_DEF_PATH}: {e}")
        return {}


# --- Helper to create Click option from definition ---
def create_click_option_from_def(name: str, definition: Dict[str, Any]) -> click.Option:
    """Creates a Click Option object from a definition dictionary."""
    param_decls = definition.get("cli_names", [f"--{name}"])  # Default to --name if cli_names missing
    option_type = definition.get("type", "flag")
    opts = {
        "help": definition.get("description", ""),
        "default": definition.get("default"),  # Pass default if defined
    }

    if option_type == "flag":
        opts["is_flag"] = True
    elif option_type == "value":
        value_type_str = definition.get("value_type")
        click_type = click.STRING  # Default
        if value_type_str == "path":
            click_type = click.Path(path_type=Path)
        elif value_type_str == "integer":
            click_type = click.INT
        # Add more type mappings as needed
        opts["type"] = click_type
        opts["metavar"] = definition.get("value_name")  # Use value_name for metavar
    elif option_type == "positional":
        # Note: Positional arguments are handled differently (click.Argument)
        # This helper might need splitting or adjustment for arguments.
        # For now, assuming global options are not positional.
        raise ValueError(f"Positional argument definition '{name}' cannot be created as a global Click Option.")
    else:
        raise ValueError(f"Unknown option type '{option_type}' for option '{name}'")

    # Remove None values from opts to avoid passing them to click.Option
    opts = {k: v for k, v in opts.items() if v is not None}

    return click.Option(param_decls, **opts)


# --- Logging Setup Function (May need adjustment for structlog) ---
def setup_structlog_logging(level_name: str, use_color: bool | None) -> None:
    """Set up structlog logging based on level and color preference."""
    # Map level names to standard logging level numbers
    level_map = {
        "debug": 10,
        "info": 20,
        "warning": 30,
        "error": 40,
        "critical": 50,  # Add critical just in case
    }
    # Use WARNING (30) as default if level_name is unknown
    level_num = level_map.get(level_name.lower(), 30)

    # Reconfigure structlog based on CLI args
    # TODO: Add more sophisticated configuration based on flags
    # For now, just set the minimum level filter on the underlying stdlib logger
    # This requires getting the actual root logger configured by structlog
    # Note: structlog doesn't directly set the level, it relies on stdlib filtering
    stdlib_root_logger = logging.getLogger()  # Get the standard lib root logger
    stdlib_root_logger.setLevel(level_num)

    # TODO: Implement color handling
    # Maybe swap ConsoleRenderer based on `use_color`
    log.debug(
        "Structlog logging level filter adjusted (via stdlib) to %s (%d)",
        level_name.upper(),
        level_num,
    )


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


# === CLI Group Factory Function ===
def create_cli_group() -> click.Group:
    """Factory to create the main CLI group with dynamically added options."""

    option_defs = load_zlt_option_definitions()

    # Define the base function for the group *without* static options
    @click.group(context_settings=CONTEXT_SETTINGS)
    @click.version_option(version=zlt_version, package_name="zeroth-law", prog_name="zeroth-law")
    @click.pass_context
    def base_cli_group(ctx: click.Context, **kwargs) -> None:
        """Zeroth Law Toolkit (zlt) - Enforces the Zeroth Law of Code Quality."""

        # Extract values from kwargs passed by Click based on dynamic options
        verbosity = kwargs.get("verbose", 0)  # Using canonical names
        quiet = kwargs.get("quiet", False)
        color = kwargs.get("color")  # Allow None for color
        config_path_override = kwargs.get("config")

        # Determine effective log level name based on flags
        if quiet:
            level_name = "error"
        elif verbosity == 1:
            level_name = "info"
        elif verbosity >= 2:
            level_name = "debug"
        else:
            level_name = DEFAULT_LOG_LEVEL_NAME

        # Setup/Adjust structlog logging based on determined level and color option
        setup_structlog_logging(level_name, color)

        # Find project root (might be needed by commands)
        project_root = find_project_root(start_path=Path.cwd())
        if not project_root:
            log.error("Could not determine project root. Some commands might fail.")

        # Load config (needed by commands)
        config_data = load_config(config_path_override=config_path_override)
        if config_data is None:
            log.warning("No valid configuration found. Dynamic commands may not be available.")
            config_data = {}  # Use empty config if none found

        # Store context
        ctx.ensure_object(dict)
        ctx.obj["project_root"] = project_root
        ctx.obj["config"] = config_data
        # Store all dynamic options in context as well for potential use by subcommands
        ctx.obj["options"] = kwargs

        log.debug("CLI context prepared", options=kwargs)

    # Dynamically add options to the base_cli_group function's parameters
    # We reverse the definitions so options are added in a consistent order (like top-to-bottom in file)
    dynamic_options: List[click.Option] = []
    for name, definition in reversed(option_defs.items()):
        if definition.get("type") != "positional":  # Skip positional for global options
            try:
                option = create_click_option_from_def(name, definition)
                dynamic_options.append(option)
            except ValueError as e:
                log.warning(f"Skipping dynamic option '{name}': {e}")

    # Add the dynamically created options to the command
    # Modifying __click_params__ is one way, but applying decorators is cleaner if possible.
    # Let's try modifying the params list directly before the group is finalized.
    base_cli_group.params.extend(dynamic_options)

    # Add the subcommands (this happens after the group is created)
    base_cli_group.add_command(audit)
    base_cli_group.add_command(install_git_hook)
    base_cli_group.add_command(restore_git_hooks)
    base_cli_group.add_command(tools_group)  # Add the tools subcommand group
    # base_cli_group.add_command(definition_group) # <-- REMOVE THIS REGISTRATION

    # TODO: Add dynamic commands based on capabilities/mapping later
    # add_dynamic_commands(base_cli_group)

    return base_cli_group


# === Create the CLI instance using the factory ===
main = create_cli_group()

# === Entry Point ===
if __name__ == "__main__":
    main()


# <<< ZEROTH LAW FOOTER >>>
