import json
from pathlib import Path
import sys
from collections import OrderedDict


def update_command_sequence(json_file_path: Path, base_tools_dir: Path):
    """Reads a JSON file, adds/updates the command_sequence, and writes it back."""
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            # Use OrderedDict to preserve key order upon loading if possible,
            # although standard json library doesn't guarantee it.
            # We ensure order on writing.
            data = json.load(f, object_pairs_hook=OrderedDict)
    except json.JSONDecodeError as e:
        print(f"Error reading {json_file_path}: {e}", file=sys.stderr)
        return False
    except IOError as e:
        print(f"Error opening {json_file_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(
            f"An unexpected error occurred reading {json_file_path}: {e}",
            file=sys.stderr,
        )
        return False

    # Determine the command sequence from the path relative to the base tools dir
    # e.g., ruff/ruff_check.json -> ['ruff', 'check']
    # e.g., bandit/bandit.json -> ['bandit']
    # e.g., poetry/install.json -> ['poetry', 'install']
    relative_path = json_file_path.relative_to(base_tools_dir)
    tool_dir_name = relative_path.parts[0]
    json_stem = json_file_path.stem  # Filename without extension

    derived_sequence = []
    if json_stem == tool_dir_name:
        # e.g., bandit/bandit.json -> ['bandit']
        derived_sequence = [tool_dir_name]
    elif json_stem.startswith(tool_dir_name + "_"):
        # e.g., ruff/ruff_check.json -> ['ruff', 'check']
        subcommand = json_stem[len(tool_dir_name) + 1 :]
        derived_sequence = [tool_dir_name, subcommand]
    else:
        # e.g., poetry/install.json -> ['poetry', 'install']
        # Assumes the stem is the subcommand name directly
        derived_sequence = [tool_dir_name, json_stem]

    # Check if update is needed
    current_sequence = data.get("command_sequence")
    if current_sequence == derived_sequence:
        # No change needed
        return False

    # Create a new ordered dictionary to ensure command_sequence is first
    new_data = OrderedDict()
    new_data["command_sequence"] = derived_sequence

    # Add other keys from the original data
    for key, value in data.items():
        if key != "command_sequence":
            new_data[key] = value

    try:
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=4, ensure_ascii=False)
            f.write("\n")  # Add trailing newline
        print(f"Updated command_sequence in {json_file_path} to {derived_sequence}")
        return True
    except IOError as e:
        print(f"Error writing {json_file_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(
            f"An unexpected error occurred writing {json_file_path}: {e}",
            file=sys.stderr,
        )
        return False


def main():
    # workspace_root = Path(".")  # Assume script is run from workspace root
    # Get script dir, go up 3 levels (dev_scripts -> zeroth_law -> src -> workspace)
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent.parent.parent
    tools_dir = workspace_root / "src/zeroth_law/tools"
    modified_count = 0
    processed_count = 0
    error_count = 0

    if not tools_dir.is_dir():
        print(f"Error: Tools directory not found at {tools_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning for JSON definition files in {tools_dir}...")

    # Iterate through potential tool directories
    for item in tools_dir.iterdir():
        # Process only directories (tool folders)
        if item.is_dir():
            tool_dir = item
            # Find JSON files within the tool directory
            found_json = False
            for json_file in tool_dir.glob("*.json"):
                # Explicitly skip tool_index.json or its backups if they somehow end up here
                if json_file.name.startswith("tool_index.json"):
                    continue

                found_json = True
                processed_count += 1
                try:
                    if update_command_sequence(json_file, tools_dir):
                        modified_count += 1
                except Exception as e:
                    print(f"Critical error processing {json_file}: {e}", file=sys.stderr)
                    error_count += 1
            # if not found_json:
            #     print(f"Warning: No JSON definition files found in directory {tool_dir}")
        # Skip files like tool_index.json at the top level of tools_dir
        elif item.is_file() and item.name == "tool_index.json":
            print(f"Skipping main index file: {item.name}")
        # else:
        #     print(f"Skipping non-directory item: {item.name}")

    print("\n--- Summary ---")
    print(f"Processed {processed_count} potential JSON definition files.")
    print(f"Updated {modified_count} files.")
    if error_count > 0:
        print(f"Encountered {error_count} errors during processing.", file=sys.stderr)
        sys.exit(1)
    else:
        print("Script completed successfully.")
    print("---------------")


if __name__ == "__main__":
    main()
