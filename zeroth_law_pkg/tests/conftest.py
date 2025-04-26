import re
import shlex
import subprocess
import ast
import time
import sys
from pathlib import Path
import logging
from typing import Any, Generator, List, Optional, Tuple
import concurrent.futures
import json
import warnings
import yaml
import zlib
import os

import pytest

# Import the path utility function
from zeroth_law.common.path_utils import find_project_root

# Explicitly import the session-scoped fixture
# from tests.test_tool_defs.conftest import WORKSPACE_ROOT

log = logging.getLogger(__name__)


# --- ADDED WORKSPACE_ROOT Fixture --- #
@pytest.fixture(scope="session")
def WORKSPACE_ROOT() -> Path:
    """Fixture to dynamically find and provide the project root directory."""
    _conftest_dir = Path(__file__).parent
    root = find_project_root(_conftest_dir)
    if not root:
        pytest.fail("Could not find project root (containing pyproject.toml) from conftest.py location.")
    logging.info(f"WORKSPACE_ROOT determined as: {root}")  # Use logging instead of print
    return root


# --- END ADDED WORKSPACE_ROOT Fixture --- #


# --- ADDED TOOLS_DIR Fixture --- #
@pytest.fixture(scope="session")
def TOOLS_DIR(WORKSPACE_ROOT: Path) -> Path:
    """Fixture to provide the derived tools directory path."""
    tools_dir = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
    logging.info(f"TOOLS_DIR determined as: {tools_dir}")
    return tools_dir


# --- END ADDED TOOLS_DIR Fixture --- #


# --- ADDED TOOL_INDEX_PATH Fixture --- #
@pytest.fixture(scope="session")
def TOOL_INDEX_PATH(TOOLS_DIR: Path) -> Path:
    """Fixture to provide the derived tool index path."""
    index_path = TOOLS_DIR / "tool_index.json"
    logging.info(f"TOOL_INDEX_PATH determined as: {index_path}")
    return index_path


# --- END ADDED TOOL_INDEX_PATH Fixture --- #


# --- ADDED ZLT_ROOT Fixture --- #
@pytest.fixture(scope="session")
def ZLT_ROOT(WORKSPACE_ROOT: Path) -> Path:
    """Fixture to provide the derived ZLT source root directory path."""
    zlt_root = WORKSPACE_ROOT / "src" / "zeroth_law"
    logging.info(f"ZLT_ROOT determined as: {zlt_root}")
    return zlt_root


# --- END ADDED ZLT_ROOT Fixture --- #


# --- ADDED ZLT_SCHEMA_PATH Fixture --- #
@pytest.fixture(scope="session")
def ZLT_SCHEMA_PATH(ZLT_ROOT: Path) -> Path:
    """Fixture to provide the derived path to the tool definition schema."""
    schema_path = ZLT_ROOT / "schemas" / "tool_definition_schema.json"
    logging.info(f"ZLT_SCHEMA_PATH determined as: {schema_path}")
    return schema_path


# --- END ADDED ZLT_SCHEMA_PATH Fixture --- #


