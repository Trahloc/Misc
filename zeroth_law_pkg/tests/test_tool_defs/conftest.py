import pytest
import json
import logging
import sys
import zlib
import time
import yaml
import subprocess
import shlex
import os
import warnings
import concurrent.futures
from pathlib import Path
import re  # Import regex module
from .test_ensure_txt_baselines_exist import get_managed_sequences, get_index_entry  # Import the function

# Add src directory to sys.path
_SRC_DIR = Path(__file__).parent.parent.parent / "src"
if str(_SRC_DIR.resolve()) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR.resolve()))
    # print(f"DEBUG: Added {_SRC_DIR.resolve()} to sys.path") # Keep commented unless debugging path

# Import the path utility function *after* modifying sys.path
try:
    from zeroth_law.path_utils import find_project_root
except ImportError as e:
    print(f"DEBUG: Failed to import find_project_root from path_utils. sys.path={sys.path}")
    raise e

# Import the *actual* handler class
try:
    from zeroth_law.lib.tool_index_handler import ToolIndexHandler
except ImportError as e:
    print(f"ERROR: Could not import ToolIndexHandler from zeroth_law.lib.tool_index_handler. {e}")
    raise

# --- Logging Setup ---
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Constants ---
UV_BIN = os.environ.get("UV_BIN_PATH", "uv")
MAX_WORKERS = os.cpu_count() or 4  # Default to 4 if cpu_count returns None

# --- Fixtures for Paths (Session Scoped) ---


@pytest.fixture(scope="session")
def WORKSPACE_ROOT() -> Path:
    """Fixture to dynamically find and provide the project root directory."""
    _conftest_dir = Path(__file__).parent
    root = find_project_root(_conftest_dir)
    if not root:
        pytest.fail("Could not find project root (containing pyproject.toml) from conftest.py location.")
    log.info(f"WORKSPACE_ROOT determined as: {root}")
    return root


@pytest.fixture(scope="session")
def TOOLS_DIR(WORKSPACE_ROOT: Path) -> Path:
    """Fixture to provide the derived tools directory path."""
    tools_dir = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
    log.info(f"TOOLS_DIR determined as: {tools_dir}")
    return tools_dir


@pytest.fixture(scope="session")
def TOOL_INDEX_PATH(TOOLS_DIR: Path) -> Path:
    """Fixture to provide the derived tool index path."""
    index_path = TOOLS_DIR / "tool_index.json"
    log.info(f"TOOL_INDEX_PATH determined as: {index_path}")
    return index_path


# --- Helper Functions (mostly from timing script, adapted) ---
def command_sequence_to_id(command_parts: tuple[str, ...]) -> str:
    """Creates a file/tool ID from a command sequence tuple."""
    return "_".join(command_parts)


def calculate_crc32_hex(content_bytes: bytes) -> str:
    """Calculates the CRC32 checksum and returns it as an uppercase hex string prefixed with 0x."""
    crc_val = zlib.crc32(content_bytes) & 0xFFFFFFFF
    return f"0x{crc_val:08X}"


def load_managed_tools(yaml_path: Path) -> list[str]:
    """Loads the list of managed tool names from the YAML config."""
    if not yaml_path.is_file():
        log.error(f"Managed tools file not found at {yaml_path}")
        return []
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            managed = data.get("managed_tools", [])
            if not isinstance(managed, list):
                log.error(f"'managed_tools' key in {yaml_path} is not a list.")
                return []
            return [tool for tool in managed if isinstance(tool, str)]
    except yaml.YAMLError as e:
        log.error(f"Error parsing YAML file {yaml_path}: {e}")
        return []
    except Exception as e:
        log.error(f"Unexpected error loading {yaml_path}: {e}")
        return []


# Define a regex pattern to match log lines (adjust if format varies significantly)
LOG_LINE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[[^]]+\]")


