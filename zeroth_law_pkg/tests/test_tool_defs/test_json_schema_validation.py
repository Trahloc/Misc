# FILE: tests/test_tool_defs/test_json_schema_validation.py
"""
Validates tool definition JSON files against the defined schema.
"""

import json
import pytest
import logging
from pathlib import Path
from jsonschema import validate, ValidationError

# Reuse constants and helpers from TXT test
from tests.test_tool_defs.test_ensure_txt_baselines_exist import (
    MANAGED_COMMAND_SEQUENCES,
    command_sequence_to_id,
)

# Import fixtures from top-level conftest
from tests.conftest import ZLT_ROOT, TOOLS_DIR, ZLT_SCHEMA_PATH

# Setup logger for this test module
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Path to the schema file (relative to workspace root)
SCHEMA_PATH_RELATIVE = Path("src/zeroth_law/schemas/tool_definition_schema.json")


@pytest.fixture(scope="module")
def tool_definition_schema(WORKSPACE_ROOT):
    """Loads the tool definition JSON schema."""
    schema_path = WORKSPACE_ROOT / SCHEMA_PATH_RELATIVE
    if not schema_path.is_file():
        pytest.fail(f"Schema file not found at expected location: {schema_path}")
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        # Basic check to ensure it looks like a schema
        assert "$schema" in schema
        assert "properties" in schema
        return schema
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode schema file {schema_path}: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load schema file {schema_path}: {e}")


# --- Test Function --- #
@pytest.mark.parametrize(
    "command_parts",
    MANAGED_COMMAND_SEQUENCES,
    ids=[command_sequence_to_id(cp) for cp in MANAGED_COMMAND_SEQUENCES],
)
def test_json_schema_validation(
    command_parts: tuple[str, ...],
    tool_definition_schema,  # Fixture for the loaded schema
    WORKSPACE_ROOT,  # Fixture from conftest
    TOOLS_DIR,  # Fixture from conftest
):
    """Validates a tool's JSON definition against the master schema."""

    if not command_parts:
        pytest.skip("Skipping test for empty command parts.")

    tool_id = command_sequence_to_id(command_parts)
    tool_name = command_parts[0]

    # Construct path to the specific JSON file
    json_file = TOOLS_DIR / tool_name / f"{tool_id}.json"
    relative_json_path = json_file.relative_to(WORKSPACE_ROOT)

    # --- Load JSON Content --- #
    if not json_file.is_file():
        # If the JSON doesn't exist, skip this test.
        # Existence is checked by test_ensure_json_definitions_exist
        pytest.skip(f"Skipping schema validation: JSON file missing for {tool_id} at {relative_json_path}")

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode JSON file {relative_json_path}: {e}")
    except Exception as e:
        pytest.fail(f"Failed to read JSON file {relative_json_path}: {e}")

    # --- Perform Schema Validation --- #
    try:
        validate(instance=json_data, schema=tool_definition_schema)
        log.info(f"Schema validation passed for {relative_json_path}")
    except ValidationError as e:
        # Provide a more detailed error message including the instance and schema path
        fail_message = (
            f"Schema validation FAILED for {relative_json_path}:\n"
            f"  Schema: {SCHEMA_PATH_RELATIVE}\n"
            f"  Error: {e.message}\n"
            f"  Path in JSON: {list(e.path)}\n"
            # f"  Validator: {e.validator} = {e.validator_value}\n"
            # f"  Instance causing error: {e.instance}\n"
            "Action Required: Correct the structure or data types in the JSON file according to the schema."
        )
        pytest.fail(fail_message, pytrace=False)
    except Exception as e:
        # Catch other potential errors during validation
        pytest.fail(f"An unexpected error occurred during schema validation for {relative_json_path}: {e}")
