"""Script to deterministically regenerate the tool_index.json file.

Reads the tool whitelist from pyproject.toml, discovers tools/subcommands,
runs baseline generation to get CRCs/timestamps, and writes the index.
"""

import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import zlib  # Import zlib for CRC calculation

# --- Configuration & Constants ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Assume this script runs from the workspace root or src/zeroth_law/dev_scripts
try:
    _SCRIPT_DIR = Path(__file__).parent.resolve()
    WORKSPACE_ROOT = _SCRIPT_DIR.parents[2]
except NameError:
    WORKSPACE_ROOT = Path.cwd().resolve()

PYPROJECT_PATH = WORKSPACE_ROOT / "pyproject.toml"
TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
TOOL_INDEX_PATH = TOOLS_DIR / "tool_index.json"


# Placeholder for loading pyproject.toml data
def load_pyproject_toml(path: Path) -> Dict[str, Any]:
    """Loads the pyproject.toml file (basic implementation)."""
    # TODO: Replace with robust loading, potentially using config_loader logic
    try:
        import toml

        with open(path, "r", encoding="utf-8") as f:
            return toml.load(f)
    except (ImportError, FileNotFoundError, Exception) as e:
        log.error(f"Failed to load {path}: {e}")
        sys.exit(1)


def get_tool_whitelist(pyproject_data: Dict[str, Any]) -> Set[str]:
    """Extracts the tool whitelist from pyproject data."""
    try:
        whitelist = pyproject_data["tool"]["zeroth-law"]["tools"]["whitelist"]
        if not isinstance(whitelist, list) or not all(isinstance(t, str) for t in whitelist):
            raise ValueError("Whitelist must be a list of strings.")
        return set(whitelist)
    except (KeyError, ValueError) as e:
        log.error(f"Failed to read tool whitelist from pyproject.toml: {e}")
        sys.exit(1)


def get_venv_executables() -> Set[str]:
    """Gets executable names from the active venv bin directory."""
    # TODO: Reuse/refactor logic from tool_discovery.py if possible
    potential_tools: Set[str] = set()
    try:
        venv_path = Path(sys.prefix)
        bin_path = venv_path / ("Scripts" if sys.platform == "win32" else "bin")
        if bin_path.is_dir():
            all_scripts = [f.name for f in bin_path.iterdir() if f.is_file()]
            # Basic filtering - might need refinement based on tool_discovery exclusions
            potential_tools = {Path(script).stem for script in all_scripts}
        else:
            log.warning(f"Venv bin directory not found: {bin_path}")
        return potential_tools
    except Exception as e:
        log.error(f"Error getting venv executables: {e}")
        return set()


# --- Helper Functions (Potentially move to utils) ---


def command_sequence_to_id(command_parts: Tuple[str, ...]) -> str:
    """Converts a command sequence to a unique ID (e.g., ('ruff', 'check') -> 'ruff_check')."""
    # Simple join, assuming this matches test helpers
    return "_".join(command_parts)


def calculate_hex_crc32(data: bytes) -> str:
    """Calculates the CRC32 hash of byte data and returns it as 0x prefixed hex."""
    # IMPORTANT: zlib.crc32 can return signed int; ensure unsigned 32-bit
    crc_int = zlib.crc32(data) & 0xFFFFFFFF
    return f"0x{crc_int:08X}"


# --- Core Logic Functions ---


def capture_command_output(command_sequence: Tuple[str, ...]) -> Tuple[bytes | None, int]:
    """Captures the raw byte output of command --help | cat."""
    # Ensure --help is added if not present (basic check)
    # This assumes baselines are always generated from --help
    if not any(arg == "--help" for arg in command_sequence):
        command_list = list(command_sequence) + ["--help"]
    else:
        command_list = list(command_sequence)

    # Use uv run to ensure the command is found in the environment
    shell_command = f"uv run -- {' '.join(command_list)} | cat"
    log.debug(f"Executing capture: {shell_command}")

    try:
        result = subprocess.run(
            shell_command,
            capture_output=True,
            check=False,  # Check manually
            shell=True,
            timeout=60,  # Generous timeout
        )
        if result.returncode != 0:
            log.warning(
                f"Capture command '{' '.join(command_list)}' exited with {result.returncode}. Stderr: {result.stderr.decode(errors='ignore')}"
            )

        if not result.stdout and result.returncode != 0:
            log.error(
                f"Failed to capture any output for '{' '.join(command_list)}'. Stderr: {result.stderr.decode(errors='ignore')}"
            )
            return None, result.returncode
        elif not result.stdout:
            log.warning(
                f"Captured empty stdout for '{' '.join(command_list)}', but command exited 0. Treating as empty content."
            )
            return b"", 0
        return result.stdout, 0
    except subprocess.TimeoutExpired:
        log.error(f"Timeout expired capturing output for '{' '.join(command_list)}'")
        return None, -1
    except Exception as e:
        log.exception(f"Unexpected error capturing output for '{' '.join(command_list)}': {e}")
        return None, -2


