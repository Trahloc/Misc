#!/usr/bin/env python3
# FILE: src/zeroth_law/dev_scripts/fix_json_schema.py
"""Scans for JSON tool definitions and attempts to fix common structural schema violations."""

import sys
import structlog
import json
import jsonschema
from pathlib import Path
from zeroth_law.common.path_utils import find_project_root

# Add project root to sys.path to ensure correct module resolution
project_root = find_project_root(start_path=Path(__file__).resolve())

# Add project root to sys.path to allow importing 'src.zeroth_law'
_PROJECT_ROOT = project_root  # Use the determined project root
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

log = structlog.get_logger()

# --- Schema Requirements (Simplified) ---
REQUIRED_TOP_LEVEL_KEYS = [
    "command",
    "description",
    "usage",
    "options",
    "arguments",
    "metadata",
]
REQUIRED_METADATA_KEYS = ["ground_truth_crc"]
EXPECTED_ARRAY_KEYS = ["options", "arguments"]
EXPECTED_OBJECT_KEYS = ["metadata", "subcommands_detail"]  # Add others if needed

# Define the set of allowed top-level keys based on the schema
ALLOWED_TOP_LEVEL_KEYS = {
    "command",
    "subcommand",
    "description",
    "usage",
    "options",
    "arguments",
    "subcommands_detail",
    "metadata",
}

# Mapping from simple type name to jsonschema type dict


