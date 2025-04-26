"""Utility functions for modifying whitelist/blacklist in pyproject.toml."""

import logging
from pathlib import Path
from typing import List, Set, Tuple

# Use tomlkit to preserve formatting
import tomlkit
from tomlkit.exceptions import NonExistentKey, TOMLKitError

log = logging.getLogger(__name__)

# --- Helper Functions --- #


def _parse_tool_item(item: str) -> Tuple[str, str | None]:
    """Parses an item like 'tool' or 'tool:subcommand'."""
    if ":" in item:
        parts = item.split(":", 1)
        return parts[0], parts[1]
    return item, None


def _format_tool_item(tool: str, subcommand: str | None) -> str:
    """Formats tool and subcommand back into an item string."""
    return f"{tool}:{subcommand}" if subcommand else tool


def modify_tool_list(
    project_root: Path,
    tool_items: Tuple[str, ...],
    target_list_name: str,  # "whitelist" or "blacklist"
    action: str,  # "add" or "remove"
    apply_all: bool,
) -> bool:
    """Reads pyproject.toml, modifies the target list, and writes it back.

    Returns:
        True if the file was modified, False otherwise.
    """
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {pyproject_path}")

    try:
        # Read the file content
        content = pyproject_path.read_text(encoding="utf-8")
        # Parse with tomlkit
        doc = tomlkit.parse(content)

        # Navigate to the managed-tools table
        # Use get() with default {} to avoid errors if sections are missing
        managed_tools_table = doc.setdefault("tool", {}).setdefault("zeroth-law", {}).setdefault("managed-tools", {})

        # Ensure the target list exists as a tomlkit array
        if target_list_name not in managed_tools_table:
            managed_tools_table[target_list_name] = tomlkit.array()
            managed_tools_table[target_list_name].multiline(True)  # Prefer multiline
        elif not isinstance(managed_tools_table[target_list_name], tomlkit.items.Array):
            # Attempt to convert if it's a standard list, otherwise raise error
            try:
                current_list = list(managed_tools_table[target_list_name])
                managed_tools_table[target_list_name] = tomlkit.array(current_list)
                managed_tools_table[target_list_name].multiline(True)  # Prefer multiline for lists
            except (TypeError, ValueError):
                raise TypeError(f"Config key 'tool.zeroth-law.managed-tools.{target_list_name}' is not a list/array.")

        # Get the actual list array and the name of the *other* list
        target_list: tomlkit.items.Array = managed_tools_table[target_list_name]
        other_list_name = "blacklist" if target_list_name == "whitelist" else "whitelist"
        other_list_exists = other_list_name in managed_tools_table and isinstance(
            managed_tools_table.get(other_list_name), tomlkit.items.Array
        )
        other_list: tomlkit.items.Array | None = managed_tools_table.get(other_list_name) if other_list_exists else None

        # Convert to sets for efficient lookup
        target_set = set(target_list)
        other_set = set(other_list) if other_list else set()

        modified = False
        for item in tool_items:
            tool_name, subcommand_name = _parse_tool_item(item)
            item_to_modify = _format_tool_item(tool_name, subcommand_name)
            items_for_all_action: Set[str] = set()

            # Determine related items if --all is used
            if apply_all:
                if subcommand_name is None:
                    items_for_all_action = {i for i in other_set if i.startswith(f"{tool_name}:")}
                else:
                    items_for_all_action = {i for i in other_set if i.startswith(f"{item_to_modify}:")}

            # --- Perform Add/Remove Action --- #
            if action == "add":
                # Add the main item to the target list
                if item_to_modify not in target_set:
                    target_list.append(item_to_modify)
                    target_set.add(item_to_modify)
                    log.debug(f"Added '{item_to_modify}' to {target_list_name}.")
                    modified = True

                # Remove the main item from the other list (if present)
                if other_list and item_to_modify in other_set:
                    try:
                        other_list.remove(item_to_modify)
                        other_set.remove(item_to_modify)
                        log.debug(f"Removed '{item_to_modify}' from {other_list_name}.")
                        modified = True
                    except ValueError:
                        pass  # Item wasn't actually in the list

                # If --all, remove related items from the other list
                if apply_all and items_for_all_action and other_list:
                    for related_item in items_for_all_action:
                        if related_item in other_set:
                            try:
                                other_list.remove(related_item)
                                other_set.remove(related_item)
                                log.debug(f"Removed related item '{related_item}' from {other_list_name} due to --all.")
                                modified = True
                            except ValueError:
                                pass

                # Check for conflicts in the other list
                if other_list:
                    if item_to_modify in other_set:
                        log.info(f"Note: '{item_to_modify}' remains explicitly in {other_list_name}.")
                    elif subcommand_name is None and any(i.startswith(f"{tool_name}:") for i in other_set):
                        log.info(f"Note: Subcommands of '{tool_name}' may still exist in {other_list_name}.")
                    elif subcommand_name is not None and tool_name in other_set:
                        log.info(f"Note: Base tool '{tool_name}' remains explicitly in {other_list_name}.")

            elif action == "remove":
                # Remove the main item from the target list
                if item_to_modify in target_set:
                    try:
                        target_list.remove(item_to_modify)
                        target_set.remove(item_to_modify)
                        log.debug(f"Removed '{item_to_modify}' from {target_list_name}.")
                        modified = True
                    except ValueError:
                        pass

                # If --all, remove related items from the target list
                if apply_all:
                    related_target_items: Set[str] = set()
                    if subcommand_name is None:
                        related_target_items = {i for i in target_set if i.startswith(f"{tool_name}:")}
                    else:
                        related_target_items = {i for i in target_set if i.startswith(f"{item_to_modify}:")}

                    for related_item in related_target_items:
                        if related_item in target_set:
                            try:
                                target_list.remove(related_item)
                                target_set.remove(related_item)
                                log.debug(
                                    f"Removed related item '{related_item}' from {target_list_name} due to --all."
                                )
                                modified = True
                            except ValueError:
                                pass

        # Ensure lists are sorted for consistency
        if modified:
            target_list._value.sort()
            if other_list:
                other_list._value.sort()

            # Write the modified document back to the file
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
    """Reads pyproject.toml and returns the contents of the target list."""
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