def _run_tool_help_internal(command_list):  # Renamed internal helper
    """Runs a command list with --help and captures output."""
    # ... (rest of the implementation is the same)
    try:
        process = subprocess.run(
            ["poetry", "run"] + command_list + ["--help"],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        return process.stdout
    except FileNotFoundError:
        pytest.fail(f"Tool command not found: {shlex.join(command_list)}")
    except subprocess.CalledProcessError as e:
        pytest.fail(
            f"Tool command ' {shlex.join(command_list + ['--help'])}' failed with exit code {e.returncode}:\n{e.stderr}"
        )
    except Exception as e:
        pytest.fail(f"Unexpected error running tool help command: {e}")


@pytest.fixture
def run_tool_help_func():  # Fixture that returns the helper function
    """Pytest fixture that provides the tool help execution function."""
    return _run_tool_help_internal


# --- NEW Simplified Text Processing ---
def simplify_text_for_matching(text):
    """Prepares text for basic substring matching.

    Keeps only alphanumeric and spaces, converts to lowercase,
    collapses whitespace, and strips leading/trailing spaces.
    """
    if not isinstance(text, str):
        return ""  # Handle non-string input gracefully
    # Keep only alphanumeric and spaces
    processed = "".join(c for c in text if c.isalnum() or c.isspace())
    # Lowercase
    processed = processed.lower()
    # Collapse whitespace and strip
    processed = " ".join(processed.split())
    return processed


@pytest.fixture
def text_simplifier_func():  # New fixture name
    """Pytest fixture providing the text simplification function."""
    return simplify_text_for_matching


# --- END NEW ---

# --- OLD Fuzzy Pattern (Commented out/Removed) ---
# def create_fuzzy_help_pattern(help_text):
#     r"""Converts a help string into a regex pattern.
#
#     Keeps alphanumeric literally.
#     Escapes safe punctuation.
#     Replaces regex metacharacters with '.'.
#     Collapses whitespace sequences to r'\\s+'.
#     Ignores specific characters (like ':').
#     """
#     regex_metachars = r\".^$*+?{}[]\\|()\"  # Characters to replace with .
#     chars_to_ignore = \":\"  # Characters to skip entirely
#     pattern = \"\"
#     in_whitespace = False
#
#     # Strip trailing whitespace from input to avoid spurious \\s+ at the end
#     help_text = help_text.rstrip()
#
#     for char in help_text:
#         if char in chars_to_ignore:
#             # Ensure preceding whitespace is added before skipping
#             if in_whitespace:
#                 pattern += r\"\\s+\"
#                 in_whitespace = False
#             continue  # Skip this character
#         elif char.isalnum():
#             if in_whitespace:
#                 pattern += r\"\\s+\"
#                 in_whitespace = False
#             pattern += char  # Keep alnum literally
#         elif char.isspace():
#             if not in_whitespace:
#                 in_whitespace = True  # Start whitespace sequence
#         elif char in regex_metachars:
#             if in_whitespace:
#                 pattern += r\"\\s+\"
#                 in_whitespace = False
#             pattern += \".\"  # Replace meta char with wildcard
#         else:
#             # Other punctuation/symbols: escape and add
#             if in_whitespace:
#                 pattern += r\"\\s+\"
#                 in_whitespace = False
#             pattern += re.escape(char)
#
#     # Add trailing whitespace if needed
#     # REMOVED: This might add unwanted whitespace, especially with rstrip()
#     # if in_whitespace:
#     #     pattern += r\"\\s+\"
#
#     return pattern
#
# @pytest.fixture
# def fuzzy_pattern_func():
#     """Pytest fixture that provides the fuzzy help pattern creation function."""
#     return create_fuzzy_help_pattern
# --- END OLD ---


# --- AST Scan Fixture ---


def _scan_project_ast(workspace_root: Path):
    """Performs an AST scan of Python files in src/ and tests/."""
    target_dirs = [workspace_root / "src", workspace_root / "tests"]
    py_files = []

    print(
        f"\nAST Scan: Scanning for Python files in: {[str(d.relative_to(workspace_root)) for d in target_dirs]}",
        flush=True,
    )

    # Find files, excluding common unwanted directories like .venv, __pycache__
    for target_dir in target_dirs:
        if target_dir.is_dir():
            for file_path in target_dir.rglob("*.py"):
                is_excluded = False
                for part in file_path.parts:
                    # Use Path methods for exclusion check
                    if part == ".venv" or part == "__pycache__" or part.endswith(".egg-info"):
                        is_excluded = True
                        break
                if not is_excluded:
                    py_files.append(file_path)
        else:
            print(f"AST Scan Warning: Target directory not found: {target_dir}", file=sys.stderr, flush=True)

    print(f"AST Scan: Found {len(py_files)} Python files.", flush=True)

    start_time = time.monotonic()
    parsed_count = 0
    error_count = 0
    error_files = []

    for file_path in py_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            ast.parse(content, filename=str(file_path))
            parsed_count += 1
        except SyntaxError as e:
            print(f"AST Scan SyntaxError in {file_path.relative_to(workspace_root)}: {e}", file=sys.stderr, flush=True)
            error_files.append(f"{file_path.relative_to(workspace_root)} (SyntaxError)")
            error_count += 1
        except Exception as e:
            print(
                f"AST Scan Error processing {file_path.relative_to(workspace_root)}: {e}", file=sys.stderr, flush=True
            )
            error_files.append(f"{file_path.relative_to(workspace_root)} ({type(e).__name__})")
            error_count += 1  # Count other errors too

    end_time = time.monotonic()
    duration = end_time - start_time

    print("--- AST Scan Summary ---", flush=True)
    # print(f"Total Python files found: {len(py_files)}", flush=True) # Redundant with earlier print
    print(f"Successfully parsed:      {parsed_count}", flush=True)
    print(f"Files with errors:       {error_count}", flush=True)
    print(f"Total time taken:        {duration:.4f} seconds", flush=True)

    if error_count > 0:
        pytest.fail(f"AST scan detected {error_count} file(s) with parsing errors: {error_files}", pytrace=False)


# Use WORKSPACE_ROOT fixture defined in tests/test_tool_defs/conftest.py
# We need to ensure that fixture is available or redefine WORKSPACE_ROOT here if needed.
# Assuming WORKSPACE_ROOT will be available session-wide from the other conftest.
@pytest.fixture(scope="session", autouse=True)
def project_ast_scan(WORKSPACE_ROOT):
    """Session-scoped fixture that automatically runs an AST scan at the start."""
    print("\nRunning project-wide AST scan...")
    _scan_project_ast(WORKSPACE_ROOT)
    print("AST scan complete.")


# Ensure WORKSPACE_ROOT is available if defined elsewhere (e.g., tests/test_tool_defs/conftest.py)
# If not, we need to define it here similar to how it's done there.


# --- Auto-fixer Fixture for JSON Validation Test ---
@pytest.fixture(scope="session", autouse=True)
def auto_fix_json_validation_test():
    """Session-scoped fixture that attempts to auto-fix the JSON validation test file."""
    test_file_path = Path("tests/test_json_validation.py")
    if not test_file_path.exists():
        logging.warning(f"Auto-fix fixture: {test_file_path} not found. Skipping fix.")
        return

    command = ["uv", "run", "ruff", "check", str(test_file_path), "--fix", "--quiet"]
    logging.info(f"Auto-fix fixture: Running '{shlex.join(command)}'")
    try:
        # Run quietly, we only care if it fails or succeeds
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code, just log
            encoding="utf-8",
        )
        if process.returncode != 0:
            logging.warning(
                f"Auto-fix fixture: Ruff ({shlex.join(command)}) exited with code {process.returncode}. "
                f"Fixing may have failed or file is already clean.\nStderr: {process.stderr.strip()}"
            )
        else:
            logging.info(f"Auto-fix fixture: Ruff completed successfully for {test_file_path}.")

    except FileNotFoundError:
        logging.error(f"Auto-fix fixture: 'uv' or 'ruff' command not found. Ensure ruff is installed.")
    except Exception as e:
        logging.error(f"Auto-fix fixture: Unexpected error running ruff: {e}")


