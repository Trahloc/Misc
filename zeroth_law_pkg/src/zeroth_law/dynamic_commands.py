"""
Handles loading the tool index and dynamically generating Click commands.
"""

import json

# import logging # Remove standard logging
from pathlib import Path
from typing import Any, Dict, Callable, Optional, Type
import click
import importlib.resources  # Import importlib.resources
import structlog  # Import structlog

from zeroth_law.common.path_utils import find_project_root

# from zeroth_law.managed_tools import get_tool_mapping # Removed unused import
from zeroth_law.action_runner import run_action

log = structlog.get_logger()  # Use structlog

GLOBAL_OPTIONS = {"verbose", "quiet", "config"}
GLOBAL_SHORT_OPTIONS = {"-v", "-q", "-c"}


# --- Generic Action Handler --- (Remains the same - uses ctx.obj['config'])
@click.pass_context
def _generic_action_handler(ctx: click.Context, **kwargs) -> None:
    """Generic callback for dynamically generated action commands."""
    # Collect all arguments passed to the ZLT command
    # Filter out None values, maybe handle defaults?
    cli_options = {
        k: v for k, v in kwargs.items() if v is not None and k != "paths"
    }  # Ensure paths isn't included here

    # Handle paths separately, ensuring they are Path objects
    paths_arg = kwargs.get("paths", [])  # Get paths from kwargs directly
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

    # Get the specific configuration for this action from the main config
    action_config = full_config.get("actions", {}).get(action_name)
    if not action_config or not isinstance(action_config, dict):
        log.error(f"Configuration for action '{action_name}' not found or invalid in main config.")
        ctx.exit(1)

    # Call the action runner with the specific action config
    try:
        # Pass necessary context/config to run_action
        success = run_action(
            action_name=action_name,
            action_config=action_config,
            project_root=project_root,
            cli_args=cli_options,  # Pass filtered CLI options
            paths=paths,  # Pass processed paths
        )

        if not success:
            log.error(f"Action '{action_name}' failed.")
            ctx.exit(1)  # Exit with non-zero code for failure
        else:
            log.info(f"Action '{action_name}' completed successfully.")
            # ctx.exit(0) # Default exit code is 0

    except Exception as e:
        log.exception(f"An unexpected error occurred running action '{action_name}'", exc_info=e)
        ctx.exit(1)


# Modified function signature - accepts config again
def add_dynamic_commands(cli_group: click.Group, config: Dict[str, Any]) -> None:
    """
    Dynamically adds command stubs to the Click group based on actions defined
    in the provided configuration dictionary (typically from pyproject.toml).

    Args:
        cli_group: The main click.Group instance to add commands to.
        config: The loaded configuration dictionary containing the 'actions'.
    """
    log.debug("Attempting to add dynamic command stubs from configuration...")

    # --- Get actions from CONFIGURATION ---
    if not config or "actions" not in config or not isinstance(config.get("actions"), dict):
        log.warning("Configuration does not contain a valid 'actions' dictionary. No dynamic commands added.")
        return

    action_definitions = config["actions"]
    log.debug(f"Found {len(action_definitions)} actions in configuration.")

    # --- Loop through actions defined in CONFIG ---
    for action_id, action_config in action_definitions.items():
        if not isinstance(action_config, dict):
            log.warning(f"Skipping invalid action configuration in index for '{action_id}'.")
            continue

        log.debug(f"Defining command stub for action: {action_id}")
        help_text = action_config.get("description", f"Run the '{action_id}' action.")
        summary = action_config.get("summary", help_text.split(".")[0])

        # Define the standard parameters expected by the generic handler
        # These need to be defined here so Click knows about them for parsing.
        params = [
            click.Argument(
                ["paths"],
                nargs=-1,
                type=click.Path(exists=True, path_type=Path, readable=True),
                required=False,
            ),
            click.Option(
                ["-r", "--recursive"],
                is_flag=True,
                default=False,
                help="Recursively search directories.",
            ),
            click.Option(
                ["--output-json"],
                is_flag=True,
                default=False,
                help="Output results in JSON format.",
            ),
            # Add --fix flag, hidden status might depend on index info if available,
            # but handler ultimately checks config. Let's assume potentially supported.
            click.Option(
                ["--fix"],
                is_flag=True,
                default=False,
                help="Attempt to automatically fix issues (if supported).",
                hidden=False,  # Show by default, handler confirms support via config
            ),
            # Do NOT add action-specific options from zlt_options here.
            # The generic handler receives them via **kwargs if passed on cmd line,
            # and validation against actual config happens in action_runner.
        ]

        # --- Create and add the command stub ---
        try:
            cmd = click.Command(
                name=action_id,
                callback=_generic_action_handler,  # Use the generic handler
                params=params,  # Standard params only for the stub
                help=help_text,
                short_help=summary,
                # Pass ignore_unknown_options and allow_interspersed_args via context_settings
                context_settings={
                    "ignore_unknown_options": True,
                    "allow_interspersed_args": True,
                    # Add other context settings if needed
                },
                # Remove these arguments from direct call
                # ignore_unknown_options=True,
                # allow_interspersed_args=True,
            )
            # Check again before adding, just in case of race conditions (unlikely here)
            if action_id not in cli_group.commands:
                cli_group.add_command(cmd)
                log.debug(f"Added command stub: {action_id}")
            else:
                # This case should be hit by the earlier check, but log if it happens
                log.warning(f"Command '{action_id}' appeared in group between check and add. Skipping.")

        except Exception as e:
            log.error(f"Failed to create or add command stub for action '{action_id}': {e}")
