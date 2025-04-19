import pytest
import json
import logging
import sys
import zlib
import time
from pathlib import Path

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

# --- Logging Setup ---
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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


# --- Constants ---
CACHE_DURATION_SECONDS = 24 * 60 * 60  # 24 hours


# --- Helper Functions (Can remain module-level) ---
def command_sequence_to_id(command_parts: tuple[str, ...]) -> str:
    """Creates a readable ID for parametrized tests and dictionary keys."""
    return "_".join(command_parts)


def calculate_crc32(text_content: str) -> str:  # Ensure using correct name if defined here, or import
    """Calculates the CRC32 checksum of text content and returns it as a hex string."""
    # Assuming this function is needed by tests directly, otherwise it could be removed
    # if only calculate_crc32 from src.zeroth_law.lib.crc is used by tests.
    # If kept, ensure it matches the implementation in lib/crc.py if necessary.
    CRC32_HEX_WIDTH = 8
    crc_val = zlib.crc32(text_content.encode("utf-8", errors="replace"))
    hex_str = format(crc_val & 0xFFFFFFFF, f"0{CRC32_HEX_WIDTH}x")
    return f"0x{hex_str.upper()}"


# --- Fixture for Index Handling (Session Scoped) ---
@pytest.fixture(scope="session")
def tool_index_handler(WORKSPACE_ROOT: Path, TOOL_INDEX_PATH: Path):
    """Fixture to load, manage, and save the tool index. Depends on path fixtures."""
    index_data = {}
    try:
        if TOOL_INDEX_PATH.is_file():
            with open(TOOL_INDEX_PATH, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            log.info(f"Loaded tool index from: {TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}")
        else:
            log.warning(f"Tool index not found, initializing empty: {TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}")

    except json.JSONDecodeError:
        log.warning(f"Failed to decode existing tool index at {TOOL_INDEX_PATH}. Starting fresh.")
        index_data = {}
    except Exception as e:
        log.error(f"Error loading tool index {TOOL_INDEX_PATH}: {e}")
        pytest.fail(f"Could not load tool index: {e}")

    valid_index_data = {}
    for key, value in index_data.items():
        if isinstance(value, dict) and "crc" in value and "timestamp" in value:
            valid_index_data[key] = value
        else:
            log.warning(f"Invalid entry format for '{key}' in tool index. Discarding.")

    handler_state = {"data": valid_index_data, "dirty": False}

    yield handler_state

    if handler_state["dirty"]:
        try:
            TOOL_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TOOL_INDEX_PATH, "w", encoding="utf-8") as f:
                json.dump(handler_state["data"], f, indent=2, sort_keys=True)
            log.info(f"Saved updated tool index to: {TOOL_INDEX_PATH.relative_to(WORKSPACE_ROOT)}")
        except Exception as e:
            log.error(f"Error saving tool index {TOOL_INDEX_PATH}: {e}")
