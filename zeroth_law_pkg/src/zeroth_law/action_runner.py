# FILE: src/zeroth_law/action_runner.py
"""Handles the execution of underlying developer tools based on mapping."""

# import logging # Remove standard logging
import os
import subprocess
from pathlib import Path
from typing import Any
import structlog  # Import structlog

log = structlog.get_logger()  # Use structlog

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
                    log.debug(
                        f"No specific tool_arg for value option '{zlt_opt_name}' in '{tool_name}', appending value directly."
                    )
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
            log.debug(
                f"Tool '{tool_name}' requires path option '{path_option_key}', but no paths were provided. Adding no path arguments."
            )

    return path_args


def _prepare_environment(tool_name: str, project_root: Path) -> dict[str, str]:
    """Prepares environment variables, returning a modifiable copy."""
    # Always start with a copy of the current environment
    env_vars = os.environ.copy()

    if tool_name == "mypy":
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
            # If src not found, MYPYPATH remains unchanged in the copied env

    # Future: Add logic for other tools requiring specific env vars here

    return env_vars  # Always return the (potentially modified) copy


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

        # Handle output/logging based on output_json flag from cli_args
        output_json_flag = cli_args.get("output_json", False)
        stdout = result.stdout.strip()

        if output_json_flag:
            if stdout:  # Only print if there is something to print
                print(stdout)  # Print raw output for JSON flag
        else:
            if stdout:
                log.info(f"Output:\n{stdout}")  # Log output for non-JSON flag
            else:
                log.info("Tool produced no output.")

        if result.returncode != 0:
            tool_passed = False
            log.error(f"Tool '{tool_name}' failed (Exit Code: {result.returncode}) - captured above")
            # Error details logged previously
        elif cli_args.get("verbose", 0) > 0 or cli_args.get("verbosity", 0) > 0:
            # Verbose logging already happened via debug logs
            if result.stderr:
                log.info(f"Tool '{tool_name}' stderr (already debug logged): {result.stderr.strip()}")

    except FileNotFoundError:
        log.error(
            f"Execution failed for tool '{tool_name}': 'poetry' command not found. Is Poetry installed and in PATH?"
        )
        tool_passed = False
    except Exception as e:
        log.exception(f"Unexpected error executing tool '{tool_name}'", exc_info=e)
        tool_passed = False

    return tool_passed


def run_action(
    action_name: str,
    action_config: dict[str, Any],  # Config for the specific action being run
    project_root: Path,
    cli_args: dict[str, Any],  # Args passed to ZLT (keys = zlt_option names)
    paths: list[Path],
) -> bool:
    """Runs the specified action by executing underlying tools based on the action's config.

    Args:
    ----
        action_name: The name of the action to run (e.g., 'format', 'lint').
        action_config: The configuration dictionary for the specific action, loaded from pyproject.toml.
                       Expected structure: {"description": ..., "zlt_options": ..., "tools": ...}
        project_root: The root directory of the project.
        cli_args: Dictionary of parsed command-line arguments/options for the zlt command.
                  Keys should match the option names defined in zlt_options.
        paths: List of target file/directory paths provided.

    Returns:
    -------
        True if all underlying tool executions were successful, False otherwise.

    """
    log.info(f"Running action: {action_name} with args: {cli_args} on paths: {paths}")

    # Extract necessary parts from action_config
    action_tools = action_config.get("tools")
    zlt_options_config = action_config.get("zlt_options", {})  # Needed for building args

    if not action_tools or not isinstance(action_tools, dict):
        log.error(f"No valid 'tools' defined for action '{action_name}' in configuration.")
        return False

    overall_success = True

    # Iterate through tools defined for this action
    for tool_name, tool_config in action_tools.items():
        if not isinstance(tool_config, dict):
            log.warning(f"Skipping invalid tool configuration for '{tool_name}' in action '{action_name}'.")
            continue

        base_command_list = tool_config.get("command")
        maps_options = tool_config.get("maps_options", {})

        if not base_command_list or not isinstance(base_command_list, list):
            log.warning(f"Skipping tool '{tool_name}' due to missing or invalid 'command' list.")
            continue
        if not isinstance(maps_options, dict):
            log.warning(f"Invalid 'maps_options' for tool '{tool_name}'. Assuming no option mapping.")
            maps_options = {}

        log.debug(f"Processing tool: {tool_name} with base command: {base_command_list}")

        # Build arguments based on zlt options and tool's mapping
        tool_args = _build_tool_arguments(
            maps_options=maps_options,
            zlt_options=zlt_options_config,
            cli_args=cli_args,
            tool_name=tool_name,
        )

        # Build path arguments
        path_args = _build_path_arguments(
            tool_maps_options=maps_options,  # Pass the specific tool's map
            zlt_options_config=zlt_options_config,  # Pass the action's definitions
            paths=paths,
            project_root=project_root,
            tool_name=tool_name,
        )

        # Combine base command, mapped arguments, and path arguments
        command_to_run = base_command_list + tool_args + path_args

        log.info(f"Executing command for '{tool_name}': {' '.join(command_to_run)}")

        # Prepare environment (e.g., for mypy)
        env_vars = _prepare_environment(tool_name, project_root)

        # Execute the tool
        tool_passed = _execute_tool(command_to_run, project_root, env_vars, tool_name, cli_args)
        if not tool_passed:
            overall_success = False
            # Decide whether to continue with other tools or stop on first failure
            # For now, continue executing all tools defined for the action
            log.error(f"Tool '{tool_name}' failed for action '{action_name}'. Continuing...")

    return overall_success


# <<< ZEROTH LAW FOOTER >>>
