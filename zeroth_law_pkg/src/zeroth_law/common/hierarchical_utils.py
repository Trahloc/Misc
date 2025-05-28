"""Utilities for handling hierarchical list structures (whitelist/blacklist)."""

import structlog
from typing import List, Dict, Union, Optional, Tuple, Literal, Set
from tomlkit.items import Array
import sys
import time

log = structlog.get_logger()

# --- Type Hint for Nested Structure --- #
# Represents the hierarchical structure: Dict[node_name, NodeDict]
# Special keys: '_explicit' (bool), '_all' (bool)
NodeData = Dict[str, Union[bool, "NodeData"]]  # Recursive type hint
ParsedHierarchy = Dict[str, NodeData]

# --- Parsing --- #


def parse_to_nested_dict(raw_list: Union[List[str], Set[str], Array]) -> ParsedHierarchy:
    """Parses a list of hierarchical strings into a nested dictionary representation."""
    log.debug("Starting hierarchical list parsing.", input_list=raw_list)

    # --- Input Validation --- #
    if not isinstance(raw_list, (list, set, Array)):
        log.warning("Invalid input type for hierarchical parsing, returning empty dict.", input_type=type(raw_list))
        return {}  # Return empty dict for invalid input types (matches test expectation)
    # --- End Validation --- #

    root: ParsedHierarchy = {}
    processed_list = list(raw_list)  # Ensure it's a list

    for original_entry in processed_list:
        if not isinstance(original_entry, str) or not original_entry.strip():
            continue

        # --- Pre-validation for invalid patterns --- #
        if "::" in original_entry:
            log.warning(f"Skipping entry '{original_entry}' due to invalid '::'.")
            continue
        # --- End Pre-validation ---

        entry = original_entry.strip()

        # --- Pre-process entry for suffix handling ---
        entry_to_process = entry
        apply_all_flag = False
        apply_explicit_flag = False

        if entry.endswith(":*"):
            entry_to_process = entry[:-2]
            apply_all_flag = True
            log.debug(f"Detected ':*' suffix for '{original_entry}', processing base '{entry_to_process}'.")
        elif entry.endswith(":") and len(entry) > 1:
            entry_to_process = entry[:-1]
            apply_explicit_flag = True  # Treat 'toolA:' as explicit 'toolA'
            log.debug(f"Detected trailing ':' suffix for '{original_entry}', processing base '{entry_to_process}'.")
        elif ":" not in entry and entry != "*":  # Simple entry like "toolA"
            entry_to_process = entry  # Already correct
            apply_explicit_flag = True
            log.debug(f"Detected simple entry '{original_entry}', processing base '{entry_to_process}'.")
        # else: Entry like "toolA:sub" - flags determined by loop later, or complex like "tool:*" which is handled by apply_all_flag

        if not entry_to_process:  # Handle ":*", ":", or entries reducing to empty
            log.warning(
                f"Skipping invalid or empty entry after suffix processing: '{original_entry}' -> '{entry_to_process}'"
            )
            continue  # Skip to next entry in outer loop

        # Check for '*' appearing not at the end after ':'. e.g., toolA:*:subB is invalid
        if "*" in entry_to_process and not entry_to_process.endswith("*"):
            # Allow '*' if it's the only part, but handled by apply_all_flag earlier
            parts_check = entry_to_process.split(":")
            if not (len(parts_check) == 1 and parts_check[0] == "*"):
                log.warning(f"Skipping entry '{original_entry}': Wildcard '*' can only appear after the last ':'")
                continue

        parts = entry_to_process.split(":")
        current_level = root
        path_accumulator = []
        is_valid_entry_path = True
        nodes_at_final_level = []  # Nodes identified by the last part of entry_to_process

        # --- Traverse/Create Path ---
        for i, part in enumerate(parts):
            is_last_part = i == len(parts) - 1
            stripped_part = part.strip()

            # --- Basic Validation ---
            if not stripped_part:
                # This should ideally not happen now due to pre-processing, but check anyway
                log.warning(
                    f"Skipping entry '{original_entry}' due to unexpected empty component during path traversal at index {i}."
                )
                is_valid_entry_path = False
                break
            if not is_last_part and ("," in stripped_part or "*" in stripped_part):
                log.warning(
                    f"Skipping entry '{original_entry}': Commas or '*' are only allowed in the final component '{parts[-1]}'."
                )
                is_valid_entry_path = False
                break
            # --- End Validation ---

            # Split by comma ONLY if it's the last part
            node_names = []
            if is_last_part:
                node_names = [name.strip() for name in stripped_part.split(",") if name.strip()]
                if not node_names:
                    log.warning(
                        f"Skipping entry '{original_entry}': Final part '{part}' resulted in no valid node names."
                    )
                    is_valid_entry_path = False
                    break
                # Handle '*' as a node name if it was *not* removed by suffix processing (e.g., "toolA:*" without the final :)
                # This case should be caught earlier, but as a safeguard:
                if "*" in node_names and not apply_all_flag:
                    log.warning(
                        f"Skipping entry '{original_entry}': Found '*' in final part but not handled as suffix."
                    )
                    is_valid_entry_path = False
                    break

            else:  # Not the last part
                if stripped_part == "*":  # '*' not allowed mid-path
                    log.warning(
                        f"Skipping entry '{original_entry}': Wildcard '*' not allowed in intermediate path component '{part}'."
                    )
                    is_valid_entry_path = False
                    break
                node_names = [stripped_part]  # Only one node name allowed mid-path

            next_level_dict = None  # Store the dict for the next level (if needed)
            current_part_nodes_temp = []  # Track nodes created/found at this level for this part

            for node_name in node_names:
                path_accumulator.append(node_name)

                if node_name not in current_level:
                    current_level[node_name] = {"_explicit": False, "_all": False}  # Initialize flags
                node = current_level[node_name]

                if not isinstance(node, dict):
                    log.error(
                        f"Config structure error in '{original_entry}': Node '{node_name}' is not a dict.",
                        path=path_accumulator,
                    )
                    is_valid_entry_path = False
                    break  # Break inner name loop

                current_part_nodes_temp.append(node)  # Store node found/created

                # Prepare for descent if not last part
                if not is_last_part:
                    # Check if descent is blocked by _all flag from a previous entry
                    if node.get("_all", False):
                        log.warning(
                            f"Parser: Cannot define sub-nodes under '{':'.join(path_accumulator)}' (marked with ':*'). Skipping deeper parts of entry '{original_entry}'."
                        )
                        is_valid_entry_path = False
                        break  # Break inner name loop

                    # We descend into the first (and should be only) node for non-last parts
                    if next_level_dict is None:
                        next_level_dict = node
                    else:
                        # This should not happen due to earlier validation
                        log.error(
                            f"Internal parser error: Multiple nodes specified in non-final part '{part}' for entry '{original_entry}'."
                        )
                        is_valid_entry_path = False
                        break

                path_accumulator.pop()  # Backtrack for sibling nodes in the same part (if any)

            if not is_valid_entry_path:
                break  # Break outer part loop if inner loop failed

            if not is_last_part:
                if next_level_dict is not None:
                    current_level = next_level_dict  # Descend
                else:
                    # Should be caught by node_names check or validation
                    log.error(
                        f"Internal parser error: Failed to determine next level for entry '{original_entry}' at part '{part}'."
                    )
                    is_valid_entry_path = False
                    break  # Break outer part loop
            else:
                # Reached the end of the path for this entry
                nodes_at_final_level.extend(current_part_nodes_temp)

        # --- Apply Flags based on original suffix or explicit simple entry ---
        if is_valid_entry_path and nodes_at_final_level:
            log.debug(
                f"Applying flags for '{original_entry}'. All={apply_all_flag}, Explicit={apply_explicit_flag}. Target Nodes: {len(nodes_at_final_level)}"
            )
            for final_node in nodes_at_final_level:
                if apply_all_flag:
                    # Clear children and set _all=True, _explicit=False
                    keys_to_delete = [k for k in final_node if not k.startswith("_")]
                    if keys_to_delete:
                        log.debug(
                            f"Parser: Clearing children {keys_to_delete} due to ':*' override for entry '{original_entry}'."
                        )
                    for k in keys_to_delete:
                        if k in final_node:
                            del final_node[k]  # Check existence before deleting
                    final_node["_all"] = True
                    final_node["_explicit"] = False  # Wildcard overrides explicit
                elif apply_explicit_flag:
                    # Set _explicit=True, ensure _all=False (or exists and is False)
                    # Don't set explicit if _all is already True from a previous wildcard
                    if not final_node.get("_all", False):
                        final_node["_explicit"] = True
                    # Ensure _all key exists if we set explicit
                    final_node.setdefault("_all", False)
                else:
                    # Case like "toolA:sub", no specific suffix. Node exists.
                    # Set explicit=True on the final node(s) unless _all is already set.
                    if not final_node.get("_all", False):
                        final_node["_explicit"] = True
                    # Ensure _all key exists if we set explicit
                    final_node.setdefault("_all", False)

    log.debug("Finished parsing all entries", final_structure=root)
    return root