def fix_json_file_structure(file_path: Path, tool_name: str, command_id: str) -> bool:
    """Attempts to fix common structural schema errors in a JSON file."""
    changed = False
    raw_content = ""
    needs_regeneration = False
    minimal_json_generated = False  # Flag to track if we generated minimal JSON

    # --- Pre-processing: Read, Strip, Validate Basic Structure ---
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
        stripped_content = raw_content.strip()

        if not stripped_content or not (stripped_content.startswith("{") and stripped_content.endswith("}")):
            log.warning(f"[{command_id}] Content is empty or not valid JSON structure. Regenerating minimal structure.")
            needs_regeneration = True
        else:
            # Attempt to parse the stripped content first
            try:
                data = json.loads(stripped_content)
            except json.JSONDecodeError as e:
                log.warning(
                    f"[{command_id}] Content failed initial JSON parsing after stripping ({e}). Regenerating minimal structure."
                )
                needs_regeneration = True

    except Exception as e:
        log.error(f"Error during pre-processing/reading of {file_path.relative_to(_PROJECT_ROOT)}: {e}")
        return False  # Can't proceed if reading failed

    # --- Regenerate Minimal Structure If Needed ---
    if needs_regeneration:
        inferred_subcommand = None
        if command_id != tool_name:
            possible_subcommand = command_id.replace(f"{tool_name}_", "", 1)
            if possible_subcommand != command_id:
                inferred_subcommand = possible_subcommand

        data = {
            "command": tool_name,
            "subcommand": inferred_subcommand,
            "description": f"(Placeholder description for {command_id})",
            "usage": f"{tool_name} {inferred_subcommand or ''} [OPTIONS]".strip(),
            "options": [],
            "arguments": [],
            "metadata": {"ground_truth_crc": "0x00000000"},  # Ensure essential metadata key
        }
        changed = True  # Mark as changed since we regenerated content
        minimal_json_generated = True
        log.info(f"[{command_id}] Generated minimal JSON structure.")

    # --- Apply Standard Fixes (Original logic starts here) ---
    try:
        original_data_str = json.dumps(data)  # Use current data state for comparison

        # --- Fix 1: Ensure command/subcommand exist (Now mostly handled by regeneration, but keep for edge cases) ---
        command_key_missing = "command" not in data
        subcommand_key_missing = "subcommand" not in data

        if command_key_missing:
            log.info(f"[{command_id}] Adding missing 'command': {tool_name}")
            data["command"] = tool_name
            changed = True
        # --- NEW: Explicitly check and fix type of existing 'command' key ---
        elif not isinstance(data.get("command"), str) and data.get("command") is not None:
            log.warning(f"[{command_id}] Fixing non-string type for 'command' key: {data.get('command')}")
            # Attempt recovery if it's a list with one string element
            if isinstance(data["command"], list) and len(data["command"]) == 1 and isinstance(data["command"][0], str):
                data["command"] = data["command"][0]
            else:
                data["command"] = tool_name  # Fallback to tool_name
            changed = True

        if subcommand_key_missing:
            # Infer subcommand only if it wasn't already present and tool_id differs from tool_name
            inferred_subcommand = None
            if command_id != tool_name:
                # Attempt to infer from command_id (filename stem)
                possible_subcommand = command_id.replace(f"{tool_name}_", "", 1)
                if possible_subcommand != command_id:  # Check if replacement happened
                    inferred_subcommand = possible_subcommand

            log.info(f"[{command_id}] Adding missing 'subcommand' during standard fixes: {inferred_subcommand}")
            data["subcommand"] = inferred_subcommand  # Will be None if not inferred
            changed = True
        # --- NEW: Explicitly check and fix type of existing 'subcommand' key ---
        elif not isinstance(data.get("subcommand"), (str, type(None))):
            log.warning(
                f"[{command_id}] Fixing non-string/non-null type for 'subcommand' key: {data.get('subcommand')}"
            )
            # Attempt recovery if it's a list with one string element
            if (
                isinstance(data["subcommand"], list)
                and len(data["subcommand"]) == 1
                and isinstance(data["subcommand"][0], str)
            ):
                data["subcommand"] = data["subcommand"][0]
            else:
                data["subcommand"] = None  # Fallback to None
            changed = True

        # --- Fix 2: Ensure top-level keys exist with placeholders ---
        if "description" not in data or not data["description"]:
            log.info(f"[{command_id}] Adding placeholder description.")
            data["description"] = f"(Placeholder description for {command_id})"
            changed = True
        if "usage" not in data or not data["usage"]:
            log.info(f"[{command_id}] Adding placeholder usage.")
            data["usage"] = (
                f"{data.get('command', '?')} {data.get('subcommand', '') or ''} [OPTIONS]"  # Basic placeholder
            )
            changed = True

        # --- Fix 3: Ensure specific keys are arrays ---
        for key in EXPECTED_ARRAY_KEYS:
            if key not in data or not isinstance(data[key], list):
                log.info(f"[{command_id}] Ensuring '{key}' is an array.")
                data[key] = []
                changed = True

        # --- Fix 4: Ensure specific keys are objects (if they exist) ---
        # This won't add them if missing, only corrects type if present but wrong
        for key in EXPECTED_OBJECT_KEYS:
            if key in data and not isinstance(data[key], dict):
                log.info(f"[{command_id}] Ensuring '{key}' is an object/dict.")
                data[key] = {}
                changed = True

        # --- Fix 5: Ensure metadata block and its required keys ---
        if "metadata" not in data or not isinstance(data["metadata"], dict):
            log.info(f"[{command_id}] Adding missing 'metadata' object.")
            data["metadata"] = {}
            changed = True

        metadata = data["metadata"]
        if "tool_name" not in metadata:
            log.info(f"[{command_id}] Adding missing metadata.tool_name: {tool_name}")
            metadata["tool_name"] = tool_name
            changed = True
        if "command_name" not in metadata:
            # Infer command name, ensuring it's a string
            inferred_cmd_value = data.get("subcommand") or data.get("command")
            final_cmd_name = None
            if isinstance(inferred_cmd_value, list) and inferred_cmd_value:
                # If it's a non-empty list, take the first element
                final_cmd_name = str(inferred_cmd_value[0])
                log.warning(
                    f"[{command_id}] Inferred command/subcommand was a list ({inferred_cmd_value}). Using first element: {final_cmd_name}"
                )
            elif isinstance(inferred_cmd_value, str):
                final_cmd_name = inferred_cmd_value
            elif inferred_cmd_value is not None:
                # Handle other unexpected types by converting to string
                final_cmd_name = str(inferred_cmd_value)
                log.warning(
                    f"[{command_id}] Inferred command/subcommand had unexpected type ({type(inferred_cmd_value)}). Converting to string: {final_cmd_name}"
                )
            else:
                # Fallback if command/subcommand are missing or null
                final_cmd_name = tool_name  # Use tool_name as last resort
                log.warning(f"[{command_id}] Could not infer command/subcommand, using tool_name: {final_cmd_name}")

            log.info(f"[{command_id}] Adding missing metadata.command_name: {final_cmd_name}")
            metadata["command_name"] = final_cmd_name
            changed = True
        if "ground_truth_crc" not in metadata:
            log.info(f"[{command_id}] Adding missing metadata.ground_truth_crc with skeleton value.")
            metadata["ground_truth_crc"] = "0x00000000"
            changed = True

        # --- Fix 6: Remove invalid top-level 'subcommands' key ---
        if "subcommands" in data:
            log.info(f"[{command_id}] Removing invalid top-level 'subcommands' key.")
            del data["subcommands"]
            changed = True

        # --- Fix 7: Remove invalid top-level 'examples' key ---
        if "examples" in data:
            log.info(f"[{command_id}] Removing invalid top-level 'examples' key.")
            del data["examples"]
            changed = True

        # --- Fix 8: Remove invalid top-level 'schema_version' key ---
        if "schema_version" in data:
            log.info(f"[{command_id}] Removing invalid top-level 'schema_version' key.")
            del data["schema_version"]
            changed = True

        # --- NEW Fix: Remove invalid top-level 'command_sequence' key (from yamllint error) ---
        if "command_sequence" in data:
            log.info(f"[{command_id}] Removing invalid top-level 'command_sequence' key.")
            del data["command_sequence"]
            changed = True

        # --- NEW Fix: Remove *any* unexpected top-level keys ---
        keys_to_remove = set(data.keys()) - ALLOWED_TOP_LEVEL_KEYS
        if keys_to_remove:
            for key in keys_to_remove:
                log.info(f"[{command_id}] Removing unexpected top-level key: '{key}'")
                del data[key]
            changed = True

        # --- Fix 9: Remove options where 'name' is null or missing ---
        if "options" in data and isinstance(data["options"], list):
            original_options_count = len(data["options"])
            # Filter in place by creating a new list
            data["options"] = [opt for opt in data["options"] if isinstance(opt, dict) and opt.get("name")]
            if len(data["options"]) != original_options_count:
                log.info(
                    f"[{command_id}] Removed {original_options_count - len(data['options'])} options with null/missing names."
                )
                changed = True

        # --- NEW Fix: Ensure option/argument descriptions are strings, replace null with "" ---
        for key_to_check in ["options", "arguments"]:
            if key_to_check in data and isinstance(data[key_to_check], list):
                for item in data[key_to_check]:
                    if isinstance(item, dict) and "description" in item and item["description"] is None:
                        log.info(
                            f"[{command_id}] Replacing null description with empty string in {key_to_check}: {item.get('name')}"
                        )
                        item["description"] = ""
                        changed = True

        # --- NEW Check: Validate subcommands_detail structure (missing json_definition) ---
        if "subcommands_detail" in data and isinstance(data["subcommands_detail"], dict):
            for sub_name, sub_detail in data["subcommands_detail"].items():
                if isinstance(sub_detail, dict):
                    if "description" not in sub_detail:
                        log.warning(
                            f"[{command_id}] Subcommand '{sub_name}' in subcommands_detail is missing 'description'. Adding placeholder."
                        )
                        sub_detail["description"] = f"(Placeholder for {sub_name})"
                        changed = True
                    if "json_definition" not in sub_detail:
                        # Log a warning/error - requiring manual intervention is safer -> CHANGED: Add placeholder instead
                        # log.error(f"[{command_id}] FATAL SCHEMA ERROR: Subcommand '{sub_name}' in subcommands_detail is MISSING required 'json_definition' key. Manual correction needed in {file_path.name}")
                        # Optionally, could try to add a placeholder, but this is risky:
                        placeholder_path = f"./{sub_name}.json"  # Simple derivation based on subcommand name
                        log.warning(
                            f"[{command_id}] Subcommand '{sub_name}' in subcommands_detail is missing required 'json_definition' key. Adding placeholder: {placeholder_path}"
                        )
                        sub_detail["json_definition"] = placeholder_path
                        changed = True
                else:
                    log.warning(
                        f"[{command_id}] Invalid item found in subcommands_detail for key '{sub_name}'. Expected an object."
                    )

        # --- Save if changed (Adjusted Logic) ---
        if changed:
            final_data_str = json.dumps(data, indent=2)
            # Determine if we should add a newline based on original content (if valid)
            # or always add if we generated minimal JSON from scratch.
            add_newline = True  # Default to adding newline
            if not minimal_json_generated and not needs_regeneration:
                # If we started with valid-looking content, respect original ending
                if raw_content.endswith("\n"):
                    add_newline = True
                elif stripped_content == final_data_str:  # Check if *only* formatting changed
                    add_newline = raw_content.endswith("\n")  # Keep original ending
                else:
                    # Content changed beyond formatting, default to adding newline
                    add_newline = True
            # Only write if the final formatted string differs from the original raw content
            # OR if we regenerated the minimal structure
            if minimal_json_generated or final_data_str != stripped_content:
                log.info(f"Saving structural fixes for: {file_path.relative_to(_PROJECT_ROOT)}")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(final_data_str)
                    if add_newline:
                        f.write("\n")
                return True
            else:
                log.debug(f"[{command_id}] No effective change after attempting fixes.")
                return False  # No effective change
        else:
            return False  # No change needed

    except Exception as e:
        # Log error during standard fixing phase
        log.error(
            f"Error processing structure for file {file_path.relative_to(_PROJECT_ROOT)} during standard fixes: {e}"
        )
        return False


