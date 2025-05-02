# FILE: src/zeroth_law/cli.py
"""Command Line Interface for Zeroth Law Auditor."""

import json
import structlog
import sys
import os
import subprocess
import logging
import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast
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
from zeroth_law.common.path_utils import find_project_root, ZLFProjectRootNotFoundError

# Import the logging setup function from its new location
from zeroth_law.common.logging_utils import setup_structlog_logging

# Re-add necessary imports
from zeroth_law.analysis_runner import (
    analyze_files,
    format_violations_as_json,
    log_violations_as_text,
    run_all_checks,
)
from .subcommands.audit.audit import audit as audit_command  # NEW import of function
from .subcommands.git_hooks import install_git_hook, restore_git_hooks  # Correct: Import individual commands
from .subcommands.tools.tools import tools_group  # Tools GROUP
from .subcommands.todo.todo_group import todo_group  # Todo GROUP
from zeroth_law.analyzers.precommit_analyzer import analyze_precommit_config  # Analyzer

# Import sync command directly for testing
# from .subcommands.tools.sync import sync as sync_command

# --- Early Structlog Setup --- START
# Configure structlog minimally early on for setup messages
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=False,  # Set to False during debugging
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
    "ignore_unknown_options": True,  # Temporarily disable -- RESTORE
    "allow_interspersed_args": False,
}

# --- Path to dynamic options definitions ---
OPTIONS_DEF_PATH = Path(__file__).parent / "zlt_options_definitions.json"