# --- END Auto-fixer Fixture ---


# --- Auto-formatter Fixture for Tool JSON Files ---
@pytest.fixture(scope="session", autouse=True)
def auto_format_tool_json_files(TOOLS_DIR: Path, WORKSPACE_ROOT: Path):
    """Session-scoped fixture that attempts to auto-format tool JSON files using Prettier via npx."""
    # Define the logger within the fixture scope
    log = logging.getLogger(__name__)
    # Configure logging level if needed (optional, can rely on global config)
    # logging.basicConfig(level=logging.INFO) # Example: Uncomment if specific level needed here

    log.info("[JSON Auto-Format] Starting prerequisite checks for Prettier...")

    # 1. Check for npx (Node.js/npm)
    try:
        npx_version_proc = subprocess.run(
            ["npx", "--version"], capture_output=True, check=True, text=True, encoding="utf-8"
        )
        log.info(f"[JSON Auto-Format] Found npx version: {npx_version_proc.stdout.strip()}")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        log.error(
            "[JSON Auto-Format] Prerequisite Check Failed: 'npx' command not found or failed. "
            "Prettier formatting will be skipped. Error details: %s\n"
            "  ACTION REQUIRED: Install Node.js (LTS version recommended, includes npm & npx) for your system. "
            "Visit https://nodejs.org/. Ensure Node is in your system PATH. "
            "After installing Node.js, navigate to the project root (%s) in your terminal and run 'npm install'.",
            e,
            WORKSPACE_ROOT,
        )
        return  # Stop the fixture

    # 2. Check for package.json
    package_json_path = WORKSPACE_ROOT / "package.json"
    if not package_json_path.is_file():
        log.error(
            "[JSON Auto-Format] Prerequisite Check Failed: 'package.json' not found in project root (%s). "
            "Prettier formatting will be skipped.\n"
            "  ACTION REQUIRED: Create 'package.json' in the project root. You can use: "
            'echo \'{"devDependencies": {"prettier": "^3.0.0"}}\' > %s. '
            "Then run 'npm install' in the project root.",
            WORKSPACE_ROOT,
            package_json_path,
        )
        return  # Stop the fixture
    log.info(f"[JSON Auto-Format] Found package.json at: {package_json_path}")

    # 3. Check if npx can find/run prettier (quick check)
    # We run --check on a non-existent file to test execution path without formatting anything yet.
    # Exit code 2 from prettier --check usually means formatting is needed, but we only care if it runs (exit 0, 1, or 2 ok here)
    check_cmd = ["npx", "--no-install", "prettier", "--check", "non_existent_dummy_file_for_check.json"]
    log.info(f"[JSON Auto-Format] Performing Prettier executability check: {shlex.join(check_cmd)}")
    try:
        check_proc = subprocess.run(
            check_cmd, capture_output=True, check=False, text=True, encoding="utf-8", cwd=WORKSPACE_ROOT
        )
        # Check stderr for common errors like 'command not found' within npx itself
        if check_proc.returncode != 0 and (
            "command not found" in check_proc.stderr or "Could not determine version" in check_proc.stderr
        ):
            raise FileNotFoundError(f"npx could not find/run prettier: {check_proc.stderr.strip()}")
        log.info(
            f"[JSON Auto-Format] Prettier executability check passed (Exit code: {check_proc.returncode}). Proceeding with formatting."
        )

    except (FileNotFoundError, Exception) as e:
        log.error(
            "[JSON Auto-Format] Prerequisite Check Failed: Could not execute 'npx prettier'. "
            "Prettier formatting will be skipped. Error details: %s\n"
            "  ACTION REQUIRED: Ensure you have run 'npm install' in the project root (%s) after installing Node.js/npm.",
            e,
            WORKSPACE_ROOT,
        )
        return  # Stop the fixture

    # --- Proceed with Formatting --- #
    log.info("[JSON Auto-Format] Starting actual formatting of tool JSON files...")
    target_dir = TOOLS_DIR
    json_files = list(target_dir.rglob("*.json"))

    if not json_files:
        log.info("[JSON Auto-Format] No JSON files found in target directory. Skipping formatting run.")
        return

    log.info(f"[JSON Auto-Format] Found {len(json_files)} JSON files to format.")
    formatter_cmd_base = ["npx", "--no-install", "prettier", "--write"]

    formatted_count = 0
    error_count = 0
    for json_file in json_files:
        relative_path = json_file.relative_to(WORKSPACE_ROOT)
        command = formatter_cmd_base + [str(relative_path)]  # Use relative path for prettier command
        log.debug(f"[JSON Auto-Format] Running: {shlex.join(command)}")
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,  # Don't fail the whole test run if one file fails formatting
                encoding="utf-8",
                cwd=WORKSPACE_ROOT,  # Run prettier from workspace root
            )
            if process.returncode == 0:
                log.debug(f"[JSON Auto-Format] Successfully processed {relative_path}.")
                formatted_count += 1  # Count processed, not necessarily changed
            else:
                log.warning(
                    f"[JSON Auto-Format] Formatting command failed for {relative_path} (exit code {process.returncode}).\n"
                    f"Stderr: {process.stderr.strip()}"
                )
                error_count += 1
        except Exception as e:
            log.error(f"[JSON Auto-Format] Unexpected error running formatter on {relative_path}: {e}")
            error_count += 1

    log.info(f"[JSON Auto-Format] Finished. Processed: {formatted_count}, Errors: {error_count}")