# --- Formatting --- #


def format_nested_dict_to_list(hierarchy: ParsedHierarchy, current_path: List[str] = None) -> List[str]:
    """Converts the nested dictionary back into a sorted list of strings for TOML."""
    if current_path is None:
        current_path = []

    output_list = []
    for name, node_data in sorted(hierarchy.items()):
        if name.startswith("_"):
            continue

        new_path = current_path + [name]
        path_str = ":".join(new_path)

        is_explicit = node_data.get("_explicit", False)
        is_all = node_data.get("_all", False)
        child_keys = {k for k in node_data if not k.startswith("_")}
        child_hierarchy = {k: v for k, v in node_data.items() if not k.startswith("_") and isinstance(v, dict)}

        if is_all:
            output_list.append(f"{path_str}:*")
        else:
            if is_explicit:
                output_list.append(path_str)

            if child_hierarchy:
                output_list.extend(format_nested_dict_to_list(child_hierarchy, new_path))

    if not current_path:
        return sorted(list(set(output_list)))
    return output_list


# --- Node Manipulation Helpers --- #


def get_node(hierarchy: ParsedHierarchy, path: List[str]) -> Optional[NodeData]:
    """Safely gets a node at a specific path, returning None if not found."""
    current_level = hierarchy
    for part in path:
        node = current_level.get(part)
        if not node or not isinstance(node, dict):
            return None
        current_level = node
    return current_level


