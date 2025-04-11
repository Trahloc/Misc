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
    mapping: dict[str, Any],
    project_root: Path,
    cli_args: dict[str, Any],
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
    all_tools_passed = True

    for tool_name, tool_config in action_config.get("tools", {}).items():
        log.debug(f"Preparing to run tool: {tool_name}")

        base_command = tool_config.get("command", [])
        if not base_command:
            log.error(f"No base command defined for tool '{tool_name}' in mapping.")
            all_tools_passed = False
            continue

        # Build arguments based on mapping and cli_args
        tool_args = []
        mapped_options = tool_config.get("options", {})

        for zlt_option_name, tool_option_config in mapped_options.items():
            if tool_option_config is None:  # Option explicitly not supported by this tool
                continue

            # Check if the zlt option was provided in cli_args (and is not False for flags)
            # Note: Click passes False for flags not provided, None for non-flag options not provided.
            # We only add the arg if the key exists AND its value is truthy (or not None for value types).
            if zlt_option_name in cli_args and cli_args[zlt_option_name] is not None and cli_args[zlt_option_name] is not False:
                option_type = tool_option_config.get("type")
                tool_arg_name = tool_option_config.get("tool_arg")
                is_passthrough = tool_option_config.get("passthrough", False)

                # Handle passthrough options directly
                if is_passthrough and tool_arg_name:
                    if option_type == "flag":
                        # Ensure flag value is True before adding
                        if cli_args[zlt_option_name] is True:
                            tool_args.append(tool_arg_name)
                    elif option_type == "value":
                        tool_args.append(tool_arg_name)
                        tool_args.append(str(cli_args[zlt_option_name]))
                    continue  # Move to next option after handling passthrough

                # Handle mapped options
                if option_type == "flag":
                    # Ensure flag value is True before adding
                    if tool_arg_name and cli_args[zlt_option_name] is True:
                        tool_args.append(tool_arg_name)
                elif option_type == "value":
                    if tool_arg_name:
                        # Ensure cli_args[zlt_option_name] is not boolean True for value type
                        if isinstance(cli_args[zlt_option_name], bool):
                            log.warning(f"Boolean value passed for value option '{zlt_option_name}' for tool '{tool_name}'. Ignoring.")
                        else:
                            tool_args.append(tool_arg_name)
                            tool_args.append(str(cli_args[zlt_option_name]))
                # Note: Positional type is handled separately after loop

        # Combine command parts
        # Use poetry run for executing tools within the project environment
        command_to_run = ["poetry", "run"] + base_command + tool_args

        # Add paths: check if tool expects positional paths
        if "paths" in mapped_options and mapped_options["paths"].get("type") == "positional":
            # Use provided paths, or default if none provided and default exists
            effective_paths = paths if paths else mapped_options["paths"].get("default", [])
            command_to_run.extend([str(p) for p in effective_paths])
        elif paths and not any(opt is not None and opt.get("type") == "positional" for opt in mapped_options.values()):
            # If paths provided but no positional mapping found for any option
            log.warning(f"Paths provided but tool '{tool_name}' mapping doesn't specify positional path handling. Ignoring paths: {paths}")

        log.info(f"Executing: {' '.join(command_to_run)}")
        try:
            # Set MYPYPATH environment variable specifically for mypy
            env_vars: dict[str, str] | None = None  # Initialize as None
            if tool_name == "mypy":
                env_vars = os.environ.copy()  # Create copy only for mypy
                # Prepend 'src' to MYPYPATH if it exists, otherwise set it
                current_mypypath = env_vars.get("MYPYPATH", "")
                # Ensure src path is correct relative to project_root
                src_path = project_root / "src"
                if src_path.is_dir():  # Check if src directory actually exists
                    src_path_str = str(src_path.resolve())
                    if current_mypypath:
                        env_vars["MYPYPATH"] = f"{src_path_str}{os.pathsep}{current_mypypath}"
                    else:
                        env_vars["MYPYPATH"] = src_path_str
                    log.debug(f"Set MYPYPATH to: {env_vars['MYPYPATH']}")
                else:
                    log.warning(f"'src' directory not found at {src_path}. Cannot set MYPYPATH.")
                    # Decide if we should proceed without MYPYPATH or treat as error?
                    # For now, proceed without modifying env_vars
                    env_vars = None  # Revert to None if src not found

            result = subprocess.run(
                command_to_run,
                capture_output=True,
                text=True,
                cwd=project_root,  # Run command from the project root
                check=False,  # Don't raise exception on non-zero exit
                encoding="utf-8",  # Specify encoding
                env=env_vars,  # Pass the modified environment
            )
            log.debug(f"Tool {tool_name} exited with code {result.returncode}")

            if result.returncode != 0:
                all_tools_passed = False
                log.error(f"Tool '{tool_name}' failed (Exit Code: {result.returncode}):")
                # Log stdout/stderr only if they contain something
                if result.stdout:
                    log.error("--- stdout ---")
                    log.error(result.stdout.strip())
                if result.stderr:
                    log.error("--- stderr ---")
                    log.error(result.stderr.strip())
            # Log output even on success if verbose (check cli_args directly)
            elif cli_args.get("verbose", 0) > 0 or cli_args.get("verbosity", 0) > 0:
                if result.stdout:
                    log.info(f"--- stdout ({tool_name}) ---")
                    log.info(result.stdout.strip())
                if result.stderr:
                    log.info(f"--- stderr ({tool_name}) ---")
                    log.info(result.stderr.strip())

        except FileNotFoundError:
            log.error("Execution failed: 'poetry' command not found. Is Poetry installed and in PATH?")
            all_tools_passed = False
            break  # Stop processing other tools if poetry isn't found
        except Exception as e:
            log.exception(f"Unexpected error executing tool '{tool_name}'", exc_info=e)
            all_tools_passed = False
            # Continue to next tool unless error is catastrophic

    return all_tools_passed


# <<< ZEROTH LAW FOOTER >>>
