import pytest
import sys
from pathlib import Path
import json
from typing import Dict, Any # Added Any

# Add path to import the module under test
_test_file_path = Path(__file__).resolve()
_project_root = _test_file_path.parents[2]
_src_path = _project_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Module to be tested (will be created next)
from zeroth_law.dev_scripts.subcommand_discoverer import get_subcommands_from_json

# --- Test Data ---
VALID_JSON_WITH_SUBCOMMANDS = {
    "command": "tool_a",
    "description": "...",
    "subcommands_detail": {
        "sub1": {"description": "Subcommand 1", "json_definition_path": "path/sub1.json"},
        "sub2": {"description": "Subcommand 2"}
    },
    "metadata": {}
}

VALID_JSON_NO_SUBCOMMANDS = {
    "command": "tool_b",
    "description": "...",
    "options": [],
    "metadata": {}
}

VALID_JSON_NULL_SUBCOMMANDS = {
    "command": "tool_c",
    "description": "...",
    "subcommands_detail": None,
    "metadata": {}
}

VALID_JSON_SUBCOMMANDS_NOT_DICT = {
    "command": "tool_d",
    "description": "...",
    "subcommands_detail": ["sub1", "sub2"], # Invalid type
    "metadata": {}
}

INVALID_JSON_SYNTAX = "{\"command\": \"bad\", " # Truncated/invalid JSON

# --- Helper to write JSON --- #
def write_json(path: Path, data: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- Test Cases ---

def test_get_subcommands_success(tmp_path):
    """Test successfully extracting subcommands_detail dictionary."""
    json_path = tmp_path / "tool_a.json"
    write_json(json_path, VALID_JSON_WITH_SUBCOMMANDS)

    subcommands = get_subcommands_from_json(json_path)

    assert isinstance(subcommands, dict)
    assert subcommands == VALID_JSON_WITH_SUBCOMMANDS["subcommands_detail"]

def test_get_subcommands_missing_key(tmp_path):
    """Test when the subcommands_detail key is missing."""
    json_path = tmp_path / "tool_b.json"
    write_json(json_path, VALID_JSON_NO_SUBCOMMANDS)

    subcommands = get_subcommands_from_json(json_path)

    assert isinstance(subcommands, dict)
    assert subcommands == {}

def test_get_subcommands_null_value(tmp_path):
    """Test when subcommands_detail is explicitly null."""
    json_path = tmp_path / "tool_c.json"
    write_json(json_path, VALID_JSON_NULL_SUBCOMMANDS)

    subcommands = get_subcommands_from_json(json_path)

    assert isinstance(subcommands, dict)
    assert subcommands == {}

def test_get_subcommands_invalid_type(tmp_path):
    """Test when subcommands_detail is not a dictionary."""
    json_path = tmp_path / "tool_d.json"
    write_json(json_path, VALID_JSON_SUBCOMMANDS_NOT_DICT)

    # Expecting graceful handling (empty dict) rather than error
    subcommands = get_subcommands_from_json(json_path)
    assert isinstance(subcommands, dict)
    assert subcommands == {}
    # Optionally, check for a log warning here if logging is implemented

def test_get_subcommands_file_not_found():
    """Test when the JSON file does not exist."""
    missing_path = Path("./non_existent_tool.json")
    if missing_path.exists():
        missing_path.unlink()

    # Expecting graceful handling (empty dict)
    subcommands = get_subcommands_from_json(missing_path)
    assert isinstance(subcommands, dict)
    assert subcommands == {}
    # Optionally, check for a log warning/error

def test_get_subcommands_invalid_json(tmp_path):
    """Test when the file contains invalid JSON syntax."""
    json_path = tmp_path / "bad_tool.json"
    json_path.write_text(INVALID_JSON_SYNTAX, encoding="utf-8")

    # Expecting graceful handling (empty dict)
    subcommands = get_subcommands_from_json(json_path)
    assert isinstance(subcommands, dict)
    assert subcommands == {}
    # Optionally, check for a log error