def main():
    """Main function to find and fix JSON files."""
    log.info("Starting JSON structural schema fix scan...")
    project_root = find_project_root(Path(__file__).parent)
    if not project_root:
        log.error("Could not find project root. Exiting.")
        sys.exit(1)

    tools_dir = project_root / "src" / "zeroth_law" / "tools"
    if not tools_dir.is_dir():
        log.error(f"Tools directory not found at {tools_dir}. Exiting.")
        sys.exit(1)

    json_files = list(tools_dir.rglob("*.json"))
    log.info(f"Found {len(json_files)} JSON files to check in {tools_dir.relative_to(project_root)}.")

    files_fixed = 0
    files_error = 0

    for json_file in json_files:
        if json_file.name == "tool_index.json":  # Skip the main index
            continue
        try:
            # Infer tool_name and command_id from path
            tool_name = json_file.parent.name
            command_id = json_file.stem  # Filename without extension
            if fix_json_file_structure(json_file, tool_name, command_id):
                files_fixed += 1
        except Exception as e:
            log.exception(f"Unexpected error during processing of {json_file}: {e}")
            files_error += 1

    log.info(f"JSON structural fix scan complete. Fixed: {files_fixed} file(s). Errors: {files_error}.")
    if files_error > 0:
        sys.exit(1)  # Exit with error if any file processing failed


if __name__ == "__main__":
    main()
