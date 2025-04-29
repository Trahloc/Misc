import structlog
from pathlib import Path
from typing import Dict, List, Any

log = structlog.get_logger()


def find_tool_for_capability_and_files(
    capability_needed: str,
    target_files: List[Path],
    available_definitions: Dict[str, Dict[str, Any]],
) -> Dict[Path, str | None]:
    """Finds the appropriate tool definition ID for each file based on capability and file type.

    Args:
        capability_needed: The canonical capability name (e.g., "Formatter").
        target_files: A list of file paths to find tools for.
        available_definitions: A dictionary where keys are tool definition IDs
                               and values are the loaded tool definition dicts.

    Returns:
        A dictionary mapping each target file Path to the ID (key) of the
        first matching tool definition found, or None if no match is found.
    """
    selected_tools: Dict[Path, str | None] = {}

    log.debug(f"Dispatcher looking for capability '{capability_needed}' for {len(target_files)} files.")

    for file_path in target_files:
        file_extension = file_path.suffix.lower()  # Use lower case for consistency
        if not file_extension:
            log.warning(f"Skipping file with no extension: {file_path}")
            selected_tools[file_path] = None
            continue

        log.debug(f"Processing file: {file_path} (extension: {file_extension})")
        match_found_for_file = False
        for tool_id, definition in available_definitions.items():
            metadata = definition.get("metadata", {})
            provided_caps = metadata.get("provides_capabilities", [])
            supported_types = metadata.get("supported_filetypes", [])

            log.debug(f"  Checking tool '{tool_id}': Caps={provided_caps}, Types={supported_types}")

            # Check capability
            if capability_needed not in provided_caps:
                log.debug(f"    Tool '{tool_id}' does not provide capability '{capability_needed}'.")
                continue

            # Check file type
            # Ensure supported_types are lowercased for comparison
            supported_types_lower = [t.lower() for t in supported_types]
            if "*" not in supported_types_lower and file_extension not in supported_types_lower:
                log.debug(f"    Tool '{tool_id}' does not support file type '{file_extension}'.")
                continue

            # Match found!
            log.info(f"  Match found for {file_path}: Tool '{tool_id}'")
            selected_tools[file_path] = tool_id
            match_found_for_file = True
            break  # Use the first match found for now

        if not match_found_for_file:
            log.warning(f"No tool found providing '{capability_needed}' for file type '{file_extension}' ({file_path})")
            selected_tools[file_path] = None

    return selected_tools