def remove_node_recursive(hierarchy: ParsedHierarchy, path: List[str]) -> bool:
    """Recursively removes a node and its empty parents.
    Handles removal from the provided hierarchy dictionary directly.

    Returns:
        True if a modification was made to the hierarchy, False otherwise.
    """
    if not path:
        log.debug("remove_node_recursive called with empty path, doing nothing.")
        return False

    log.debug(f"Attempting recursive removal for path: {path} from hierarchy ID: {id(hierarchy)}")
    initial_repr = repr(hierarchy)  # Capture initial state to detect changes

    # --- Recursive Approach --- #
    def _remove_helper(level: Dict, current_path: List[str]) -> bool:
        """Returns True if the current node should be deleted by its parent."""
        if not current_path:
            return False  # Should not happen with initial check

        part = current_path[0]
        remaining_path = current_path[1:]

        node = level.get(part)
        if not node or not isinstance(node, dict):
            # Node doesn't exist at this level, path invalid for removal
            log.debug(
                f"Node '{part}' not found at path {''.join(path[: len(path) - len(current_path)])}. Cannot remove."
            )
            return False

        child_requested_deletion = False
        if remaining_path:  # Recurse deeper
            child_requested_deletion = _remove_helper(node, remaining_path)
            if child_requested_deletion:
                child_key_to_delete = remaining_path[0]
                log.debug(f"Child requested deletion, removing node '{child_key_to_delete}' from '{part}'")
                if child_key_to_delete in node:
                    del node[child_key_to_delete]
                    # Deletion happened, parent needs to know. Actual modification check happens later.
                else:
                    log.warning(
                        f"Child '{child_key_to_delete}' requested deletion, but key already missing from '{part}'?"
                    )
        # else: Base case: We are at the node to be removed ('part' is the key).
        # The decision to remove is made by the caller or based on emptiness below.

        # Check if the current node ('node') should be deleted by its parent.
        is_empty = not any(k for k in node if not k.startswith("_"))
        has_flags = node.get("_explicit", False) or node.get("_all", False)

        # Decide if this node should be deleted by its parent
        if not remaining_path:
            # This is the node explicitly targeted by the path, signal for removal.
            log.debug(f"Target node '{part}' reached, requesting deletion by parent.")
            return True
        elif child_requested_deletion and is_empty and not has_flags:
            # Child was deleted, and this node is now empty and flagless, signal for removal.
            log.debug(f"Node '{part}' is now empty and flagless after child deletion, requesting deletion by parent.")
            return True
        else:
            # Keep the node otherwise.
            log.debug(
                f"Node '{part}' will be kept (Target={not not remaining_path}, ChildDel={child_requested_deletion}, Empty={is_empty}, Flags={has_flags})."
            )
            return False

    # --- Initial Call --- #
    root_part = path[0]
    if root_part not in hierarchy:
        log.debug(f"Root node '{root_part}' not found, cannot remove path {path}.")
        return False  # Node doesn't exist, nothing to do

    if len(path) == 1:  # Removing a top-level tool directly
        log.debug(f"Removing top-level node '{root_part}'. PRE-DEL STATE: {repr(hierarchy)}")  # DEBUG
        del hierarchy[root_part]
    else:  # Need to recurse into the top-level node
        root_node = hierarchy[root_part]
        if isinstance(root_node, dict):  # Ensure it's a dict before recursing
            should_delete_first_child = _remove_helper(root_node, path[1:])
            if should_delete_first_child:
                first_child_key = path[1]
                log.debug(f"Helper requested deletion of root's child '{first_child_key}' from '{root_part}'")
                if first_child_key in root_node:
                    del root_node[first_child_key]
                    # Final check: if root_part is now empty and flagless after child deletion, remove it too
                    is_empty = not any(k for k in root_node if not k.startswith("_"))
                    has_flags = root_node.get("_explicit", False) or root_node.get("_all", False)
                    if is_empty and not has_flags:
                        log.debug(f"Removing now empty/flagless top-level node '{root_part}'.")
                        del hierarchy[root_part]
                else:
                    log.warning(f"Root's child '{first_child_key}' requested deletion, but key already missing?")
        else:
            log.warning(f"Cannot recurse into '{root_part}' for path {path} as it's not a dictionary.")
            return False  # No change possible

    # Check if the overall hierarchy representation changed
    final_repr = repr(hierarchy)
    modified = final_repr != initial_repr
    log.debug(f"remove_node_recursive for path {path} resulted in modified={modified}")
    return modified