def ensure_skeleton_json(json_path: Path, command_sequence: Tuple[str, ...], tool_id: str):
    """Creates a minimal skeleton JSON if it doesn't exist."""
    if json_path.exists():
        return True

    log.info(f"Creating skeleton JSON: {json_path}")
    skeleton_content = {
        "command_sequence": list(command_sequence),
        "description": "(Placeholder - AI to populate)",
        "usage": "(Placeholder - AI to populate)",
        "options": {},
        "arguments": {},
        "subcommands": [],
        "metadata": {
            "tool_name": command_sequence[0],
            "command_name": command_sequence[1] if len(command_sequence) > 1 else None,
            "description": "(Placeholder - AI to populate)",
            "ground_truth_crc": "0x00000000",  # Placeholder CRC
            "schema_version": "1.0",
        },
    }
    try:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(skeleton_content, f, indent=2, sort_keys=True)  # Sort keys for consistency
        return True
    except OSError as e:
        log.error(f"Failed to create skeleton JSON file {json_path}: {e}")
        return False
    except Exception as e:
        log.exception(f"Unexpected error creating skeleton JSON {json_path}: {e}")
        return False


def generate_baseline_data(command_parts: Tuple[str, ...]) -> Tuple[str, float, float] | None:
    """Runs baseline generation (capture, CRC calc, TXT write, ensure skeleton JSON).

    Returns: Tuple (crc_hex, updated_timestamp, checked_timestamp) or None on failure.
    """
    command_str_log = " ".join(command_parts)
    log.info(f"Generating baseline data for: {command_str_log}")

    # 1. Capture output
    captured_output_bytes, exit_code = capture_command_output(command_parts)
    if captured_output_bytes is None:
        log.error(f"Failed baseline: Could not capture output for {command_str_log}")
        return None

    # 2. Calculate CRC
    try:
        calculated_crc_hex = calculate_hex_crc32(captured_output_bytes)
        log.info(f"  Calculated CRC: {calculated_crc_hex}")
    except Exception as e:
        log.exception(f"Failed baseline: Error calculating CRC for {command_str_log}: {e}")
        return None

    # 3. Determine Paths & Ensure Dirs/Files
    tool_id = command_sequence_to_id(command_parts)
    tool_name = command_parts[0]
    tool_dir = TOOLS_DIR / tool_name
    txt_path = tool_dir / f"{tool_id}.txt"
    json_path = tool_dir / f"{tool_id}.json"

    # 3a. Write .txt file
    try:
        tool_dir.mkdir(parents=True, exist_ok=True)
        txt_path.write_bytes(captured_output_bytes)
        log.info(f"  Wrote TXT baseline: {txt_path.relative_to(WORKSPACE_ROOT)}")
    except OSError as e:
        log.error(f"Failed baseline: Error writing TXT file {txt_path}: {e}")
        return None
    except Exception as e:
        log.exception(f"Failed baseline: Unexpected error writing TXT file {txt_path}: {e}")
        return None

    # 3b. Ensure skeleton JSON exists
    if not ensure_skeleton_json(json_path, command_parts, tool_id):
        log.error(f"Failed baseline: Could not ensure skeleton JSON exists at {json_path}")
        return None  # Fail if skeleton step fails
    else:
        log.info(f"  Ensured skeleton JSON exists: {json_path.relative_to(WORKSPACE_ROOT)}")

    # 4. Get Timestamps
    current_time = time.time()

    # 5. Return data needed for index
    return calculated_crc_hex, current_time, current_time


def discover_subcommands(tool_name: str) -> List[str]:
    """Discovers subcommands by reading the base tool's JSON definition file."""
    base_tool_id = command_sequence_to_id((tool_name,))
    json_path = TOOLS_DIR / tool_name / f"{base_tool_id}.json"

    log.debug(f"Attempting to discover subcommands for '{tool_name}' from {json_path.relative_to(WORKSPACE_ROOT)}")

    if not json_path.is_file():
        log.debug(f"  Base JSON definition not found for {tool_name}. Cannot discover subcommands yet.")
        return []

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Check for the 'subcommands' key, expecting a dictionary/map
        subcommands_data = json_data.get("subcommands")
        if isinstance(subcommands_data, dict):
            subcommand_names = list(subcommands_data.keys())
            log.debug(f"  Found subcommands defined in JSON: {subcommand_names}")
            return subcommand_names
        elif subcommands_data is None:
            log.debug(f"  No 'subcommands' key found in {json_path.relative_to(WORKSPACE_ROOT)}.")
            return []
        else:
            log.warning(
                f"  Expected 'subcommands' key in {json_path.relative_to(WORKSPACE_ROOT)} to be a dictionary, but found type {type(subcommands_data)}. Ignoring."
            )
            return []

    except json.JSONDecodeError as e:
        log.warning(f"  Error decoding JSON {json_path.relative_to(WORKSPACE_ROOT)}: {e}. Cannot discover subcommands.")
        return []
    except Exception as e:
        log.exception(
            f"  Unexpected error reading {json_path.relative_to(WORKSPACE_ROOT)}: {e}. Cannot discover subcommands."
        )
        return []


