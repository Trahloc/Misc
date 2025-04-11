# FILE: src/zeroth_law/action_runner.py
"""Handles the execution of underlying developer tools based on mapping."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, cast

import yaml

log = logging.getLogger(__name__)

# Constants
# MAPPING_FILE_NAME = "tool_mapping.json" # Keep commented out or remove definition if defined elsewhere
YAML_MAPPING_FILE_NAME = "tool_mapping.yaml"  # New constant for YAML


def _build_tool_arguments(
    maps_options: dict[str, str | None],  # Tool's map: {zlt_opt_name: tool_arg_string | None}
    zlt_options: dict[str, Any],  # Action's zlt_options for type info
    cli_args: dict[str, Any],  # Arguments passed to zlt command
    tool_name: str,
) -> list[str]:
    """Builds tool arguments using the tool's maps_options and action's zlt_options."""
    tool_args = []
    # Iterate through the ZLT options provided in the zlt command call
    for zlt_opt_name, cli_value in cli_args.items():
        # Skip verbosity if not explicitly mapped?
        # Or handle global args separately? For now, assume it might be mapped.
        # if zlt_opt_name == "verbosity": continue

        # Check if this tool maps this ZLT option
        if zlt_opt_name in maps_options:
            tool_arg_string = maps_options[zlt_opt_name]
            zlt_opt_config = zlt_options.get(zlt_opt_name, {})  # Get type info
            option_type = zlt_opt_config.get("type")

            # Handle based on type defined in zlt_options
            if option_type == "flag":
                # Add the tool's flag string if the zlt flag was True
                if cli_value is True and tool_arg_string:
                    tool_args.append(tool_arg_string)
            elif option_type == "value":
                # Add the tool's argument string and the value
                if tool_arg_string:
                    tool_args.append(tool_arg_string)
                    tool_args.append(str(cli_value))
                else:
                    # If tool_arg_string is null/empty, maybe it takes value positionally?
                    # This needs careful handling based on tool behavior.
                    # For now, just append the value if no tool_arg specified.
                    log.debug(f"No specific tool_arg for value option '{zlt_opt_name}' in '{tool_name}', appending value directly.")
                    tool_args.append(str(cli_value))
            # Ignore 'positional' type here, handled by _build_path_arguments
            # Ignore unknown types

        # else: Option provided to zlt but not mapped for this tool - ignore it

    return tool_args


def _build_path_arguments(
    tool_maps_options: dict[str, Any],  # Tool's specific option map
    zlt_options_config: dict[str, Any],  # Action's option definitions
    paths: list[Path],  # User-provided paths
    project_root: Path,
    tool_name: str,
) -> list[str]:
    """Builds the list of path arguments for the tool command."""
    path_args: list[str] = []

    # Check if the tool accepts positional paths or needs a specific option
    path_option_key = tool_maps_options.get("paths")

    if path_option_key is None:  # Tool accepts positional paths (value is null in YAML)
        if paths:
            # Use user-provided paths, convert to strings WITHOUT resolving
            path_args.extend([str(p) for p in paths])
            log.debug(f"Using user-provided paths for '{tool_name}': {path_args}")
        else:
            # No user paths, check for defaults defined in the action's zlt_options
            action_path_config = zlt_options_config.get("paths")
            default_paths = []
            if isinstance(action_path_config, dict):
                default_paths = action_path_config.get("default", [])

            if default_paths and isinstance(default_paths, list):
                # Use default paths (expecting strings), WITHOUT resolving
                path_args.extend([str(p) for p in default_paths])
                log.debug(f"Using default paths for '{tool_name}': {path_args}")
            else:
                # No user paths and no valid defaults, use project root as fallback
                log.debug(f"No user paths or valid default paths found for '{tool_name}'. Using project root.")
                # Use project root as string, try to make relative to CWD
                try:
                    relative_project_root = project_root.relative_to(Path.cwd())
                    path_args.append(str(relative_project_root))
                except ValueError:
                    # If not relative (e.g., different drive), use absolute path
                    path_args.append(str(project_root))

    elif path_option_key:  # Tool uses a specific option (e.g., --files)
        if paths:
            # Use user-provided paths with the specific option
            path_args.append(path_option_key)
            # Convert paths to strings WITHOUT resolving
            path_args.extend([str(p) for p in paths])
            log.debug(f"Using paths '{paths}' with option '{path_option_key}' for '{tool_name}'")
        else:
            # No user paths provided. Should we use defaults here too?
            # For now, if a tool requires a specific option, and no paths are given,
            # we add neither the option nor any paths.
            # TODO: Consider if default paths should be used with the specific option.
            log.debug(f"Tool '{tool_name}' requires path option '{path_option_key}', but no paths were provided. Adding no path arguments.")

    return path_args


def _prepare_environment(tool_name: str, project_root: Path) -> dict[str, str] | None:
    """Prepares environment variables for specific tools (e.g., MYPYPATH for mypy)."""
    env_vars: dict[str, str] | None = None  # Start with None (use default os.environ)

    if tool_name == "mypy":
        # Create a copy of the current environment only if we need to modify it
        env_vars = os.environ.copy()
        current_mypypath = env_vars.get("MYPYPATH", "")
        src_path = project_root / "src"

        if src_path.is_dir():
            src_path_str = str(src_path.resolve())
            if current_mypypath:
                # Prepend src path, ensuring separation
                env_vars["MYPYPATH"] = f"{src_path_str}{os.pathsep}{current_mypypath}"
            else:
                env_vars["MYPYPATH"] = src_path_str
            log.debug(f"Set MYPYPATH for mypy execution: {env_vars['MYPYPATH']}")
        else:
            log.warning(f"'src' directory not found at {src_path}. Cannot automatically set MYPYPATH for mypy.")
            # If src not found, don't modify the environment, revert to default
            env_vars = None

    # Future: Add logic for other tools requiring specific env vars here

    return env_vars


def _execute_tool(
    command_to_run: list[str],
    project_root: Path,
    env_vars: dict[str, str] | None,
    tool_name: str,  # For logging
    cli_args: dict[str, Any],  # For verbose logging check
) -> bool:
    """Executes the tool command using subprocess and handles results."""
    tool_passed = True
    try:
        result = subprocess.run(
            command_to_run,
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False,
            encoding="utf-8",
            env=env_vars,
        )
        log.debug(f"Tool {tool_name} exited with code {result.returncode}")

        if result.returncode != 0:
            tool_passed = False
            log.error(f"Tool '{tool_name}' failed (Exit Code: {result.returncode}):")
            if result.stdout:
                log.error("--- stdout ---")
                log.error(result.stdout.strip())
            if result.stderr:
                log.error("--- stderr ---")
                log.error(result.stderr.strip())
        elif cli_args.get("verbose", 0) > 0 or cli_args.get("verbosity", 0) > 0:
            if result.stdout:
                log.info(f"--- stdout ({tool_name}) ---")
                log.info(result.stdout.strip())
            if result.stderr:
                log.info(f"--- stderr ({tool_name}) ---")
                log.info(result.stderr.strip())

    except FileNotFoundError:
        log.error(f"Execution failed for tool '{tool_name}': 'poetry' command not found. Is Poetry installed and in PATH?")
        tool_passed = False
    except Exception as e:
        log.exception(f"Unexpected error executing tool '{tool_name}'", exc_info=e)
        tool_passed = False

    return tool_passed


def load_tool_mapping(project_root: Path) -> dict[str, Any] | None:
    """Loads the tool mapping configuration from the YAML file."""
    # Construct path relative to project root (assuming src layout)
    mapping_file_path = project_root / "src" / "zeroth_law" / YAML_MAPPING_FILE_NAME  # Use YAML constant
    log.debug(f"Attempting to load tool mapping from: {mapping_file_path}")

    if not mapping_file_path.is_file():
        log.error(f"Tool mapping file '{YAML_MAPPING_FILE_NAME}' not found at expected location: {mapping_file_path}")
        return None

    try:
        with mapping_file_path.open("r", encoding="utf-8") as f:
            # mapping_data = json.load(f) # Old JSON loading
            mapping_data = yaml.safe_load(f)  # Use yaml.safe_load
        log.debug("Successfully loaded tool mapping.")
        # Cast to the expected type to satisfy the linter
        return cast(dict[str, Any], mapping_data)
    # except json.JSONDecodeError as e: # Old JSON error handling
    #     log.error(f"Error decoding JSON from {mapping_file_path}: {e}")
    #     return None
    except yaml.YAMLError as e:  # Use YAML error handling
        log.error(f"Error parsing YAML from {mapping_file_path}: {e}")
        return None
    except OSError as e:
        log.error(f"Error reading tool mapping file {mapping_file_path}: {e}")
        return None


def run_action(
    action_name: str,
    mapping: dict[str, Any],  # Full mapping loaded from YAML
    project_root: Path,
    cli_args: dict[str, Any],  # Args passed to ZLT (keys = zlt_option names)
    paths: list[Path],
) -> bool:
    """Runs the specified action by executing underlying tools based on the mapping.

    Args:
    ----
        action_name: The name of the action to run (e.g., 'format', 'lint').
        mapping: The loaded tool mapping dictionary.
        project_root: The root directory of the project.
        cli_args: Dictionary of parsed command-line arguments/options for the zlt command.
                  Keys should match the option names defined in the mapping (e.g., 'check', 'verbose').
        paths: List of target file/directory paths provided.

    Returns:
    -------
        True if all underlying tool executions were successful, False otherwise.

    """
    log.info(f"Running action: {action_name} with args: {cli_args} on paths: {paths}")

    if action_name not in mapping:
        log.error(f"Action '{action_name}' not found in tool mapping.")
        return False

    action_config = mapping[action_name]
    zlt_options_config = action_config.get("zlt_options", {})  # Get action's option definitions
    all_tools_passed = True

    for tool_name, tool_config in action_config.get("tools", {}).items():
        log.debug(f"Preparing to run tool: {tool_name}")

        base_command = tool_config.get("command", [])
        if not base_command:
            log.error(f"No base command defined for tool '{tool_name}' in mapping.")
            all_tools_passed = False
            continue

        # Get the tool's specific mapping configuration
        tool_maps_options = tool_config.get("maps_options", {})

        # Build arguments using the tool's mapping and the action's definitions
        tool_args = _build_tool_arguments(tool_maps_options, zlt_options_config, cli_args, tool_name)

        # Build path arguments
        path_args = _build_path_arguments(tool_maps_options, zlt_options_config, paths, project_root, tool_name)

        # Combine command parts
        command_to_run = ["poetry", "run"] + base_command + tool_args + path_args

        log.info(f"Executing: {' '.join(command_to_run)}")

        # Prepare environment variables (e.g., MYPYPATH for mypy)
        env_vars = _prepare_environment(tool_name, project_root)

        # Execute the tool and handle results
        if not _execute_tool(command_to_run, project_root, env_vars, tool_name, cli_args):
            all_tools_passed = False
            # Decide on error handling: break or continue?
            # For now, let's continue to run other tools even if one fails,
            # but ensure the overall action result reflects the failure.
            # If poetry itself is not found, _execute_tool handles logging and returns False,
            # which will set all_tools_passed = False. We can add a break here if needed.
            if "poetry" in command_to_run and "command not found" in locals().get("e", ""):
                # Check if the error was FileNotFoundError for poetry
                # This check is a bit fragile, relying on exception message content.
                # A better approach might involve custom exceptions from _execute_tool.
                log.critical("Poetry command not found. Aborting action.")
                break

    return all_tools_passed


# <<< ZEROTH LAW FOOTER >>>