def set_node_flags(hierarchy: ParsedHierarchy, path: List[str], is_explicit: Optional[bool], is_all: Optional[bool]):
    """Sets the _explicit and _all flags for a node, creating path if needed.
    Only modifies if the new flag value is different from the existing one.
    Returns True if a change was made, False otherwise.
    """
    current_level = hierarchy
    node = None  # Initialize node to None
    for part in path:
        # Use get first to check if path exists without creating it
        child_node = current_level.get(part)
        if child_node is None:
            # Path doesn't exist, create it
            child_node = current_level.setdefault(part, {})
        elif not isinstance(child_node, dict):
            log.error(f"Structure error: Expected dict, found {type(child_node)} at path {path}")
            return False  # Cannot proceed, no change
        current_level = child_node
    node = current_level  # Node is the final level dict

    if node is None:
        log.error(f"Failed to get or create node for path {path}")
        return False  # Should not happen if logic above is correct

    made_change = False
    # Update _explicit only if value is provided and different
    if is_explicit is not None:
        current_explicit = node.get("_explicit", False)
        if current_explicit != is_explicit:
            # Only set explicit if _all is not currently True
            if not node.get("_all", False):
                node["_explicit"] = is_explicit
                made_change = True
            # Implicit: If _all is True, setting explicit makes no difference
            # and doesn't count as a modification.

    # Update _all only if value is provided and different
    if is_all is not None:
        current_all = node.get("_all", False)
        if current_all != is_all:
            node["_all"] = is_all
            made_change = True  # Changing _all always matters
            if is_all:  # If setting _all=True, ensure _explicit=False and remove children
                node["_explicit"] = False  # Wildcard overrides explicit
                keys_to_delete = [k for k in node if not k.startswith("_")]
                if keys_to_delete:
                    log.debug(f"Clearing children of node at '{path}' because _all=True is being set.")
                    for k in keys_to_delete:
                        # Check if key exists before deleting, prevent KeyError
                        if k in node:
                            del node[k]
                    # Deleting children counts as a modification, already covered by made_change = True
            # No need for an else block; if is_all is False, we just set it and made_change is True

    # Ensure both flags exist if either was set, but don't count this as a change
    if "_explicit" in node or "_all" in node:
        node.setdefault("_explicit", False)
        node.setdefault("_all", False)

    # Return True ONLY if a flag was actually changed or children were deleted
    return made_change