def determine_index_structure(command_parts: Tuple[str, ...]) -> Dict[str, Any]:
    """Determines the default command/args structure for the index entry."""
    # Assumption: Default structure is just command name and empty args.
    # Specific tools like bandit, ruff check/format might need overrides.
    # TODO: Implement override mechanism (e.g., read from dedicated config?).
    tool_id = command_sequence_to_id(command_parts)
    structure = {
        "command": " ".join(command_parts),
        "args": [],
        # Baseline/skeleton filenames derived deterministically from tool_id
        "baseline_file": f"{tool_id}.txt",
        "json_skeleton_file": f"{tool_id}.json",
    }
    # --- Apply Known Overrides (Example - Needs proper config mechanism) ---
    if tool_id == "bandit":
        structure["args"] = ["-r", "."]
        structure["baseline_file"] = "bandit_report.txt"  # Original name
        structure["json_skeleton_file"] = "bandit_report_skeleton.json"  # Original name
    elif tool_id == "ruff_check":
        structure["args"] = ["."]
        structure["baseline_file"] = "ruff_check_report.txt"
        structure["json_skeleton_file"] = "ruff_check_report_skeleton.json"
    elif tool_id == "ruff_format":
        structure["command"] = "ruff format"  # Base command without args here
        structure["args"] = ["--diff", "."]
        structure["baseline_file"] = "ruff_format_diff.txt"
        structure["json_skeleton_file"] = "ruff_format_diff_skeleton.json"
    # Add other known overrides here...
    # --- End Overrides ---
    log.debug(f"Determined index structure for {tool_id}: {structure}")
    return structure


# --- Main Regeneration Function ---


def regenerate_index() -> None:
    """Orchestrates the regeneration of the tool_index.json file."""
    log.info("Starting tool_index.json regeneration...")

    pyproject_data = load_pyproject_toml(PYPROJECT_PATH)
    whitelist = get_tool_whitelist(pyproject_data)
    venv_executables = get_venv_executables()

    managed_executables = whitelist.intersection(venv_executables)
    missing_executables = whitelist - venv_executables

    if missing_executables:
        log.warning(f"Whitelisted tools not found in environment: {sorted(list(missing_executables))}")

    if not managed_executables:
        log.error("No whitelisted tools found in the environment. Cannot generate index.")
        sys.exit(1)

    log.info(f"Found {len(managed_executables)} managed executables in venv: {sorted(list(managed_executables))}")

    new_index_data: Dict[str, Dict[str, Any]] = {}

    for tool_name in sorted(list(managed_executables)):
        log.info(f"Processing tool: {tool_name}...")
        base_command_parts = (tool_name,)

        # --- Process Base Tool ---
        tool_id = command_sequence_to_id(base_command_parts)
        baseline_data = generate_baseline_data(base_command_parts)
        if baseline_data:
            crc, updated_ts, checked_ts = baseline_data
            index_entry = determine_index_structure(base_command_parts)
            index_entry["crc"] = crc
            index_entry["updated_timestamp"] = updated_ts
            index_entry["checked_timestamp"] = checked_ts
            new_index_data[tool_id] = index_entry
        else:
            log.warning(f"Failed to generate baseline data for base tool: {tool_name}")

        # --- Discover and Process Subcommands (Placeholder) ---
        subcommands = discover_subcommands(tool_name)
        if subcommands:
            log.info(f"  Discovered subcommands: {subcommands}")
            # Ensure base entry has a subcommands dict if not already present
            # Check if the base entry was successfully created first
            if tool_id in new_index_data:
                if "subcommands" not in new_index_data[tool_id]:
                    new_index_data[tool_id]["subcommands"] = {}

                for sub_name in subcommands:
                    sub_command_parts = (tool_name, sub_name)
                    sub_tool_id = command_sequence_to_id(sub_command_parts)
                    log.info(f"  Processing subcommand: {sub_name} (ID: {sub_tool_id})")

                    sub_baseline_data = generate_baseline_data(sub_command_parts)
                    if sub_baseline_data:
                        sub_crc, sub_updated_ts, sub_checked_ts = sub_baseline_data

                        # Structure for index: nested under base command
                        sub_entry = {
                            "crc": sub_crc,
                            "updated_timestamp": sub_updated_ts,
                            "checked_timestamp": sub_checked_ts,
                            # Note: The command/args structure for subcommands is NOT
                            # determined here; it belongs in the AI-populated JSON definition.
                            # The index only stores CRC/timestamps for subcommands found in the JSON.
                        }
                        new_index_data[tool_id]["subcommands"][sub_name] = sub_entry
                    else:
                        log.warning(f"Failed to generate baseline data for subcommand: {sub_name}")
            else:
                log.warning(
                    f"Base tool entry for {tool_name} (ID: {tool_id}) was not created (likely baseline failure). Skipping subcommands."
                )

    # --- Write the new index file ---
    log.info(f"Writing regenerated index to {TOOL_INDEX_PATH}...")
    try:
        TOOL_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOOL_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(new_index_data, f, indent=2, sort_keys=True)
        log.info("Index regeneration complete.")
    except IOError as e:
        log.error(f"Failed to write tool index: {e}")
        sys.exit(1)


if __name__ == "__main__":
    regenerate_index()