# --- END JSON Auto-formatter Fixture ---

# --- Codebase Map Generation Fixture ---


@pytest.fixture(scope="session")
def code_map_db(WORKSPACE_ROOT: Path) -> Path:
    """Fixture to ensure the codebase map DB is generated/updated once per session."""
    generator_script = WORKSPACE_ROOT / "tests" / "codebase_map" / "map_generator.py"
    db_path = WORKSPACE_ROOT / "tests" / "codebase_map" / "code_map.db"
    schema_path = WORKSPACE_ROOT / "tests" / "codebase_map" / "schema.sql"
    src_dir = WORKSPACE_ROOT / "src"

    if not generator_script.exists():
        pytest.fail(f"Codebase map generator script not found at: {generator_script}")
    if not src_dir.exists():
        pytest.fail(f"Source directory not found at: {src_dir}")
    if not schema_path.exists():
        pytest.fail(f"Schema file not found at: {schema_path}")

    log.info(f"Running codebase map generator for session: {generator_script}")
    cmd = [
        sys.executable,
        str(generator_script),
        "--db",
        str(db_path),
        "--src",
        str(src_dir),
        "--schema",
        str(schema_path),
        # Do NOT add --prune-stale-entries here - should be manual or specific test
    ]

    try:
        # Use check=True to automatically raise CalledProcessError on failure
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=WORKSPACE_ROOT)
        log.info("Codebase map generator finished successfully.")
        # Log stdout/stderr only if verbose logging is enabled perhaps?
        # print("Generator STDOUT:", result.stdout)
        # print("Generator STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print("Codebase map generator script failed during session setup:")
        print("RETURN CODE:", e.returncode)
        print("COMMAND:", e.cmd)
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        pytest.fail("Codebase map generator failed, aborting tests.")
    except Exception as e:
        print(f"An unexpected error occurred running the codebase map generator: {e}")
        pytest.fail("Codebase map generator failed unexpectedly.")

    if not db_path.exists():
        pytest.fail(f"Codebase map database file was not created at: {db_path}")

    yield db_path
    # No cleanup needed for session-scoped fixture using default path