# --- Conflict and Status Checks --- #


def check_list_conflicts(whitelist_tree: ParsedHierarchy, blacklist_tree: ParsedHierarchy) -> List[Tuple[str, ...]]:
    """Checks for items explicitly listed in both whitelist and blacklist,
       including conflicts between parent ':*' and specific children.

    Returns:
        A list of conflicting sequence paths as tuples (e.g., [('tool', 'sub')]).
    """
    conflicts: List[Tuple[str, ...]] = []

    def _traverse(
        node_w: NodeData,
        node_b: NodeData,
        current_path: List[str],
        parent_all_w: bool = False,  # Track if parent had _all=True
        parent_all_b: bool = False,
    ):
        # Get flags for the current node
        is_explicit_w = node_w.get("_explicit", False)
        is_explicit_b = node_b.get("_explicit", False)
        is_all_w = parent_all_w or node_w.get("_all", False)  # Consider parent _all
        is_all_b = parent_all_b or node_b.get("_all", False)

        # --- Conflict Detection Logic --- #
        # Conflict only if both are EXPLICITLY set at the same level
        # OR if both use a WILDCARD (*) at the same level.
        # Explicit definitions override parent wildcards, so those are NOT conflicts.
        conflict_found = False
        if is_explicit_w and is_explicit_b:
            conflict_found = True
            log.debug(f"Explicit conflict found at path: {current_path}")
        # Conflict if both have _all=True at this exact level
        elif node_w.get("_all", False) and node_b.get("_all", False):
            conflict_found = True
            log.debug(f"Wildcard conflict found at path: {current_path}")
        # --- Restore checks against PARENT wildcards --- #
        elif is_explicit_w and parent_all_b:
            conflict_found = True
            log.debug(f"Conflict: Explicit WL vs Parent BL (*) at path: {current_path}")
        elif is_explicit_b and parent_all_w:
            conflict_found = True
            log.debug(f"Conflict: Explicit BL vs Parent WL (*) at path: {current_path}")

        if conflict_found:
            conflicts.append(tuple(current_path))

        # Find common keys to recurse into (excluding internal keys)
        keys_w = {k for k in node_w if not k.startswith("_")}
        keys_b = {k for k in node_b if not k.startswith("_")}
        common_keys = keys_w & keys_b
        # If parent_all_w is True, consider all keys in node_b for recursion
        # If parent_all_b is True, consider all keys in node_w for recursion
        recurse_keys = common_keys
        if parent_all_w:
            recurse_keys.update(keys_b)  # Check all children in blacklist side
        if parent_all_b:
            recurse_keys.update(keys_w)  # Check all children in whitelist side

        for key in sorted(list(recurse_keys)):
            child_node_w = node_w.get(key, {})  # Default to empty dict if key missing
            child_node_b = node_b.get(key, {})  # Default to empty dict if key missing

            # Ensure we are dealing with dicts (could be empty if defaulted)
            if isinstance(child_node_w, dict) and isinstance(child_node_b, dict):
                # Propagate _all status down: current level's _all OR parent's _all
                next_parent_all_w = is_all_w or parent_all_w
                next_parent_all_b = is_all_b or parent_all_b
                _traverse(child_node_w, child_node_b, current_path + [key], next_parent_all_w, next_parent_all_b)

    # Start traversal from the root of both trees
    root_keys = set(whitelist_tree.keys()) | set(blacklist_tree.keys())
    for root_key in sorted(list(root_keys)):
        root_node_w = whitelist_tree.get(root_key, {})  # Default to empty dict
        root_node_b = blacklist_tree.get(root_key, {})  # Default to empty dict
        if isinstance(root_node_w, dict) and isinstance(root_node_b, dict):
            # Pass the initial _all status from the root nodes
            initial_all_w = root_node_w.get("_all", False)
            initial_all_b = root_node_b.get("_all", False)
            _traverse(root_node_w, root_node_b, [root_key], initial_all_w, initial_all_b)

    # Sort for consistent output (optional) - REMOVED
    # return sorted(conflicts)
    return conflicts  # Return the list directly