def _update_baseline_and_index_entry(
    command_sequence: tuple[str, ...], tools_dir: Path, handler: ToolIndexHandler
) -> tuple[str, bool]:
    """Worker function: Generates TXT, calculates CRC, updates index via handler if needed. Handles subcommands."""
    tool_id = command_sequence_to_id(command_sequence)  # e.g., 'safety' or 'ruff_check'
    tool_name = command_sequence[0]  # Base tool name, e.g., 'safety' or 'ruff'
    tool_dir = tools_dir / tool_name
    txt_file_path = tool_dir / f"{tool_id}.txt"
    update_occurred = False
    current_time = time.time()

    # print(f"Starting baseline/index update for: {tool_id}") # Maybe too verbose for fixture

    try:
        tool_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log.error(f"Error creating directory {tool_dir} for {tool_id}: {e}")
        return tool_id, update_occurred  # Return False for update_occurred on error

    cmd_list_part1 = [UV_BIN, "run", "--"]
    # Construct help command for tool or subcommand
    cmd_list_tool_help = list(command_sequence) + ["--help"]
    full_cmd_str = f"{shlex.join(cmd_list_part1 + cmd_list_tool_help)} | cat"
    log.debug(f"Running command for {tool_id}: {full_cmd_str}")

    try:
        process = subprocess.run(
            full_cmd_str,
            shell=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=60,  # Added timeout
        )

        # Handle command failures more robustly
        if process.returncode != 0:
            # Check if the failure is expected (e.g., subcommand doesn't support --help directly)
            # Heuristic: If stderr mentions 'no such option' or 'unrecognized arguments: --help',
            # and stdout is empty, maybe skip baseline generation for this subcommand?
            # For now, just log a warning and skip update. Refine later if needed.
            stderr_lower = process.stderr.lower() if process.stderr else ""
            if (
                "no such option" in stderr_lower
                or "unrecognized arguments: --help" in stderr_lower
                or "unexpected argument '--help'" in stderr_lower
            ):
                log.warning(
                    f"Command for '{tool_id}' failed, possibly due to no direct --help support for subcommand. Skipping baseline/index update. Stderr: {process.stderr.strip()}"
                )
            else:
                log.warning(
                    f"Command for '{tool_id}' failed (exit code {process.returncode}). Skipping baseline/index update. Stderr: {process.stderr.strip()}"
                )
            return tool_id, update_occurred

        # --- Filter out log lines --- START
        raw_output_lines = process.stdout.splitlines()
        filtered_output_lines = []
        for line in raw_output_lines:
            if not LOG_LINE_PATTERN.match(line):
                filtered_output_lines.append(line)
            else:
                log.debug(f"Filtered out log line for {tool_id}: {line}")

        # Join the filtered lines back, normalize line endings, and strip trailing whitespace
        output_normalized_str = "\n".join(filtered_output_lines).replace("\r\n", "\n").replace("\r", "\n").rstrip()
        # --- Filter out log lines --- END

        # Handle cases where command succeeds but produces no *filtered* output
        if not output_normalized_str:
            log.info(
                f"Command for '{tool_id}' succeeded but produced no non-log stdout. Skipping baseline/index update."
            )
            # Update checked timestamp only?
            entry_update_data = {"checked_timestamp": current_time}
            handler.update_entry(command_sequence, entry_update_data)  # Best effort update
            return tool_id, update_occurred

        output_normalized_bytes = output_normalized_str.encode("utf-8")

        # Write the .txt file (now filtered)
        txt_file_path.write_bytes(output_normalized_bytes)

        # Calculate CRC (on filtered content)
        calculated_crc = calculate_crc32_hex(output_normalized_bytes)

        # --- Load Index Data ---
        raw_data = handler.get_raw_index_data()  # Get the raw dictionary
        current_entry = get_index_entry(raw_data, command_sequence)  # Use the helper
        stored_crc = current_entry.get("crc") if current_entry else None

        # Compare and update index via handler if needed
        entry_update_data = {"checked_timestamp": current_time}
        if stored_crc != calculated_crc:
            log.info(
                f"Updating index for {tool_id} (filtered baseline): Stored CRC='{stored_crc}', New CRC='{calculated_crc}'"
            )
            # Update both CRC and timestamp
            entry_update_data["crc"] = calculated_crc
            entry_update_data["updated_timestamp"] = current_time
            update_occurred = True
        else:
            # Even if CRC matches, update checked_timestamp
            log.debug(f"CRC matches for {tool_id} (filtered baseline) ({stored_crc}). Updating checked_timestamp.")
            # entry_update_data only needs checked_timestamp (already set)

        # --- Use handler to update the index --- #
        if not handler.update_entry(command_sequence, entry_update_data):
            log.error(f"Handler failed to update index for {tool_id} with data: {entry_update_data}")
            # Optionally, don't set update_occurred to True if index update fails?
            # For now, assume txt write success means potential update, even if index fails.

        # print(f"Finished baseline/index update for: {tool_id}")
        return tool_id, update_occurred

    except subprocess.TimeoutExpired:
        log.error(f"Command for '{tool_id}' timed out after 60 seconds. Skipping baseline/index update.")
        return tool_id, update_occurred
    except Exception as e:
        log.exception(f"Unexpected error processing baseline for '{tool_id}': {e}")
        return tool_id, update_occurred  # Return False on unexpected error