# --- Codebase Map Report Generation Fixture ---


@pytest.fixture(scope="session")
def code_map_report_json(WORKSPACE_ROOT: Path, code_map_db: Path) -> Path:
    """Fixture to generate the codebase map JSON report once per session.
    Depends on code_map_db to ensure the DB exists first.
    """
    reporter_script = WORKSPACE_ROOT / "tests" / "codebase_map" / "map_reporter.py"
    # Use the default output path defined in the reporter script if possible,
    # otherwise define it here.
    # from tests.codebase_map.map_reporter import OUTPUT_PATH_DEFAULT # Avoid import if possible
    output_path = WORKSPACE_ROOT / "tests" / "codebase_map" / "code_map_report.json"

    if not reporter_script.exists():
        pytest.fail(f"Codebase map reporter script not found at: {reporter_script}")
    if not code_map_db.exists():  # Check DB from dependent fixture
        pytest.fail(f"Codebase map database not found at expected path: {code_map_db}")

    log.info(f"Running codebase map reporter for session: {reporter_script}")
    cmd = [
        sys.executable,
        str(reporter_script),
        "--db",
        str(code_map_db),
        "--output",
        str(output_path),
    ]

    try:
        # Use check=True to automatically raise CalledProcessError on failure
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=WORKSPACE_ROOT)
        log.info("Codebase map reporter finished successfully.")
        # print("Reporter STDOUT:", result.stdout)
        # print("Reporter STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print("Codebase map reporter script failed during session setup:")
        print("RETURN CODE:", e.returncode)
        print("COMMAND:", e.cmd)
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        pytest.fail("Codebase map reporter failed, aborting tests.")
    except Exception as e:
        print(f"An unexpected error occurred running the codebase map reporter: {e}")
        pytest.fail("Codebase map reporter failed unexpectedly.")

    if not output_path.exists():
        pytest.fail(f"Codebase map report file was not created at: {output_path}")

    yield output_path
    # No cleanup needed for session-scoped fixture using default path


