import subprocess
import structlog
import sys
from pathlib import Path
from typing import List, Dict, Any, Sequence

log = structlog.get_logger()


def build_tool_command_arguments(
    tool_definition: Dict[str, Any],
    zlt_options_activated: Dict[str, Any],
    target_files_for_tool: List[Path],
) -> List[str]:
    """Builds the final list of arguments to execute a tool based on activated ZLT options.

    Args:
        tool_definition: The loaded JSON definition dict for the selected tool.
        zlt_options_activated: A dictionary representing the ZLT options passed
                               on the command line (keys are canonical option names,
                               values are their values, e.g., True for flags).
        target_files_for_tool: The list of specific file paths this tool instance
                               should operate on.

    Returns:
        A list of strings representing the command and arguments to be executed.
        Returns an empty list if the base command sequence is missing.
    """
    base_command = tool_definition.get("command_sequence")
    if not base_command or not isinstance(base_command, list):
        log.error(
            f"Tool definition is missing 'command_sequence': {tool_definition.get('metadata', {}).get('tool_name')}"
        )
        return []

    final_args: List[str] = list(base_command)  # Start with the base command
    processed_zlt_options: set[str] = set()

    tool_options = tool_definition.get("options", {})
    tool_arguments = tool_definition.get("arguments", {})

    # 1. Process Tool Options based on ZLT Activated Options
    for tool_opt_name, tool_opt_def in tool_options.items():
        maps_to = tool_opt_def.get("maps_to_zlt_option")
        if not maps_to:
            continue  # This tool option doesn't map to a ZLT option

        zlt_opt_value = zlt_options_activated.get(maps_to)

        if zlt_opt_value is not None:  # Check if the ZLT option was provided
            option_type = tool_opt_def.get("type")
            if option_type == "flag" and zlt_opt_value is True:
                final_args.append(tool_opt_name)
                processed_zlt_options.add(maps_to)
            elif option_type == "value":
                # Append the tool's flag and then the value provided to ZLT
                final_args.append(tool_opt_name)
                final_args.append(str(zlt_opt_value))  # Ensure value is string
                processed_zlt_options.add(maps_to)
            # Add handling for other types if needed

    # 2. Process Tool Arguments (mainly for 'paths')
    for tool_arg_name, tool_arg_def in tool_arguments.items():
        maps_to = tool_arg_def.get("maps_to_zlt_option")
        if maps_to == "paths":
            # Append the target files relevant to this tool execution
            # Convert Path objects to strings
            final_args.extend([str(p) for p in target_files_for_tool])
            processed_zlt_options.add(maps_to)
            # Assume only one argument maps to 'paths'
            break

    # TODO: Add logic for handling default behaviors from metadata if needed
    # e.g., if zlt_options_activated['recursive'] is True but no tool option
    # maps to it, check metadata for default recursive behavior.

    log.debug(f"Built command arguments: {final_args}")
    return final_args


def run_tool_command():
    # Placeholder for the function that will actually execute the command
    # It would likely take the result from build_tool_command_arguments
    # and use subprocess.run or similar.
    pass
