#!/usr/bin/env python3
"""Manual script to run baseline generation for whitelisted tools."""

import sys
import logging
from pathlib import Path
import time
import concurrent.futures

# Add project root to path to allow importing project modules
_SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = _SCRIPT_PATH.parent.parent  # Assumes script is in project_root/scripts
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))
TESTS_DIR = PROJECT_ROOT / "tests"
sys.path.insert(0, str(TESTS_DIR))  # Need this for conftest import

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

try:
    from zeroth_law.dev_scripts.config_reader import load_tool_lists_from_toml

    # IMPORTANT: We need the *actual implementation* from conftest, not a dummy one
    from conftest import (
        _update_baseline_and_index_entry,  # The worker function
        MAX_WORKERS,  # Reuse max workers
        # WORKSPACE_ROOT, # REMOVED - Determine path locally
        # TOOLS_DIR, # REMOVED - Determine path locally
        # TOOL_INDEX_PATH # REMOVED - Determine path locally
    )
    from zeroth_law.lib.tool_index_handler import ToolIndexHandler
except ImportError as e:
    log.error(
        f"Failed to import necessary modules. Ensure script is run from project root or PYTHONPATH is set. Error: {e}"
    )
    sys.exit(1)


def main():
    """Main execution function."""
    start_time = time.monotonic()
    log.info("Starting manual baseline generation...")

    # Determine paths based on script location
    workspace_root = PROJECT_ROOT  # Use root derived from script path
    tools_dir = workspace_root / "src" / "zeroth_law" / "tools"
    tool_index_path = tools_dir / "tool_index.json"
    pyproject_path = workspace_root / "pyproject.toml"

    log.info(f"Using Workspace Root: {workspace_root}")
    log.info(f"Using Tools Dir: {tools_dir}")
    log.info(f"Using Index Path: {tool_index_path}")

    # 1. Load Whitelist
    try:
        whitelist, _ = load_tool_lists_from_toml(pyproject_path)
        if not whitelist:
            log.warning("Whitelist is empty. No baselines to generate.")
            return
        log.info(f"Loaded {len(whitelist)} tools from whitelist: {sorted(list(whitelist))}")
    except Exception as e:
        log.error(f"Failed to load whitelist from {pyproject_path}: {e}", exc_info=True)
        sys.exit(1)

    # 2. Instantiate Index Handler
    try:
        # Ensure index file exists or is created
        if not tool_index_path.is_file():
            log.warning(f"Tool index file not found at {tool_index_path}, creating empty index.")
            tool_index_path.parent.mkdir(parents=True, exist_ok=True)
            tool_index_path.write_text("{}", encoding="utf-8")

        tool_index_handler = ToolIndexHandler(tool_index_path)
        tool_index_handler.reload()  # Load initial state
        log.info("ToolIndexHandler initialized.")
    except Exception as e:
        log.error(f"Failed to initialize ToolIndexHandler for {tool_index_path}: {e}", exc_info=True)
        sys.exit(1)

    # 3. Run baseline updates in parallel
    updated_count = 0
    processed_count = 0
    error_list = []

    # Assume only base commands for now (no subcommands) - Create tuples
    sequences_to_process = [(tool,) for tool in whitelist]

    log.info(f"Processing {len(sequences_to_process)} command sequences...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_sequence = {
            executor.submit(_update_baseline_and_index_entry, seq, tools_dir, tool_index_handler): seq
            for seq in sequences_to_process
        }

        for future in concurrent.futures.as_completed(future_to_sequence):
            sequence = future_to_sequence[future]
            tool_id = sequence[0]  # Since sequence is just (tool,)
            processed_count += 1
            try:
                _tool_id_returned, update_occurred = future.result()
                if _tool_id_returned != tool_id:
                    log.error(f"Worker returned unexpected tool_id '{_tool_id_returned}' for sequence {sequence}")
                if update_occurred:
                    log.info(f"Updated baseline/index for: {tool_id}")
                    updated_count += 1
                else:
                    log.info(f"Verified baseline/index for: {tool_id}")
            except Exception as exc:
                log.error(f"Sequence '{tool_id}' generated an exception during baseline update: {exc}", exc_info=True)
                error_list.append(tool_id)

    # Final save might not be strictly necessary if handler updates in place, but good practice
    # tool_index_handler.save_index() # Assuming ToolIndexHandler handles saving internally on updates

    end_time = time.monotonic()
    duration = end_time - start_time
    log.info(f"Manual baseline generation finished in {duration:.2f}s.")
    log.info(f"Processed: {processed_count}, Updated: {updated_count}, Errors: {len(error_list)}")

    if error_list:
        log.error(f"Errors occurred during baseline generation for: {error_list}")
        sys.exit(1)
    else:
        log.info("Baseline generation completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
