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
from typing import List, Tuple, Set, Dict, Any

# Remove manual path manipulation
# _conftest_dir = Path(__file__).parent.resolve()
# _tests_root = _conftest_dir.parent
# _workspace_root_session = _tests_root.parent
# _src_path = _workspace_root_session / "src"
# if str(_src_path) not in sys.path:
#     sys.path.insert(0, str(_src_path))

# --- Import Refactored Components (Assume standard imports work) ---
try:
    from zeroth_law.dev_scripts.tool_reconciler import ToolStatus
    from zeroth_law.dev_scripts.subcommand_discoverer import get_subcommands_from_json
    from zeroth_law.dev_scripts.sequence_generator import generate_sequences_for_tool
    from zeroth_law.lib.tool_index_handler import ToolIndexHandler
    from zeroth_law.dev_scripts.reconciliation_logic import perform_tool_reconciliation, ReconciliationError
except ImportError as e:
    # Keep the ImportError handling as a safeguard
    print(
        f"ERROR in test_tool_defs/conftest.py: Failed to import dev scripts. Check PYTHONPATH/editable install. Details: {e}"
    )

    # Define dummy functions or raise early failure if imports fail
    def get_subcommands_from_json(*args, **kwargs):
        pytest.fail("Import failed")
        return {}

    def generate_sequences_for_tool(*args, **kwargs):
        pytest.fail("Import failed")
        return []

    class ToolIndexHandler:
        def __init__(*args, **kwargs):
            pytest.fail("Import failed")

        def get_raw_index_data(*args, **kwargs):
            return {}

        def reload(*args, **kwargs):
            pass

        def get_entry(*args, **kwargs):
            return None

    def perform_tool_reconciliation(*args, **kwargs):
        pytest.fail("Import failed")
        return {}, set()

    class ReconciliationError(Exception):
        pass

    # ToolStatus might not be directly importable if reconcile_tools is removed, handle appropriately
    # If ToolStatus enum is needed, ensure it can still be imported or defined.
    # Assuming it might still come from tool_reconciler or another accessible place.
    class ToolStatus:
        MANAGED_OK = object()
        MANAGED_MISSING_ENV = object()
        WHITELISTED_NOT_IN_TOOLS_DIR = object()
        # Add other statuses if needed by remaining logic


# --- Logging Setup ---
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Constants ---
UV_BIN = os.environ.get("UV_BIN_PATH", "uv")
MAX_WORKERS = os.cpu_count() or 4  # Default to 4 if cpu_count returns None

# --- Fixtures for Paths (Session Scoped) ---


@pytest.fixture(scope="session")
def WORKSPACE_ROOT() -> Path:
    # Assuming this conftest is in tests/test_tool_defs/
    # Recalculate relative to this file's location
    # This might still be needed if the root conftest doesn't provide it
    # or if we want to be self-contained here.
    ws_root = Path(__file__).resolve().parents[3]
    # Add a check?
    if not (ws_root / "pyproject.toml").exists():
        pytest.fail(f"CRITICAL: pyproject.toml not found at deduced WORKSPACE_ROOT: {ws_root}")
    return ws_root


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


@pytest.fixture(scope="session")
def TOOL_DEFS_DIR_FIXTURE(WORKSPACE_ROOT: Path) -> Path:
    """Fixture providing the path to the tool definitions directory."""
    # Define tool_defs dir based on WORKSPACE_ROOT, consistent with integration test
    tool_defs_path = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
    log.info(f"TOOL_DEFS_DIR determined as: {tool_defs_path}")
    if not tool_defs_path.is_dir():
        # Changed to pytest.fail as this is critical for reconciliation
        pytest.fail(f"CRITICAL: Tool definitions directory not found: {tool_defs_path}")
    return tool_defs_path


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


# --- Fixture to Generate Managed Sequences --- #
@pytest.fixture(scope="session")
def managed_sequences(WORKSPACE_ROOT: Path, TOOL_DEFS_DIR_FIXTURE: Path) -> List[Tuple[str, ...]]:
    """Generates a list of all command sequences for managed tools."""
    log.info("Generating managed sequences...")
    all_generated_sequences = []

    # Use the correct tool definitions directory path from the fixture
    tool_defs_dir_path = TOOL_DEFS_DIR_FIXTURE

    # --- Refactored Reconciliation Section ---
    try:
        # Call the helper function
        reconciliation_results, managed_tools_for_processing, blacklist = perform_tool_reconciliation(
            project_root_dir=WORKSPACE_ROOT, tool_defs_dir=tool_defs_dir_path
        )
        log.info(f"Managed tools identified for sequence generation: {managed_tools_for_processing}")

    except ReconciliationError as e:
        pytest.fail(f"Tool reconciliation failed during fixture setup: {e}")
    except FileNotFoundError as e:
        pytest.fail(f"Required directory/file not found during reconciliation in fixture setup: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during reconciliation in fixture setup: {e}", pytrace=True)
    # --- End Refactored Section ---

    # --- Sequence Generation Logic (Uses refactored results) ---
    tools_with_issues = []
    for tool_name in managed_tools_for_processing:
        # Need the reconciliation_results to check status if filtering is needed here
        tool_status = reconciliation_results.get(tool_name)

        # Skip tools that are only whitelisted but have no definition directory,
        # as we cannot generate sequences for them.
        if tool_status == ToolStatus.WHITELISTED_NOT_IN_TOOLS_DIR:
            log.warning(f"Skipping sequence generation for whitelisted tool '{tool_name}' - no definition found.")
            continue

        tool_def_dir = tool_defs_dir_path / tool_name
        if not tool_def_dir.is_dir():
            # This check might be redundant given the WHITELISTED_NOT_IN_TOOLS_DIR status check above,
            # but serves as a safeguard.
            log.error(f"Tool '{tool_name}' is managed but definition directory missing: {tool_def_dir}")
            tools_with_issues.append(tool_name)
            continue

        # Get subcommands from the JSON definitions for this tool
        subcommands_dict = get_subcommands_from_json(tool_def_dir)
        if subcommands_dict is None:  # Handle potential errors from subcommand discovery
            log.warning(
                f"Could not retrieve subcommands for tool '{tool_name}' from {tool_def_dir}. Skipping sequence generation."
            )
            continue

        # Generate all sequences (base command + subcommands)
        sequences = generate_sequences_for_tool(tool_name, subcommands_dict, blacklist)
        all_generated_sequences.extend(sequences)
        log.debug(f"Generated {len(sequences)} sequences for tool '{tool_name}'.")

    if tools_with_issues:
        # Fail the test session if definition directories are missing for expected tools
        pytest.fail(f"Missing definition directories for managed tools: {tools_with_issues}")

    log.info(f"Total managed sequences generated: {len(all_generated_sequences)}")
    if not all_generated_sequences:
        log.warning("No managed sequences were generated. Check tool definitions and reconciliation.")
        # Decide if this should be a failure? For now, just warn.
        # pytest.fail("Fixture 'managed_sequences' generated an empty list.")

    return all_generated_sequences