def get_effective_status(
    sequence: List[str],
    whitelist_tree: ParsedHierarchy,
    blacklist_tree: ParsedHierarchy,
) -> Literal["WHITELISTED", "BLACKLISTED", "UNSPECIFIED"]:
    """Determines the effective status (whitelist/blacklist/unspecified)
       of a command sequence based on hierarchical rules and precedence.

    Precedence Rules:
    1. Explicit match (_explicit=True) at any level beats any wildcard match (_all=True).
    2. A more specific match (deeper path) beats a less specific match (parent path).
    3. If conflicting rules match at the *same* level (e.g., explicit whitelist vs
       explicit blacklist for the exact same sequence), blacklist wins.
       (Note: `check_list_conflicts` should catch identical _explicit flags beforehand).

    Args:
        sequence: The command sequence (e.g., ["tool", "sub", "subsub"]).
        whitelist_tree: Parsed whitelist hierarchy.
        blacklist_tree: Parsed blacklist hierarchy.

    Returns:
        'WHITELISTED', 'BLACKLISTED', or 'UNSPECIFIED'.
    """
    from typing import Literal  # Local import for Literal type hint

    # Track the most specific rule found so far from each list
    # (level, is_explicit, is_all)
    most_specific_whitelist: Optional[Tuple[int, bool, bool]] = None
    most_specific_blacklist: Optional[Tuple[int, bool, bool]] = None

    # --- Traverse Whitelist --- #
    current_level_w = whitelist_tree
    for i, part in enumerate(sequence):
        node_w = current_level_w.get(part)
        level = i + 1

        if isinstance(node_w, dict):
            is_explicit = node_w.get("_explicit", False)
            is_all = node_w.get("_all", False)
            if is_explicit or is_all:
                most_specific_whitelist = (level, is_explicit, is_all)
                break  # <<< FIXED: Stop descent once *any* rule (explicit or all) is found
            # Only continue descent if no rule applied at this level
            current_level_w = node_w
        else:
            break  # Path doesn't exist further

    # --- Traverse Blacklist --- #
    current_level_b = blacklist_tree
    for i, part in enumerate(sequence):
        node_b = current_level_b.get(part)
        level = i + 1

        if isinstance(node_b, dict):
            is_explicit = node_b.get("_explicit", False)
            is_all = node_b.get("_all", False)
            if is_explicit or is_all:
                most_specific_blacklist = (level, is_explicit, is_all)
                break  # <<< FIXED: Stop descent once *any* rule (explicit or all) is found
            # Only continue descent if no rule applied at this level
            current_level_b = node_b
        else:
            break  # Path doesn't exist further

    # --- Determine Final Status --- #

    # Case 1: Neither list has any matching rule
    if most_specific_whitelist is None and most_specific_blacklist is None:
        return "UNSPECIFIED"

    # Case 2: Only one list has a matching rule
    if most_specific_whitelist is None:
        return "BLACKLISTED"
    if most_specific_blacklist is None:
        return "WHITELISTED"

    # Case 3: Both lists have matching rules, apply precedence
    level_w, explicit_w, all_w = most_specific_whitelist
    level_b, explicit_b, all_b = most_specific_blacklist

    # If levels differ, the deeper match wins
    if level_w > level_b:
        return "WHITELISTED"
    if level_b > level_w:
        return "BLACKLISTED"

    # Levels are the same, explicit beats wildcard
    if explicit_w and not explicit_b:
        return "WHITELISTED"
    if explicit_b and not explicit_w:
        return "BLACKLISTED"

    # Same level, both explicit or both wildcard - Blacklist wins tie
    # (check_list_conflicts should prevent explicit_w and explicit_b both being true)
    return "BLACKLISTED"