# --- ADDED UV Environment Check Fixture --- #
@pytest.fixture(scope="session", autouse=True)
def check_uv_environment(WORKSPACE_ROOT: Path):
    """Verify that tests are running in a uv-managed environment."""
    command = ["uv", "run", "--quiet", "--", "which", "python"]
    try:
        result = subprocess.run(
            command,
            cwd=WORKSPACE_ROOT,  # Run from workspace root
            capture_output=True,
            text=True,
            check=False,  # Check return code manually
            timeout=15,  # Generous timeout for uv run
        )
        if result.returncode != 0:
            error_message = (
                "Failed to verify uv environment.\n"
                f"Command '{" ".join(command)}' failed with exit code {result.returncode}.\n"
                f"Stderr: {result.stderr}\n"
                "Ensure 'uv' is installed and the environment is active/managed correctly."
            )
            pytest.fail(error_message, pytrace=False)
        # Optionally, check if the python path seems reasonable (e.g., contains .venv)
        python_path = result.stdout.strip()
        if not python_path:
            pytest.fail(f"Command '{" ".join(command)}' succeeded but returned an empty path.", pytrace=False)
        # Add more sophisticated path checks if needed
        logging.info(f"UV Environment Check PASSED. Using Python at: {python_path}")

    except FileNotFoundError:
        pytest.fail(
            "Failed to verify uv environment: 'uv' command not found. Is uv installed and in PATH?", pytrace=False
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"Failed to verify uv environment: Command '{" ".join(command)}' timed out.", pytrace=False)
    except Exception as e:
        pytest.fail(f"Unexpected error during uv environment check: {e}", pytrace=False)


# --- END ADDED UV Environment Check Fixture --- #


# --- Import ZLT Components (add try-except block) ---
try:
    from zeroth_law.lib.tool_index_handler import ToolIndexHandler
    from zeroth_law.dev_scripts.reconciliation_logic import perform_tool_reconciliation, ReconciliationError
    from zeroth_law.dev_scripts.tool_reconciler import ToolStatus  # Assuming this is the correct location
    # Note: These might not be strictly needed by the moved fixtures but are related
    # from zeroth_law.dev_scripts.subcommand_discoverer import get_subcommands_from_json
    # from zeroth_law.dev_scripts.sequence_generator import generate_sequences_for_tool
