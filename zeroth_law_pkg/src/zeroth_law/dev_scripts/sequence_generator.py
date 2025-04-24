"""Generates command sequences for a tool, including its subcommands."""

import logging
from typing import List, Tuple, Dict, Any, Set

log = logging.getLogger(__name__)

def _generate_sequence_id(parts: Tuple[str, ...]) -> str:
    """Helper to generate the underscore-separated ID for blacklist checking."""
    return "_".join(parts)

def generate_sequences_for_tool(
    tool_name: str,
    subcommands_detail: Dict[str, Any],
    blacklist: Set[str]
) -> List[Tuple[str, ...]]:
    """Generates a list of command sequence tuples for a given tool and its subcommands.

    Handles nested subcommands and filters based on the blacklist.

    Args:
        tool_name: The base name of the tool.
        subcommands_detail: The dictionary extracted from the tool's JSON
                           ('subcommands_detail' key), possibly nested.
        blacklist: A set of sequence IDs (e.g., 'tool_sub') to exclude.

    Returns:
        A list of command sequence tuples. Example: [('tool',), ('tool', 'sub')]
    """
    generated_sequences: List[Tuple[str, ...]] = []

    # Check if the base tool itself is blacklisted
    base_tool_id = _generate_sequence_id((tool_name,))
    if base_tool_id in blacklist:
        log.debug(f"Base tool '{tool_name}' is blacklisted, skipping sequence generation.")
        return []

    # Add the base tool sequence
    generated_sequences.append((tool_name,))

    # Recursive helper function to process subcommands
    def process_level(current_parts: Tuple[str, ...], details: Dict[str, Any]):
        for sub_name, sub_data in details.items():
            if not sub_name or not isinstance(sub_data, dict):
                continue # Skip invalid entries

            new_parts = current_parts + (sub_name,)
            sequence_id = _generate_sequence_id(new_parts)

            if sequence_id in blacklist:
                log.debug(f"Sequence '{sequence_id}' is blacklisted, skipping.")
                continue

            # Add the current subcommand sequence
            generated_sequences.append(new_parts)
            log.debug(f"Added sequence: {new_parts}")

            # Recurse if nested subcommands exist
            nested_subcommands = sub_data.get("subcommands_detail", None)
            if isinstance(nested_subcommands, dict):
                process_level(new_parts, nested_subcommands)

    # Start processing from the top level
    process_level((tool_name,), subcommands_detail)

    log.info(f"Generated {len(generated_sequences)} sequences for tool '{tool_name}'.")
    return generated_sequences