import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def remove_file_status_field():
    """
    Removes the 'file_status' field from the 'metadata' object in all
    tool JSON files under 'src/zeroth_law/tools/'.
    This is a temporary script to clean up a deprecated field.
    """
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent  # Assumes script is in 'scripts/'
    tools_base_dir = workspace_root / "src" / "zeroth_law" / "tools"

    if not tools_base_dir.is_dir():
        log.error(f"Tools base directory not found: {tools_base_dir}")
        return

    log.info(f"Scanning for tool JSON files in subdirectories of: {tools_base_dir}")

    modified_count = 0
    error_count = 0
    processed_count = 0

    # Iterate through tool directories first
    for tool_dir in tools_base_dir.iterdir():
        if not tool_dir.is_dir():
            continue

        # Look for JSON files within each tool directory
        for json_file in tool_dir.glob("*.json"):
            processed_count += 1
            relative_path = json_file.relative_to(workspace_root)
            log.debug(f"Processing: {relative_path}")
            was_modified = False
            try:
                # Read the JSON file
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Check and remove the field
                if isinstance(data, dict):
                    metadata = data.get("metadata")
                    if isinstance(metadata, dict) and "file_status" in metadata:
                        log.info(f"  Removing 'metadata.file_status' from: {relative_path}")
                        del metadata["file_status"]
                        # If metadata becomes empty after removal, optionally remove it too?
                        # if not metadata:
                        #     del data["metadata"]
                        was_modified = True

                # Write back if modified
                if was_modified:
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)  # Use indent=2 for readability
                        f.write("\n")  # Add trailing newline
                    modified_count += 1

            except json.JSONDecodeError as e:
                log.error(f"  Error decoding JSON file {relative_path}: {e}")
                error_count += 1
            except Exception as e:
                log.error(f"  Error processing file {relative_path}: {e}")
                error_count += 1

    log.info("-" * 30)
    log.info(f"Scan finished. Processed {processed_count} JSON files.")
    if modified_count > 0:
        log.info(f"Removed 'metadata.file_status' from {modified_count} files.")
    else:
        log.info("No JSON files required modification.")

    if error_count > 0:
        log.warning(f"{error_count} errors occurred during processing.")


if __name__ == "__main__":
    remove_file_status_field()
    log.info(
        "Script finished. Remember to delete this script ('scripts/temp_remove_file_status.py') if it's no longer needed."
    )
