import json
import zlib
import sys
from pathlib import Path
from collections import OrderedDict
import yaml

# --- Configuration ---
# Assuming script is run from workspace root
WORKSPACE_ROOT = Path(".").resolve()
TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
MANAGED_TOOLS_YAML = WORKSPACE_ROOT / "src" / "zeroth_law" / "managed_tools.yaml"

# --- Helper Functions ---


def calculate_crc32_hex(content_bytes: bytes) -> str:
    """Calculates the CRC32 checksum and returns it as an uppercase hex string prefixed with 0x."""
    # IMPORTANT: zlib.crc32 returns a signed integer on some Python versions/platforms.
    # We need to convert it to an unsigned 32-bit integer.
    crc_val = zlib.crc32(content_bytes) & 0xFFFFFFFF
    # Format as 8-character uppercase hex string, prefixed with 0x
    return f"0x{crc_val:08X}"


def command_sequence_to_id(command_parts: list[str]) -> str:
    """Creates a file/tool ID from a command sequence list."""
    # Handles simple cases like ['ruff'] -> 'ruff'
    # and complex cases like ['ruff', 'check', '--fix'] -> 'ruff_check_--fix'
    # Note: This needs to precisely match how IDs are generated for filenames.
    # Assuming simple underscore joining for now based on previous context.
    return "_".join(command_parts)