# --- Fixture for Index Handling (Session Scoped) ---
@pytest.fixture(scope="function")
def tool_index_handler(WORKSPACE_ROOT: Path, TOOL_INDEX_PATH: Path):
    """Fixture to load, manage, and save the tool index. Depends on path fixtures."""
    log.info("[HANDLER INIT] Initializing ToolIndexHandler...")
    handler_instance = ToolIndexHandler(TOOL_INDEX_PATH)
    yield handler_instance
    log.info("[HANDLER SAVE] Checking if save needed...")
    if hasattr(handler_instance, "save_if_dirty"):
        try:
            handler_instance.save_if_dirty()
            log.info(f"ToolIndexHandler saved changes (if any) to: {TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}")
        except Exception as e:
            log.error(f"Error saving tool index via handler: {e}")
    # else:
    # If save_if_dirty doesn't exist yet, we might just do nothing for now
    # log.debug("ToolIndexHandler does not yet have save_if_dirty method.")


# --- Modified Fixture: Ensure Baselines Updated (Session Scoped, NO Autouse) ---
@pytest.fixture(scope="session")
def ensure_baselines_updated(
    WORKSPACE_ROOT: Path, TOOLS_DIR: Path, TOOL_INDEX_PATH: Path, tool_index_handler: ToolIndexHandler
):
    """(MANUALLY TRIGGERED) update/verify all .txt baselines and tool index CRCs. Uses get_managed_sequences."""
    log.info("Starting manual baseline and index update using get_managed_sequences...")
    start_time = time.monotonic()

    # Use the robust sequence discovery logic from test_ensure_txt_baselines_exist.py
    config_path = WORKSPACE_ROOT / "pyproject.toml"
    all_command_sequences = get_managed_sequences(config_path, TOOLS_DIR, WORKSPACE_ROOT)

    if not all_command_sequences:
        log.warning("get_managed_sequences returned empty list, skipping baseline update.")
        return

    log.info(
        f"Discovered {len(all_command_sequences)} command sequences for baseline update via get_managed_sequences."
    )
    results = []  # Store (tool_id: str, updated: bool) tuples

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Use command_sequence directly
        future_to_sequence = {
            executor.submit(_update_baseline_and_index_entry, seq, TOOLS_DIR, tool_index_handler): seq
            for seq in all_command_sequences
        }
        for future in concurrent.futures.as_completed(future_to_sequence):
            sequence = future_to_sequence[future]
            tool_id = command_sequence_to_id(sequence)
            try:
                result_tuple = future.result()  # (returned_tool_id, update_occurred)
                # Verify returned_tool_id matches expected?
                if result_tuple[0] != tool_id:
                    log.error(f"Mismatch in tool ID from worker: expected {tool_id}, got {result_tuple[0]}")
                results.append(result_tuple)
            except Exception as exc:
                # Log exceptions from the worker function itself
                log.exception(f"Exception during baseline update task for {tool_id}: {exc}")
                results.append((tool_id, False))  # Mark as not updated on error

    end_time = time.monotonic()
    duration = end_time - start_time

    # --- Report Summary and Check for Warnings ---
    updated_sequences = []
    total_processed = len(results)
    # success_count = sum(1 for _, updated in results) # Not tracking overall success explicitly now

    for tool_id, updated_flag in results:
        if updated_flag:
            updated_sequences.append(tool_id)

    log.info(
        f"Baseline update summary: {total_processed} sequences processed, {len(updated_sequences)} updated. Total time: {duration:.2f}s"
    )
    if updated_sequences:
        log.info(f"Updated sequences: {', '.join(updated_sequences)}")

    # Adjust warning logic if needed - maybe warn if *any* CRC changed?
    if updated_sequences:
        warning_message = (
            f"{len(updated_sequences)} tool/subcommand sequences had their baselines/CRCs updated: "
            f"{', '.join(updated_sequences)}. This might indicate tool changes or initial generation."
        )
        warnings.warn(warning_message, pytest.PytestWarning)

    log.info("Finished manual baseline and index update.")


