import json
import os
import glob
from pathlib import Path
import sys


def transform_option(option):
    """Transforms a single option dictionary to the new schema."""
    new_option = {}
    aliases = []

    # Preserve original name and description
    new_option["name"] = option.get("name")
    new_option["description"] = option.get("description")

    # Handle aliases (short_name, alternative_names)
    if "short_name" in option and option["short_name"]:
        aliases.append(option["short_name"])
    if "alternative_names" in option and option["alternative_names"]:
        aliases.extend(option["alternative_names"])
    # Keep existing aliases if the field is already present
    if "aliases" in option:
        # Ensure existing aliases are also included, avoiding duplicates
        aliases.extend([a for a in option["aliases"] if a not in aliases])

    new_option["aliases"] = sorted(list(set(aliases)))  # Ensure uniqueness and order

    # Handle argument (takes_value, value_placeholder)
    takes_value = option.get("takes_value", False)  # Default to False if missing
    value_placeholder = option.get("value_placeholder")

    if takes_value:
        # Use value_placeholder if available, otherwise use a generic placeholder
        new_option["argument"] = value_placeholder if value_placeholder else "VALUE"
    else:
        new_option["argument"] = None

    # Handle required (add if missing, default to false)
    new_option["required"] = option.get("required", False)

    # Handle nargs (preserve if present)
    if "nargs" in option:
        new_option["nargs"] = option["nargs"]

    # Handle allow_multiple (add if missing, default to false)
    new_option["allow_multiple"] = option.get("allow_multiple", False)

    # Remove old keys if they somehow exist in the new dict (shouldn't happen with new_option init)
    # new_option.pop('short_name', None)
    # new_option.pop('takes_value', None)
    # new_option.pop('value_placeholder', None)
    # new_option.pop('alternative_names', None)

    return new_option


def transform_argument(argument):
    """Transforms a single argument dictionary to the new schema."""
    new_argument = argument.copy()  # Start with existing fields

    # Handle optional -> required conversion
    if "optional" in argument:
        new_argument["required"] = not argument["optional"]
        del new_argument["optional"]
    elif "required" not in argument:  # Add required if missing, default false
        new_argument["required"] = False

    return new_argument


def correct_schema(file_path):
    """Reads, corrects, and writes the JSON schema if necessary."""
    try:
        with open(file_path, "r") as f:
            content = f.read()
            # Handle potential trailing newline causing JSON errors
            if not content.strip():
                print(f"Skipping empty file: {file_path}")
                return False
            data = json.loads(content.strip())
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {file_path}: {e}", file=sys.stderr)
        print(f"Problematic content snippet:\n---\n{content[:200]}\n---", file=sys.stderr)
        raise  # Re-raise to stop the script
    except FileNotFoundError:
        print(f"Error: File not found {file_path}", file=sys.stderr)
        raise  # Re-raise to stop the script
    except Exception as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        raise  # Re-raise to stop the script

    original_data_str = json.dumps(data, sort_keys=True)  # For comparison later
    made_changes = False

    # --- Schema Corrections ---

    # 1. command_sequence -> command, subcommand
    if "command_sequence" in data and isinstance(data["command_sequence"], list):
        seq = data["command_sequence"]
        data["command"] = seq[0] if len(seq) > 0 else None
        data["subcommand"] = seq[1] if len(seq) > 1 else None
        del data["command_sequence"]
        made_changes = True
        # Ensure command/subcommand exist even if sequence was empty/short
        if "command" not in data:
            data["command"] = None
        if "subcommand" not in data:
            data["subcommand"] = None

    # 2. Arguments: optional -> required
    if "arguments" in data and isinstance(data["arguments"], list):
        new_args = []
        changed_args = False
        for arg in data["arguments"]:
            new_arg = transform_argument(arg)
            new_args.append(new_arg)
            if new_arg != arg:
                changed_args = True
        if changed_args:
            data["arguments"] = new_args
            made_changes = True

    # 3. Options: short_name, takes_value, etc. -> aliases, argument, etc.
    if "options" in data and isinstance(data["options"], list):
        new_opts = []
        changed_opts = False
        for opt in data["options"]:
            # Check if old keys exist before transforming
            needs_transform = any(
                k in opt for k in ["short_name", "takes_value", "value_placeholder", "alternative_names"]
            )
            # Also check if new keys are missing defaults
            needs_transform = needs_transform or any(
                k not in opt for k in ["aliases", "argument", "required", "allow_multiple"]
            )

            if needs_transform:
                new_opt = transform_option(opt)
                new_opts.append(new_opt)
                changed_opts = True
            else:
                new_opts.append(opt)  # Keep as is if no transform needed

        if changed_opts:
            data["options"] = new_opts
            made_changes = True

    # 4. subcommands -> subcommands_detail
    if "subcommands" in data and "subcommands_detail" not in data:
        data["subcommands_detail"] = data.pop("subcommands")
        made_changes = True
    elif "subcommands" in data and "subcommands_detail" in data:
        # Edge case: both exist somehow? Prefer subcommands_detail, discard subcommands
        del data["subcommands"]
        made_changes = True  # Technically a change

    # --- End Schema Corrections ---

    corrected_data_str = json.dumps(data, sort_keys=True)

    # Check if actual content changed after applying logic
    if original_data_str == corrected_data_str and not made_changes:
        # print(f"No schema changes needed for: {file_path}")
        return False  # No logical changes applied

    # Write back if changes were made
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
            f.write("\n")  # Add trailing newline
        print(f"Corrected schema for: {file_path}")
        return True
    except Exception as e:
        print(f"Error writing file {file_path}: {e}", file=sys.stderr)
        raise  # Re-raise to stop the script


def find_tool_json_files(base_dir):
    """Finds all potential tool definition JSON files."""
    json_files = []
    base_path = Path(base_dir)
    # Iterate through items in the base directory
    for item in base_path.iterdir():
        if item.is_dir():
            # Find JSON files directly in the tool directory
            # Exclude known non-definition files explicitly if necessary
            tool_dir_files = list(item.glob("*.json"))
            # Try to find nested definition files (e.g., tool/subcommand.json)
            nested_files = list(item.glob("*/*.json"))
            # Combine and filter - simple approach: take all JSON for now
            # A more refined approach might check filenames against dir name
            all_files = tool_dir_files + nested_files
            for f_path in all_files:
                # Basic check to exclude index/backup files by name pattern
                if "tool_index" not in f_path.name and ".bak" not in f_path.name:
                    json_files.append(str(f_path))
    return json_files


if __name__ == "__main__":
    tools_base_dir = "src/zeroth_law/tools/"
    print(f"Scanning for tool JSON files in {tools_base_dir}...")

    try:
        json_files_to_check = find_tool_json_files(tools_base_dir)
    except Exception as e:
        print(f"Error finding JSON files: {e}", file=sys.stderr)
        sys.exit(1)

    if not json_files_to_check:
        print("No JSON files found to check.")
        sys.exit(0)

    print(f"Found {len(json_files_to_check)} potential tool JSON files.")
    # print("\n".join(json_files_to_check)) # Optional: list files

    corrected_count = 0
    checked_count = 0

    for file_path in sorted(json_files_to_check):
        checked_count += 1
        try:
            was_corrected = correct_schema(file_path)
            if was_corrected:
                corrected_count += 1
        except Exception as e:
            # Error message already printed in correct_schema or file reading
            print(f"Script stopped due to error in file: {file_path}", file=sys.stderr)
            sys.exit(1)  # Stop script on first error

    print(f"\nScan complete. Checked {checked_count} files.")
    print(f"Corrected {corrected_count} files.")
    sys.exit(0)