def load_managed_tools(yaml_path: Path) -> list[str]:
    """Loads the list of managed tool names from the YAML config."""
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            managed = data.get("managed_tools", [])
            if not isinstance(managed, list):
                print(f"Error: 'managed_tools' key in {yaml_path} is not a list.", file=sys.stderr)
                return []
            return managed
    except FileNotFoundError:
        print(f"Error: Managed tools file not found at {yaml_path}", file=sys.stderr)
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {yaml_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Unexpected error loading {yaml_path}: {e}", file=sys.stderr)
        return []


# --- Main Logic ---


def main():
    print(f"Starting JSON CRC update process...")
    print(f"Workspace Root: {WORKSPACE_ROOT}")
    print(f"Tools Directory: {TOOLS_DIR}")
    print(f"Managed Tools Config: {MANAGED_TOOLS_YAML}")

    managed_tool_names = load_managed_tools(MANAGED_TOOLS_YAML)
    if not managed_tool_names:
        print("Error: No managed tools loaded. Exiting.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(managed_tool_names)} managed tool entries: {managed_tool_names}")

    updated_count = 0
    checked_count = 0
    error_count = 0

    # Iterate through managed tools - Assuming for now each name corresponds to a directory
    # and the primary command sequence is just the tool name itself.
    # TODO: This needs refinement if managed_tools contains complex command sequences directly.
    for tool_name in managed_tool_names:
        # Simplistic assumption: command sequence is just the tool name
        command_sequence = [tool_name]
        tool_id = command_sequence_to_id(command_sequence)

        tool_dir = TOOLS_DIR / tool_name
        txt_file_path = tool_dir / f"{tool_id}.txt"
        json_file_path = tool_dir / f"{tool_id}.json"

        print(f"\nProcessing Tool: '{tool_name}' (ID: {tool_id})")
        checked_count += 1

        # 1. Check and Read TXT file
        if not txt_file_path.is_file():
            print(f"  - Skipping: TXT baseline not found at {txt_file_path.relative_to(WORKSPACE_ROOT)}")
            continue  # Skip if no baseline exists

        try:
            txt_content_bytes = txt_file_path.read_bytes()
            # Normalize line endings for CRC calculation (read_bytes preserves original)
            txt_content_normalized = txt_content_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        except IOError as e:
            print(f"  - Error reading TXT file {txt_file_path.relative_to(WORKSPACE_ROOT)}: {e}", file=sys.stderr)
            error_count += 1
            continue
        except Exception as e:
            print(
                f"  - Unexpected error reading TXT file {txt_file_path.relative_to(WORKSPACE_ROOT)}: {e}",
                file=sys.stderr,
            )
            error_count += 1
            continue

        # 2. Calculate CRC from TXT
        try:
            calculated_crc = calculate_crc32_hex(txt_content_normalized)
            print(f"  - Calculated TXT CRC: {calculated_crc}")
        except Exception as e:
            print(f"  - Error calculating CRC for {txt_file_path.relative_to(WORKSPACE_ROOT)}: {e}", file=sys.stderr)
            error_count += 1
            continue

        # 3. Check and Read JSON file
        if not json_file_path.is_file():
            print(
                f"  - Warning: JSON definition not found at {json_file_path.relative_to(WORKSPACE_ROOT)}. Cannot update CRC."
            )
            # Consider this a warning, not necessarily an error unless consistency is strictly required now.
            continue

        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                # Use OrderedDict to preserve key order
                json_data = json.load(f, object_pairs_hook=OrderedDict)
        except json.JSONDecodeError as e:
            print(f"  - Error decoding JSON file {json_file_path.relative_to(WORKSPACE_ROOT)}: {e}", file=sys.stderr)
            error_count += 1
            continue
        except IOError as e:
            print(f"  - Error reading JSON file {json_file_path.relative_to(WORKSPACE_ROOT)}: {e}", file=sys.stderr)
            error_count += 1
            continue
        except Exception as e:
            print(
                f"  - Unexpected error reading JSON file {json_file_path.relative_to(WORKSPACE_ROOT)}: {e}",
                file=sys.stderr,
            )
            error_count += 1
            continue

        # 4. Get current CRC from JSON metadata
        metadata = json_data.get("metadata")
        if not isinstance(metadata, dict):
            print(
                f"  - Warning: Missing or invalid 'metadata' dictionary in {json_file_path.relative_to(WORKSPACE_ROOT)}. Cannot update CRC."
            )
            continue

        current_json_crc = metadata.get("ground_truth_crc")
        if current_json_crc is None:
            print(
                f"  - Warning: Missing 'metadata.ground_truth_crc' in {json_file_path.relative_to(WORKSPACE_ROOT)}. Cannot compare/update."
            )
            continue

        print(f"  - Current JSON CRC:  {current_json_crc}")

        # 5. Compare and Update if needed (Case-insensitive compare)
        if str(current_json_crc).lower() == calculated_crc.lower():
            print(f"  - CRCs match. No update needed for {json_file_path.relative_to(WORKSPACE_ROOT)}.")
        else:
            print(f"  - CRCs differ. Updating JSON CRC to {calculated_crc}.")
            metadata["ground_truth_crc"] = calculated_crc
            # Optionally update a timestamp here if desired
            # metadata["crc_updated_timestamp"] = datetime.now(timezone.utc).isoformat()

            # 6. Write JSON file back
            try:
                with open(json_file_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=4, ensure_ascii=False)
                    f.write("\n")  # Add trailing newline
                print(f"  - Successfully updated {json_file_path.relative_to(WORKSPACE_ROOT)}.")
                updated_count += 1
            except IOError as e:
                print(
                    f"  - Error writing updated JSON file {json_file_path.relative_to(WORKSPACE_ROOT)}: {e}",
                    file=sys.stderr,
                )
                error_count += 1
            except Exception as e:
                print(
                    f"  - Unexpected error writing JSON file {json_file_path.relative_to(WORKSPACE_ROOT)}: {e}",
                    file=sys.stderr,
                )
                error_count += 1

    # --- Summary --- #
    print("\n--- JSON CRC Update Summary ---")
    print(f"Checked {checked_count} managed tool entries.")
    print(f"Updated {updated_count} JSON files.")
    if error_count > 0:
        print(f"Encountered {error_count} errors during processing.", file=sys.stderr)
        sys.exit(1)
    else:
        print("Script completed successfully.")
    print("-------------------------------")


if __name__ == "__main__":
    # Add basic error handling for PyYAML import
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML library is required. Please install it ('pip install pyyaml')", file=sys.stderr)
        sys.exit(1)

    main()
