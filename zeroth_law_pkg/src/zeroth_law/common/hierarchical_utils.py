"""Utilities for handling hierarchical list structures (whitelist/blacklist)."""

import structlog
from typing import List, Dict, Union, Optional

log = structlog.get_logger()

# --- Type Hint for Nested Structure --- #
# Represents the hierarchical structure: Dict[node_name, NodeDict]
# Special keys: '_explicit' (bool), '_all' (bool)
NodeData = Dict[str, Union[bool, "NodeData"]]  # Recursive type hint
ParsedHierarchy = Dict[str, NodeData]

# --- Parsing --- #


def parse_to_nested_dict(raw_list: List[str]) -> ParsedHierarchy:
    """Parses a list of strings with hierarchy into a nested dictionary.

    Handles entries like "tool", "tool:*", "tool:sub", "tool:sub:subsub", "tool:sub:*".
    Uses special keys '_explicit' and '_all' within nodes.
    Comma separation applies only to the *last* component.
    """
    root: ParsedHierarchy = {}

    if not isinstance(raw_list, list):
        log.warning(
            "Managed tools list is not a valid list. Returning empty structure.", received_type=type(raw_list).__name__
        )
        return {}

    for entry in raw_list:
        if not isinstance(entry, str):
            log.warning("Ignoring non-string entry in managed tools list.", entry=entry)
            continue

        entry = entry.strip()
        if not entry:
            continue

        # --- Pre-split Validation --- #
        if entry == ":*" or entry.startswith(":") or entry.endswith("::") or "::" in entry:
            log.warning(f"Skipping entry '{entry}' due to invalid empty component pattern.")
            continue
        # --- End Pre-split Validation --- #

        parts = entry.split(":")
        is_fully_listed_at_end = False
        if parts[-1] == "*":
            if len(parts) == 1:
                continue  # Already caught by pre-split validation
            is_fully_listed_at_end = True
            parts = parts[:-1]

        # --- Validate path components --- #
        valid_path = True
        cleaned_parts = []
        num_parts = len(parts)
        for i, part in enumerate(parts):
            stripped_part = part.strip()
            is_last_part = i == num_parts - 1

            # Allow a *single* trailing empty component, but disallow others
            if not stripped_part:
                if is_last_part and i > 0:  # Allow if it's the last part AND not the only part (e.g. ":")
                    log.debug(f"Ignoring trailing empty component in entry '{entry}'.")
                    continue  # Skip adding the empty part to cleaned_parts
                else:
                    # Disallow empty components elsewhere (e.g., "::", ":tool", ":")
                    log.warning(f"Skipping entry '{entry}' due to invalid empty component at index {i}.")
                    valid_path = False
                    break

            # Check for commas in non-final parts
            if not is_last_part and "," in stripped_part:
                log.warning(f"Skipping entry '{entry}': Commas are only allowed in the final component.")
                valid_path = False
                break
            cleaned_parts.append(stripped_part)

        # Ensure cleaned_parts is not empty after potential trailing part removal
        if not cleaned_parts:
            log.warning(f"Skipping entry '{entry}' as it resulted in no valid components.")
            valid_path = False

        if not valid_path:
            continue  # Skip this whole entry

        # --- Process validated path --- #
        current_level = root
        path_accumulator = []
        for i, part in enumerate(cleaned_parts):
            path_accumulator.append(part)
            is_last_part = i == len(cleaned_parts) - 1
            node_names = (
                [p.strip() for p in part.split(",") if p.strip()] if is_last_part else [part]
            )  # Use validated part

            # This should not happen now due to earlier validation, but check defensively
            if not node_names:
                log.error(f"Internal error: Empty node_names after validation for entry '{entry}'")
                break

            next_level_holders = []
            for node_name in node_names:
                # Get or create node
                node = current_level.setdefault(node_name, {})
                if not isinstance(node, dict):
                    log.error(
                        f"Config structure error: Trying to create node '{node_name}' where a boolean flag exists.",
                        path=path_accumulator,
                    )
                    # How to recover? Maybe skip this node_name? For now, log and continue.
                    continue

                # Handle :* overriding existing children
                if is_last_part and is_fully_listed_at_end:
                    keys_to_delete = [k for k in node if not k.startswith("_")]
                    if keys_to_delete:
                        log.debug(
                            f"Parser: Clearing children of '{node_name}' due to override by ':*' in entry '{entry}'"
                        )
                    for k in keys_to_delete:
                        del node[k]

                # Set flags if last part
                if is_last_part:
                    node["_explicit"] = True
                    if is_fully_listed_at_end:
                        node["_all"] = True
                elif not is_last_part:  # Prepare for descent
                    if node.get("_all", False):
                        # This entry is trying to define something under an _all node, which is disallowed.
                        # This case should be caught by validation ideally, but double-check here.
                        log.warning(
                            f"Parser: Cannot define sub-nodes under '{node_name}' (path: {':'.join(path_accumulator)}) as it is marked with ':*'. Skipping deeper parts of entry '{entry}'"
                        )
                        # Mark entry as invalid? Or just stop descent?
                        current_level = None  # Signal error/stop
                        break  # Break inner node_names loop
                    next_level_holders.append(node)

            if current_level is None:  # Check if inner loop signalled stop
                break  # Break outer parts loop

            # Descend
            if not is_last_part:
                if not next_level_holders:  # Should not happen
                    log.error(f"Internal parser error: No valid next level found for entry '{entry}' at part {i}")
                    break
                current_level = next_level_holders[0]

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
            log.debug(f"Node '{part}' not found at path {''.join(path[:len(path)-len(current_path)])}. Cannot remove.")
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
            node["_explicit"] = is_explicit
            made_change = True
        # --- Added Else --- #
        # else: # Value is same, no change made for explicit flag
        #     pass

    # Update _all only if value is provided and different
    if is_all is not None:
        current_all = node.get("_all", False)
        if current_all != is_all:
            node["_all"] = is_all
            made_change = True
            if is_all:  # If setting _all=True, remove deeper nodes
                keys_to_delete = [k for k in node if not k.startswith("_")]
                if keys_to_delete:
                    log.debug(f"Clearing children of node at '{path}' because _all=True is being set.")
                    for k in keys_to_delete:
                        del node[k]
                    made_change = True  # Deleting children is a change
        # --- Added Else --- #
        # else: # Value is same, no change made for all flag
        #    pass

    # Return True ONLY if a flag was actually changed or children were deleted
    return made_change