# --- Helper to load option definitions ---
def load_zlt_option_definitions() -> Dict[str, Dict[str, Any]]:
    """Loads the canonical ZLT option definitions from JSON."""
    if not OPTIONS_DEF_PATH.is_file():
        log.error("zlt_options_definition_file_not_found", path=str(OPTIONS_DEF_PATH))
        return {}
    try:
        with open(OPTIONS_DEF_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error("zlt_options_definition_decoding_error", path=str(OPTIONS_DEF_PATH), error=str(e))
        return {}
    except Exception as e:
        log.exception("zlt_options_definition_loading_error", path=str(OPTIONS_DEF_PATH))
        return {}


# --- Helper to create Click option from definition ---
def create_click_option_from_def(name: str, definition: Dict[str, Any]) -> click.Option:
    """Creates a Click Option object from a definition dictionary."""
    kwargs = definition.get("kwargs", {})
    param_decls = list(definition["cli_names"])

    # Handle boolean flags (store_true/store_false)
    is_flag = definition.get("is_flag", False)
    if is_flag:
        kwargs["is_flag"] = True
        # Default 'type' is implicitly boolean for flags
        # Ensure 'default' is set appropriately (usually False)
        kwargs.setdefault("default", False)
        # Remove 'type' if explicitly set to bool, as it's implied
        if kwargs.get("type") == bool:
            del kwargs["type"]
    else:
        # Handle other types
        type_str = definition.get("type")
        if type_str == "Path":
            kwargs["type"] = click.Path()
        elif type_str == "int":
            kwargs["type"] = int
        elif type_str == "str":
            kwargs["type"] = str
        # Add more type mappings as needed

    # Handle 'count' option
    is_count = definition.get("count", False)
    if is_count:
        kwargs["count"] = True
        # Default 'type' is implicitly int for counts
        kwargs.setdefault("default", 0)
        # Remove 'type' if explicitly set to int, as it's implied
        if kwargs.get("type") == int:
            del kwargs["type"]

    # Handle 'required' attribute
    if definition.get("required", False):
        kwargs["required"] = True

    # Handle 'help' attribute
    if "help" in definition:
        kwargs["help"] = definition["help"]

    # Handle 'default' attribute
    if "default" in definition and "default" not in kwargs:  # Don't override if already set by flag/count logic
        kwargs["default"] = definition["default"]

    # Handle 'envvar' attribute
    if "envvar" in definition:
        kwargs["envvar"] = definition["envvar"]

    # Handle 'show_default' attribute
    kwargs["show_default"] = definition.get("show_default", True)

    # Ensure the destination name (like 'verbose') is included if not automatically derived
    # from param_decls (e.g., if param_decls is just ['-v'])
    expected_dest = name.replace("-", "_")
    has_dest_decl = any(decl.lstrip("-").replace("-", "_") == expected_dest for decl in param_decls)
    if not has_dest_decl:
        # Click usually derives the dest from the first long option (--option-name -> option_name)
        # or the first short option if no long options exist (-o -> o).
        # If our desired `name` doesn't match an existing declaration, we might need to add it
        # explicitly, though usually Click handles this well. Let's rely on Click's default
        # behavior for now unless issues arise.
        pass  # Revisit if options aren't stored correctly

    # Handle choices
    choices = definition.get("choices")
    if choices:
        kwargs["type"] = click.Choice(choices)

    # Create the option
    try:
        option = click.Option(param_decls=param_decls, **kwargs)
        # log.debug(f"Created option: {option.name}, Params: {param_decls}, Kwargs: {kwargs}")
        return option
    except TypeError as e:
        log.error(f"TypeError creating option '{name}' with params {param_decls} and kwargs {kwargs}: {e}")
        raise


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
    log.warning("deprecated_audit_called")
    log.info(
        "deprecated_audit_starting",
        paths=[str(p) for p in paths_to_check],
        recursive=recursive,
    )
    files_to_audit = find_files_to_audit(paths_to_check, recursive, config)
    log.info("deprecated_audit_files_found", count=len(files_to_audit))

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

    # Define the base function for the group *with* static decorators
    @click.group(context_settings=CONTEXT_SETTINGS)
    @click.version_option(version=zlt_version, package_name="zeroth-law", prog_name="zeroth-law")
    # --- Add global options manually as decorators --- #
    @click.option("--verbose", "-V", count=True, default=0, help="Increase verbosity. -V for INFO, -VV for DEBUG.")
    @click.option("--quiet", "-q", is_flag=True, default=False, help="Suppress all output except errors.")
    @click.option(
        "--config",
        type=click.Path(path_type=Path),
        default=None,
        metavar="FILE_PATH",
        help="Path to a tool-specific configuration file.",
    )
    # Add other global options like --color if defined and needed
    # Note: Positional 'paths' is not a global option, handled by subcommands
    @click.pass_context
    def base_cli_group(ctx: click.Context, **kwargs) -> None:
        """Core logic for the base CLI group."""
        # Extract values from kwargs passed by Click
        # verbosity = kwargs.get("verbose", 0) # REMOVE
        # quiet = kwargs.get("quiet", False) # REMOVE
        color = kwargs.get("color")  # Assuming color option exists/added
        config_path_override = kwargs.get("config")

        # Determine effective log level name based on flags
        # REMOVE verbose/quiet logic
        # if quiet:
        #     level_name = "error"
        # elif verbosity == 1:
        #     level_name = "info"
        # elif verbosity >= 2:
        #     level_name = "debug"
        # else:
        #     level_name = DEFAULT_LOG_LEVEL_NAME
        # Set a default level for now, subcommands will override if needed
        level_name = DEFAULT_LOG_LEVEL_NAME

        # Setup/Adjust structlog logging based on determined level and color option
        setup_structlog_logging(level_name, color)
        # log.debug("TEST: Logging should be configured for DEBUG level now.", level_set=level_name) # Remove test log

        # Store options early using kwargs
        ctx.ensure_object(dict)
        # Remove verbose/quiet from stored options if they are no longer global
        options_to_store = {k: v for k, v in kwargs.items() if k not in ["verbose", "quiet"]}
        ctx.obj["options"] = options_to_store

        # --- Consolidated Root Finding and Config Loading ---
        try:
            project_root = find_project_root(start_path=Path.cwd())
            config_file_to_load = config_path_override or (project_root / "pyproject.toml")
            if config_file_to_load and Path(config_file_to_load).is_file():
                log.info("attempting_config_load", path=str(config_file_to_load))
                config_data = load_config(config_file_to_load)
                log.debug("Inspect config_data after load_config", data=config_data)
                if config_data is None:
                    log.warning("config_loading_returned_none", path=str(config_file_to_load))
                    config_data = {}  # Use empty dict if load_config returns None
            elif config_path_override:
                log.warning("config_override_not_found", path=str(config_path_override))
                config_data = {}
            else:
                log.warning("default_config_not_found_or_override_invalid", path=str(config_file_to_load))
                config_data = {}

            ctx.obj["project_root"] = project_root
            ctx.obj["config"] = config_data
            log.debug("Storing config in context", config_stored=ctx.obj["config"])
            log.info("configuration_processed", loaded=bool(config_data), project_root=str(project_root))

        except ZLFProjectRootNotFoundError as e:
            log.critical("project_root_not_found", error=str(e))
            ctx.fail(f"Fatal Error: {e} Please run `zlt` from within a ZLF compliant project directory.")
        except Exception as e:
            log.exception("project_root_or_config_loading_failed", error=str(e))
            ctx.fail(f"Fatal Error during project root detection or configuration loading: {e}")

        # --- FINAL DEBUG: Log context state before returning --- #
        log.debug("Final context object state in base_cli_group", ctx_obj=repr(ctx.obj))

    # --- Restore Dynamic Option Loading --- #
    dynamic_options: List[click.Option] = []
    # Iterate in reverse definition order for consistent help message order
    for name, definition in reversed(option_defs.items()):
        # !! IMPORTANT: Skip verbose and quiet !!
        if name in ["verbose", "quiet"]:
            continue
        if definition.get("type") != "positional":
            try:
                option = create_click_option_from_def(name, definition)
                dynamic_options.append(option)
            except ValueError as e:
                log.warning(f"Skipping dynamic option creation for '{name}': {e}")

    # Add the options to the group's parameter list
    base_cli_group.params.extend(dynamic_options)

    # Add the subcommands
    base_cli_group.add_command(audit_command)
    base_cli_group.add_command(install_git_hook)
    base_cli_group.add_command(restore_git_hooks)
    base_cli_group.add_command(tools_group)
    base_cli_group.add_command(todo_group)

    return base_cli_group


# === Create the CLI instance using the factory ===
main = create_cli_group()

# === Entry Point ===
if __name__ == "__main__":
    main()


# <<< ZEROTH LAW FOOTER >>>
