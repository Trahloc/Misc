"""Utility functions for modifying whitelist/blacklist in pyproject.toml."""

import click
import structlog
import sys
from pathlib import Path
from typing import List, Set, Tuple, Dict, Union, Optional

# Use tomlkit to preserve formatting
import tomlkit
from tomlkit.items import Array
from tomlkit.exceptions import NonExistentKey, TOMLKitError

# --- Import from shared utils --- #
from ...common.hierarchical_utils import (
    NodeData,
    ParsedHierarchy,
    parse_to_nested_dict,
    format_nested_dict_to_list,
    get_node,
    remove_node_recursive,
    set_node_flags,
)

from ...lib.tooling.tool_reconciler import _get_effective_status

log = structlog.get_logger()

# --- Type Hint for Nested Structure --- #
# REMOVED - Imported from hierarchical_utils

# --- Helper Functions --- #
# REMOVED - Moved to hierarchical_utils

# --- Modify modify_tool_list --- #
# (Keep the _apply_modification_recursive helper here as it's specific to list modification logic)


def _apply_modification_recursive(
    target_hierarchy: ParsedHierarchy,
    other_hierarchy: ParsedHierarchy,
    path: List[str],
    action: str,  # "add" or "remove"
    apply_all: bool,
    force: bool,
    target_list_name: str,
) -> Tuple[bool, bool]:  # Return (modified_target, modified_other)
    modified_target = False
    modified_other = False
    path_str = ":".join(path)
    other_list_name = "blacklist" if target_list_name == "whitelist" else "whitelist"

    # Check initial effective status - this tells us if the EXACT path is covered
    if target_list_name == "whitelist":
        initial_target_effective_status = _get_effective_status(path, target_hierarchy, other_hierarchy)
        initial_other_effective_status = _get_effective_status(path, target_hierarchy, other_hierarchy)  # Pass WL first
    else:  # target_list_name == "blacklist"
        initial_target_effective_status = _get_effective_status(
            path, other_hierarchy, target_hierarchy
        )  # Pass WL first
        initial_other_effective_status = _get_effective_status(path, other_hierarchy, target_hierarchy)

    if action == "add":
        # --- NEW Comprehensive Conflict Check --- #
        conflict_found = False
        conflicting_paths_in_other = []  # Store paths to remove if force=True

        # Check 1: Does the exact path have conflicting status in the other list?
        if initial_other_effective_status == other_list_name:
            conflict_found = True
            # Try to find the specific node causing this status (could be ancestor)
            # This logic might be complex, for now, assume the path itself is the conflict source if status matches
            conflicting_paths_in_other.append(path)
            log.debug(f"Conflict check 1: Exact path '{path_str}' effectively exists in {other_list_name}.")

        # Check 2: If adding X:*, does X or any child of X exist in the other list?
        if apply_all:
            other_node_at_path = get_node(other_hierarchy, path)
            if other_node_at_path:
                # Check if the node itself or any descendant exists explicitly or with _all
                def _find_conflicts_under(sub_hierarchy, current_sub_path):
                    found = False
                    conflicts = []
                    node_data = get_node(sub_hierarchy, current_sub_path)
                    if node_data:
                        if node_data.get("_explicit") or node_data.get("_all"):
                            found = True
                            conflicts.append(current_sub_path)
                        # Check children
                        child_keys = [k for k in node_data if not k.startswith("_")]
                        for key in child_keys:
                            child_found, child_conflicts = _find_conflicts_under(
                                sub_hierarchy, current_sub_path + [key]
                            )
                            if child_found:
                                found = True
                                conflicts.extend(child_conflicts)
                    return found, list(set(tuple(p) for p in conflicts))  # Deduplicate paths

                # Start search from the node being overridden by apply_all
                has_conflicting_children, child_conflict_paths_tuples = _find_conflicts_under(other_hierarchy, path)
                child_conflict_paths = [list(p) for p in child_conflict_paths_tuples]

                if has_conflicting_children:
                    log.debug(
                        f"Conflict check 2: Adding '{path_str}:*' conflicts with existing children in {other_list_name}: {child_conflict_paths}"
                    )
                    conflict_found = True
                    conflicting_paths_in_other.extend(child_conflict_paths)

        # Check 3: If adding X:Y, does X:* exist in the other list?
        elif len(path) > 0:
            parent_path = path[:-1]
            # Check all ancestors for :*
            for i in range(len(path), 0, -1):
                ancestor_path = path[:i]
                other_ancestor_node = get_node(other_hierarchy, ancestor_path)
                if other_ancestor_node and other_ancestor_node.get("_all", False):
                    log.debug(
                        f"Conflict check 3: Adding '{path_str}' conflicts with ancestor '{':'.join(ancestor_path)}:*' in {other_list_name}."
                    )
                    conflict_found = True
                    conflicting_paths_in_other.append(ancestor_path)  # Conflicting node is the ancestor
                    break  # Stop at the highest conflicting ancestor

        # Remove duplicates from conflicting paths
        conflicting_paths_in_other = [list(p) for p in set(tuple(p) for p in conflicting_paths_in_other)]

        # --- Handle Conflict / Force --- #
        if conflict_found:
            if not force:
                log.error(
                    f"Conflict: Cannot add '{path_str}{':*' if apply_all else ''}' to {target_list_name}. Conflicts with entries in {other_list_name}. Use --force to override. Conflicts: {conflicting_paths_in_other}"
                )
                return False, False  # Block modification due to conflict
            else:
                # Force: Remove ALL identified conflicting nodes from the other hierarchy
                log.warning(
                    f"--force specified: Attempting to remove conflicting entries from {other_list_name}: {conflicting_paths_in_other}"
                )
                any_other_changed = False
                for conflict_path in conflicting_paths_in_other:
                    log.debug(f"Force removing path: {conflict_path} from {other_list_name}")
                    other_was_changed_single = remove_node_recursive(other_hierarchy, conflict_path)
                    if other_was_changed_single:
                        log.debug(f"Successfully removed {conflict_path} from {other_list_name}.")
                        any_other_changed = True
                    else:
                        log.warning(
                            f"Attempted force removal of {conflict_path} from {other_list_name}, but remove_node_recursive reported no change."
                        )

                if any_other_changed:
                    modified_other = True  # Record that the other list WAS modified
                else:
                    log.warning(
                        f"--force used for '{path_str}', but no conflicting paths could be effectively removed from {other_list_name}. Paths attempted: {conflicting_paths_in_other}"
                    )

        # --- Proceed with adding/updating the target list --- #
        target_changed_by_set = set_node_flags(target_hierarchy, path, is_explicit=True, is_all=apply_all)
        if target_changed_by_set:
            modified_target = True

    elif action == "remove":
        # Get the node *before* potentially modifying it
        initial_target_node = get_node(target_hierarchy, path)

        if not initial_target_node:
            log.debug(f"Item '{path_str}' not found in {target_list_name} for removal. No change.")
            return False, False

        if apply_all:
            target_was_changed = remove_node_recursive(target_hierarchy, path)
            if target_was_changed:
                modified_target = True
            else:
                log.debug(f"Remove --all called for '{path_str}', but hierarchy did not change (was it already gone?).")
        else:
            # --- Non-All Remove Logic --- #
            node_to_modify = get_node(target_hierarchy, path)
            if node_to_modify:
                was_explicit = node_to_modify.get("_explicit", False)
                has_all = node_to_modify.get("_all", False)

                if was_explicit:
                    log.debug(f"Removing explicit flag for '{path_str}'. Has _all={has_all}")
                    node_to_modify.pop("_explicit", None)
                    if not has_all:
                        modified_target = True
                        log.debug(f"Effective modification: explicit flag removed and _all=False for '{path_str}'")
                    else:
                        log.debug(f"Explicit flag removed for '{path_str}', but _all=True, so no effective change.")

                    is_empty_now = not any(k for k in node_to_modify if not k.startswith("_"))
                    has_flags_now = node_to_modify.get("_explicit", False) or node_to_modify.get("_all", False)
                    if is_empty_now and not has_flags_now:
                        log.debug(
                            f"Node '{path_str}' became empty and flagless after explicit flag removal, removing recursively."
                        )
                        cleanup_removed_something = remove_node_recursive(target_hierarchy, path)
                        if cleanup_removed_something:
                            modified_target = True
                else:
                    log.debug(
                        f"Item '{path_str}' found in {target_list_name}, but explicit flag was not set for non-recursive removal. No change."
                    )
            else:
                log.warning(
                    f"Node '{path_str}' disappeared during non-all removal check? Initial existed: {initial_target_node is not None}"
                )

    # Return final modification status for both hierarchies - rely solely on determined flags
    return modified_target, modified_other


