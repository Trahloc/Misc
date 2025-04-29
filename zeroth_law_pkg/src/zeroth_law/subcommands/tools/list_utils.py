"""Utility functions for modifying whitelist/blacklist in pyproject.toml."""

import click
import structlog
import sys
from pathlib import Path
from typing import List, Set, Tuple, Dict

# Use tomlkit to preserve formatting
import tomlkit
from tomlkit.items import Array
from tomlkit.exceptions import NonExistentKey, TOMLKitError

# Import the parser from config_loader
from ...common.config_loader import _parse_hierarchical_list

log = structlog.get_logger()

# --- Helper Functions --- #


def _format_parsed_dict_to_list(parsed_dict: Dict[str, Set[str]]) -> List[str]:
    """Converts the parsed dictionary back into a sorted list of strings for TOML."""
    output_list = []
    for tool, subs in sorted(parsed_dict.items()):
        if subs == {"*"}:
            output_list.append(tool)
        else:
            # Sort subcommands for consistent output
            sorted_subs = sorted(list(subs))
            output_list.append(f"{tool}:{','.join(sorted_subs)}")
    return output_list


def modify_tool_list(
    project_root: Path,
    tool_items_to_modify: Tuple[str, ...],
    target_list_name: str,  # "whitelist" or "blacklist"
    action: str,  # "add" or "remove"
    apply_all: bool,  # TODO: Re-evaluate --all flag logic for hierarchical data
) -> bool:
    """Reads pyproject.toml, modifies the target list (handling hierarchy), and writes it back.

    Returns:
        True if the file was modified, False otherwise.
    """
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {pyproject_path}")

    try:
        # Read and parse with tomlkit
        content = pyproject_path.read_text(encoding="utf-8")
        doc = tomlkit.parse(content)

        # Navigate to managed-tools table, creating if necessary
        managed_tools_table = doc.setdefault("tool", {}).setdefault("zeroth-law", {}).setdefault("managed-tools", {})

        # Ensure target and other lists exist as arrays, get raw lists
        raw_target_list = managed_tools_table.get(target_list_name, [])
        other_list_name = "blacklist" if target_list_name == "whitelist" else "whitelist"
        raw_other_list = managed_tools_table.get(other_list_name, [])

        # --- Parse the raw lists into structured dicts --- #
        target_dict = _parse_hierarchical_list(
            list(raw_target_list) if isinstance(raw_target_list, (Array, list)) else []
        )
        other_dict = _parse_hierarchical_list(list(raw_other_list) if isinstance(raw_other_list, (Array, list)) else [])
        initial_target_dict_repr = repr(target_dict)  # For change detection

        # --- Process Modifications --- #
        # TODO: Implement --all logic refinement here if needed.
        if apply_all:
            log.warning("Ignoring --all flag for now due to complexity with hierarchical lists.")

        for item_str in tool_items_to_modify:
            item_str = item_str.strip()
            if not item_str:
                continue

            parts = item_str.split(":", 1)
            tool_name = parts[0].strip()
            subs_to_modify_str = parts[1] if len(parts) > 1 else None
            subs_to_modify: Set[str] | None = None
            if subs_to_modify_str:
                subs_to_modify = {s.strip() for s in subs_to_modify_str.split(",") if s.strip()}
                if not subs_to_modify:
                    log.warning(f"Ignoring item '{item_str}' with colon but no valid subcommands.")
                    continue

            is_whole_tool_modification = subs_to_modify is None

            if action == "add":
                # --- Add Logic --- #
                # Check other list first (for conflicts/removals)
                if tool_name in other_dict:
                    if is_whole_tool_modification:
                        # Adding whole tool, remove any specific subs or whole tool from other list
                        other_dict.pop(tool_name, None)
                        log.debug(f"Removed '{tool_name}:*' and any specific subcommands from {other_list_name}.")
                    elif subs_to_modify:  # Adding specific subs
                        if other_dict[tool_name] == {"*"}:
                            # Cannot add specific subs if whole tool is in other list
                            log.info(
                                f"Cannot add '{item_str}' to {target_list_name}; '{tool_name}' is fully present in {other_list_name}."
                            )
                            continue  # Skip adding to target_dict
                        else:
                            # Remove these specific subs from the other list
                            other_dict[tool_name].difference_update(subs_to_modify)
                            if not other_dict[tool_name]:  # Remove tool key if set is empty
                                other_dict.pop(tool_name)
                            log.debug(f"Removed specified subcommands for '{tool_name}' from {other_list_name}.")

                # Now add to target list
                if is_whole_tool_modification:
                    # Add/overwrite tool with {"*"}
                    target_dict[tool_name] = {"*"}
                    log.debug(f"Added/Set '{tool_name}:*' in {target_list_name}.")
                elif subs_to_modify:  # Adding specific subs
                    if tool_name not in target_dict or target_dict[tool_name] != {"*"}:
                        target_dict.setdefault(tool_name, set()).update(subs_to_modify)
                        log.debug(f"Added subcommands {subs_to_modify} for '{tool_name}' in {target_list_name}.")
                    else:
                        # Whole tool already in target, do nothing
                        log.debug(
                            f"Cannot add specific subs for '{tool_name}'; tool is already fully in {target_list_name}."
                        )

            elif action == "remove":
                # --- Remove Logic --- #
                if tool_name in target_dict:
                    if is_whole_tool_modification:
                        # Removing whole tool
                        target_dict.pop(tool_name, None)
                        log.debug(f"Removed '{tool_name}:*' and any specific subcommands from {target_list_name}.")
                    elif subs_to_modify:  # Removing specific subs
                        if target_dict[tool_name] == {"*"}:
                            # Cannot remove specific subs if whole tool is listed
                            log.info(
                                f"Cannot remove '{item_str}' from {target_list_name}; '{tool_name}' is fully present."
                            )
                        else:
                            target_dict[tool_name].difference_update(subs_to_modify)
                            if not target_dict[tool_name]:  # Remove tool key if set is empty
                                target_dict.pop(tool_name)
                            log.debug(f"Removed specified subcommands for '{tool_name}' from {target_list_name}.")
                else:
                    log.debug(f"Item '{item_str}' not found in {target_list_name} for removal.")

        # --- Check if changes occurred --- #
        modified = repr(target_dict) != initial_target_dict_repr or bool(
            other_dict
        )  # Simplified check, assumes other_dict changes count
        # A more precise check would compare initial and final repr of other_dict too

        # --- Write back to TOML --- #
        if modified:
            # Convert dicts back to sorted lists
            final_target_list = _format_parsed_dict_to_list(target_dict)
            final_other_list = _format_parsed_dict_to_list(other_dict)

            # Update the tomlkit document
            target_array = tomlkit.array()
            target_array.extend(final_target_list)
            target_array.multiline(True)
            managed_tools_table[target_list_name] = target_array

            other_array = tomlkit.array()
            other_array.extend(final_other_list)
            other_array.multiline(True)
            managed_tools_table[other_list_name] = other_array  # Update the other list too

            log.info(f"Writing updated configuration to {pyproject_path}")
            pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
            return True
        else:
            log.info("No changes made to the configuration lists.")
            return False

    except (NonExistentKey, KeyError) as e:
        log.error(f"Configuration structure error in {pyproject_path}: Missing key {e}")
        raise ValueError(f"Invalid pyproject.toml structure: Missing {e}") from e
    except (TypeError, TOMLKitError) as e:
        log.error(f"Error processing {pyproject_path}: {e}")
        raise ValueError(f"Error parsing or modifying {pyproject_path}") from e
    except Exception as e:
        log.exception(f"An unexpected error occurred while modifying {pyproject_path}")
        raise


def list_tool_list(project_root: Path, target_list_name: str) -> List[str]:
    """Reads pyproject.toml and returns the contents of the target list.
    (Keeps original behavior - returns raw list of strings).
    """
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.is_file():
        log.warning(f"Configuration file not found: {pyproject_path}. Returning empty list.")
        return []

    try:
        content = pyproject_path.read_text(encoding="utf-8")
        doc = tomlkit.parse(content)
        managed_tools_table = doc.get("tool", {}).get("zeroth-law", {}).get("managed-tools", {})
        target_list = managed_tools_table.get(target_list_name, [])
        # Ensure it's a list before returning
        if isinstance(target_list, (list, tomlkit.items.Array)):
            return sorted(list(target_list))
        else:
            log.warning(
                f"Config key 'tool.zeroth-law.managed-tools.{target_list_name}' is not a list. Returning empty list."
            )
            return []
    except (TOMLKitError, TypeError) as e:
        log.error(f"Error parsing {pyproject_path}: {e}. Returning empty list.")
        return []
    except Exception as e:
        log.exception(f"An unexpected error occurred while reading {pyproject_path}. Returning empty list.")
        return []