except ImportError as e:
    # Define dummy classes/functions if imports fail, preventing test collection errors
    print(
        f"CRITICAL ERROR in conftest.py: Failed to import ZLT components. Check PYTHONPATH/install. Details: {e}",
        file=sys.stderr,
    )

    class ToolIndexHandler:
        def __init__(*args, **kwargs):
            pytest.fail("ToolIndexHandler import failed")

        def get_raw_index_data(*args, **kwargs):
            return {}

        def reload(*args, **kwargs):
            pass

        def get_entry(*args, **kwargs):
            return None

        def update_entry(*args, **kwargs):
            pass

    def perform_tool_reconciliation(*args, **kwargs):
        pytest.fail("perform_tool_reconciliation import failed")
        return {}, set()

    class ReconciliationError(Exception):
        pass

    class ToolStatus:  # Define dummy statuses if needed by tests
        MANAGED_OK = object()
        MANAGED_MISSING_ENV = object()
        WHITELISTED_NOT_IN_TOOLS_DIR = object()


# --- Constants ---
UV_BIN = os.environ.get("UV_BIN_PATH", "uv")
MAX_WORKERS = os.cpu_count() or 4  # Default to 4 if cpu_count returns None
LOG_LINE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[[^]]+\]")


# --- Helper Functions Moved from tool_defs/conftest.py ---
def command_sequence_to_id(command_parts: tuple[str, ...]) -> str:
    """Creates a file/tool ID from a command sequence tuple."""
    if not command_parts:  # Add check for empty tuple
        return "_EMPTY_SEQUENCE_"
    return "_".join(command_parts)


def calculate_crc32_hex(content_bytes: bytes) -> str:
    """Calculates the CRC32 checksum and returns it as an uppercase hex string prefixed with 0x."""
    crc_val = zlib.crc32(content_bytes) & 0xFFFFFFFF
    return f"0x{crc_val:08X}"


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

        new_crc = calculate_crc32_hex(output_normalized_bytes)

        # Check against index via handler
        existing_entry = handler.get_entry(command_sequence)
        existing_crc = existing_entry.get("crc") if existing_entry else None

        if existing_crc != new_crc:
            log.info(f"CRC mismatch for {tool_id}: Index={existing_crc}, New={new_crc}. Updating index.")
            entry_data = {
                "crc": new_crc,
                "updated_timestamp": current_time,
                "checked_timestamp": current_time,
                "source": "baseline_script",  # Indicate source
            }
            handler.update_entry(command_sequence, entry_data)
            update_occurred = True
        else:
            log.debug(f"CRC consistent for {tool_id}. Updating checked timestamp.")
            # Only update checked timestamp if CRC matches
            entry_update_data = {"checked_timestamp": current_time}
            handler.update_entry(command_sequence, entry_update_data)  # Update only checked time

    except subprocess.TimeoutExpired:
        log.error(f"Command timed out for {tool_id}. Skipping.")
    except FileNotFoundError:
        log.error(f"Command not found for {tool_id} (is '{UV_BIN}' in PATH?). Skipping.")
    except Exception as e:
        log.exception(f"Unexpected error processing {tool_id}: {e}")

    return tool_id, update_occurred


# --- Fixtures Moved/Added from tool_defs/conftest.py ---


@pytest.fixture(scope="session")  # Changed scope to session
def tool_index_handler(WORKSPACE_ROOT: Path, TOOL_INDEX_PATH: Path):
    """Provides a session-scoped ToolIndexHandler instance."""
    if not TOOL_INDEX_PATH.parent.is_dir():
        pytest.fail(f"Tool index directory not found: {TOOL_INDEX_PATH.parent}")
    # Ensure file exists, create empty JSON object if not
    if not TOOL_INDEX_PATH.is_file():
        log.warning(f"Tool index file not found at {TOOL_INDEX_PATH}, creating empty index.")
        try:
            TOOL_INDEX_PATH.write_text("{}", encoding="utf-8")
        except OSError as e:
            pytest.fail(f"Failed to create empty tool index file at {TOOL_INDEX_PATH}: {e}")

    handler = ToolIndexHandler(TOOL_INDEX_PATH)
    return handler  # Yield not strictly needed for simple object creation