def modify_tool_list(
    project_root: Path,
    tool_items_to_modify: Tuple[str, ...],
    target_list_name: str,  # "whitelist" or "blacklist"
    action: str,  # "add" or "remove"
    apply_all: bool,
    force: bool = False,
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

        # Get raw lists
        raw_target_list = managed_tools_table.get(target_list_name, [])
        other_list_name = "blacklist" if target_list_name == "whitelist" else "whitelist"
        raw_other_list = managed_tools_table.get(other_list_name, [])

        # --- Parse the raw lists into NESTED dicts using imported helper --- #
        target_hierarchy = parse_to_nested_dict(
            list(raw_target_list) if isinstance(raw_target_list, (Array, list)) else []
        )
        other_hierarchy = parse_to_nested_dict(
            list(raw_other_list) if isinstance(raw_other_list, (Array, list)) else []
        )
        initial_target_repr = repr(target_hierarchy)
        initial_other_repr = repr(other_hierarchy)

        # --- Process Modifications --- #
        any_item_caused_modification = False
        for item_str_raw in tool_items_to_modify:
            item_str = item_str_raw.strip()
            if not item_str:
                continue

            # Check for trailing :* which now indicates apply_all for this item
            item_apply_all = apply_all  # Start with global flag
            if item_str.endswith(":*"):
                item_apply_all = True
                item_str = item_str[:-2]  # Remove the trailing :*
                if not item_str:
                    log.error("Invalid format: ':*' cannot stand alone.")
                    continue

            path = [p.strip() for p in item_str.split(":") if p.strip()]
            if not path:
                log.warning(f"Ignoring invalid empty item string: '{item_str_raw}'")
                continue

            # Apply the modification recursively
            mod_target, mod_other = _apply_modification_recursive(
                target_hierarchy, other_hierarchy, path, action, item_apply_all, force, target_list_name
            )
            # Track if *any* modification call reported success for either hierarchy
            if mod_target or mod_other:
                any_item_caused_modification = True

        # --- Check if changes occurred --- #
        # NEW LOGIC:
        # Base modification status solely on the boolean flags returned by the recursive helper,
        # which now understand effective state changes.
        overall_modified = any_item_caused_modification

        # --- DEBUG: Log final hierarchies before formatting --- #
        log.debug("[FINAL HIERARCHY DEBUG] Target Hierarchy before format:", data=repr(target_hierarchy))
        log.debug("[FINAL HIERARCHY DEBUG] Other Hierarchy before format:", data=repr(other_hierarchy))
        # --- END DEBUG --- #

        # --- Write back to TOML --- #
        if overall_modified:
            log.info(f"Change detected in {target_list_name} or opposing list. Writing updated configuration...")
            final_target_list = format_nested_dict_to_list(target_hierarchy)
            final_other_list = format_nested_dict_to_list(other_hierarchy)

            # Update the tomlkit document
            target_array = tomlkit.array()  # Create new array
            target_array.extend(final_target_list)
            target_array.multiline(True)
            managed_tools_table[target_list_name] = target_array

            other_array = tomlkit.array()  # Create new array
            other_array.extend(final_other_list)
            other_array.multiline(True)
            managed_tools_table[other_list_name] = other_array

            # --- ADDED STEP: Write toml_doc back to pyproject_path ---
            try:
                log.debug("TOML doc before final dump", doc_structure=tomlkit.dumps(doc))
                with open(pyproject_path, "w", encoding="utf-8") as f:
                    f.write(tomlkit.dumps(doc))
                log.debug(f"Successfully saved updated {target_list_name} and {other_list_name} to {pyproject_path}")
            except Exception as e:
                log.exception(f"Error writing updated TOML back to {pyproject_path}", error=str(e))
                return False  # Failed to save changes
            # --- End Added Step ---

            return True  # Report modification happened and saved
        else:
            log.info(f"No effective changes made to {target_list_name} or opposing list.")
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
