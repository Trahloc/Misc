import logging
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def cleanup_tool_txt_dirs():
    """
    Moves TXT files from 'src/zeroth_law/tools/<tool>/txt/' to
    'src/zeroth_law/tools/<tool>/' and removes the empty 'txt' subdirectory.
    This is a temporary script to fix a previous mistake in directory structure.
    """
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent  # Assumes script is in 'scripts/' directory
    tools_base_dir = workspace_root / "src" / "zeroth_law" / "tools"
    txt_subdir_name = "txt"

    if not tools_base_dir.is_dir():
        log.error(f"Tools base directory not found: {tools_base_dir}")
        return

    log.info(f"Scanning for tool directories in: {tools_base_dir}")

    cleaned_count = 0
    error_count = 0

    for tool_dir in tools_base_dir.iterdir():
        if not tool_dir.is_dir():
            continue

        txt_dir = tool_dir / txt_subdir_name
        if txt_dir.is_dir():
            log.info(f"Found '{txt_subdir_name}' directory in: {tool_dir.relative_to(workspace_root)}")
            try:
                # Move files from txt_dir to tool_dir
                files_moved = 0
                for item in txt_dir.iterdir():
                    source_path = item
                    dest_path = tool_dir / item.name
                    if item.is_file():
                        log.info(
                            f"  Moving '{source_path.relative_to(workspace_root)}' -> '{dest_path.relative_to(workspace_root)}'"
                        )
                        shutil.move(str(source_path), str(dest_path))
                        files_moved += 1
                    else:
                        log.warning(f"  Skipping non-file item in txt dir: {item.relative_to(workspace_root)}")

                # Remove the now potentially empty txt_dir
                if files_moved > 0 or not list(txt_dir.iterdir()):  # Only remove if we moved files or it's empty
                    log.info(f"  Removing directory: {txt_dir.relative_to(workspace_root)}")
                    shutil.rmtree(txt_dir)
                    cleaned_count += 1
                else:
                    log.warning(
                        f"  Directory not empty after potential moves, not removing: {txt_dir.relative_to(workspace_root)}"
                    )

            except Exception as e:
                log.error(f"  Error processing directory {tool_dir.relative_to(workspace_root)}: {e}")
                error_count += 1
        # else: no txt subdir found, nothing to do for this tool

    log.info("-" * 30)
    if cleaned_count > 0:
        log.info(f"Cleanup finished. Processed {cleaned_count} tool directories successfully.")
    else:
        log.info("No 'txt' subdirectories found requiring cleanup.")

    if error_count > 0:
        log.warning(f"{error_count} errors occurred during cleanup.")


if __name__ == "__main__":
    cleanup_tool_txt_dirs()
    log.info("Script finished. Remember to delete this script if it's no longer needed.")