@pytest.fixture(scope="session")
def managed_sequences(WORKSPACE_ROOT: Path, TOOLS_DIR: Path) -> List[Tuple[str, ...]]:
    """Discovers all managed tool sequences based on reconciliation logic."""
    log.info("Discovering managed tool sequences for session...")
    try:
        # Pass WORKSPACE_ROOT first for project config, then TOOLS_DIR for definitions
        reconciliation_results, managed_tools, _ = perform_tool_reconciliation(WORKSPACE_ROOT, TOOLS_DIR)
        # Errors are handled by ReconciliationError exception below.
        # Log managed tools discovered (optional)
        log.info(f"Reconciliation identified managed tools: {managed_tools}")

        all_sequences = []
        # Extract sequences from the results (which now should include subcommand sequences)
        for tool_name, data in reconciliation_results.items():
            if isinstance(data, dict) and "sequences" in data:
                # Handle potential None value from sequences
                tool_sequences = data.get("sequences")
                if tool_sequences:
                    all_sequences.extend(tool_sequences)
            else:
                # Log unexpected structure
                log.warning(f"Unexpected structure in reconciliation results for {tool_name}: {data}")

        # Ensure sequences are tuples
        all_sequences = [tuple(seq) for seq in all_sequences]
        log.info(f"Discovered {len(all_sequences)} managed sequences.")
        return all_sequences
    except ReconciliationError as e:
        pytest.fail(f"Tool reconciliation failed during test setup: {e}")
    except Exception as e:
        log.exception("Unexpected error during managed sequence discovery")
        pytest.fail(f"Unexpected error during managed sequence discovery: {e}")
    return []  # Return empty list on failure


@pytest.fixture(scope="session", autouse=True)  # Keep autouse=True
def ensure_baselines_updated(
    WORKSPACE_ROOT: Path,
    TOOLS_DIR: Path,
    TOOL_INDEX_PATH: Path,
    tool_index_handler: ToolIndexHandler,
    managed_sequences: list,
):
    """Session-scoped fixture to ensure all tool help baselines (.txt) and tool_index.json are up-to-date."""
    start_time = time.monotonic()
    log.info(f"Starting baseline generation/verification for {len(managed_sequences)} sequences...")

    # Ensure the handler reflects the current index state before updates
    tool_index_handler.reload()

    updated_count = 0
    processed_count = 0
    skipped_count = 0  # Count commands skipped due to --help issues
    error_list = []

    # Use ThreadPoolExecutor for parallel execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Create futures for each sequence
        future_to_sequence = {
            executor.submit(_update_baseline_and_index_entry, seq, TOOLS_DIR, tool_index_handler): seq
            for seq in managed_sequences
        }

        for future in concurrent.futures.as_completed(future_to_sequence):
            sequence = future_to_sequence[future]
            tool_id = command_sequence_to_id(sequence)
            processed_count += 1
            try:
                _tool_id_returned, update_occurred = future.result()
                if _tool_id_returned != tool_id:
                    # This indicates a potential issue in the worker if tool_id doesn't match
                    log.error(f"Worker returned unexpected tool_id '{_tool_id_returned}' for sequence {sequence}")
                if update_occurred:
                    updated_count += 1
            except Exception as exc:
                log.error(f"Sequence '{tool_id}' generated an exception during baseline update: {exc}")
                error_list.append(tool_id)

    # Reload handler again after all updates are done to reflect changes
    tool_index_handler.reload()

    end_time = time.monotonic()
    duration = end_time - start_time
    log.info(f"Baseline generation/verification finished in {duration:.2f}s.")
    log.info(f"Processed: {processed_count}, Updated/Mismatch: {updated_count}, Errors: {len(error_list)}")

    if error_list:
        log.error(f"Errors occurred during baseline generation for: {error_list}")
        # Optionally fail the test session if baseline generation had errors
        # pytest.fail(f"Baseline generation failed for {len(error_list)} tools.")


# --- END Moved/Added Fixtures ---