# --- Constants (moved below fixtures) ---
# CACHE_DURATION_SECONDS = 24 * 60 * 60  # 24 hours (If needed)


# --- Helper Functions (moved below fixtures) ---
def command_sequence_to_id(command_parts: tuple[str, ...]) -> str:
    """Creates a readable ID for parametrized tests and dictionary keys."""
    return "_".join(command_parts)


def calculate_crc32(text_content: str) -> str:  # Ensure using correct name if defined here, or import
    """Calculates the CRC32 checksum of text content and returns it as a hex string."""
    # Assuming this function is needed by tests directly, otherwise it could be removed
    # If kept, ensure it matches the implementation in lib/crc.py if necessary.
    CRC32_HEX_WIDTH = 8
    crc_val = zlib.crc32(text_content.encode("utf-8", errors="replace"))
    hex_str = format(crc_val & 0xFFFFFFFF, f"0{CRC32_HEX_WIDTH}x")
    return f"0x{hex_str.upper()}"


# --- ADDED: Fixture to auto-fix JSON files --- #
@pytest.fixture(scope="session", autouse=True)
def auto_fix_json_files(WORKSPACE_ROOT):
    """Fixture to automatically run JSON fixing scripts before tests."""
    scripts_to_run = [("fix-json-whitespace", "Whitespace Fixer"), ("fix-json-schema", "Schema Fixer")]

    for script_name, description in scripts_to_run:
        log.info(f"[Fixture] Running JSON {description}...")
        script_command = ["uv", "run", script_name]
        try:
            # Run the script from the workspace root
            process = subprocess.run(
                script_command,
                cwd=WORKSPACE_ROOT,
                capture_output=True,
                text=True,
                check=False,  # Check return code manually
                encoding="utf-8",
            )
            if process.returncode != 0:
                log.error(
                    f"[Fixture] JSON {description} script ('{script_name}') failed! Exit code: {process.returncode}"
                )
                log.error(f"Stderr:\n{process.stderr}")
                # Optionally fail test session
                # pytest.fail(f"JSON {description} script failed.", pytrace=False)
            else:
                log.info(f"[Fixture] JSON {description} script completed.")
                # log.debug(f"Stdout:\n{process.stdout}")
        except FileNotFoundError:
            log.error(
                f"[Fixture] Error: Could not find 'uv' or the '{script_name}' script. Is 'uv' installed and have you run 'uv pip install -e .'?"
            )
            # pytest.fail(f"Could not execute JSON {description} script.", pytrace=False)
        except Exception as e:
            log.exception(f"[Fixture] Unexpected error running JSON {description}: {e}")
            # pytest.fail(f"Unexpected error in JSON fixer fixture: {e}", pytrace=False)


# --- END ADDED Fixture --- #
