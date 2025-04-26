# FILE: tests/test_zeroth_law/test_tool_defs/test_json_schema_validation.py
"""
Tests to validate tool definition JSON files against the ZLT tool schema.
Relies on fixtures from the root conftest.py for managed sequences and paths.
"""

import json
import logging
from pathlib import Path

import jsonschema
import pytest

# Removed outdated relative import:
# from .conftest import command_sequence_to_id
# Fixtures like 'managed_sequences', 'TOOLS_DIR', 'ZLT_SCHEMA_PATH' are session-scoped
# and automatically provided by the root conftest.py.

log = logging.getLogger(__name__)


# Fixture to load the schema once per session (can be moved to conftest if shared)
@pytest.fixture(scope="session")
def tool_definition_schema(ZLT_SCHEMA_PATH: Path) -> dict:
    """Loads the tool definition JSON schema."""
    try:
        with open(ZLT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        log.info(f"Successfully loaded tool definition schema from: {ZLT_SCHEMA_PATH}")
        return schema
    except FileNotFoundError:
        pytest.fail(f"Tool definition schema file not found: {ZLT_SCHEMA_PATH}")
    except json.JSONDecodeError as e:
        pytest.fail(f"Error decoding JSON schema file {ZLT_SCHEMA_PATH}: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error loading schema {ZLT_SCHEMA_PATH}: {e}")


# Test function - Remove parametrization, iterate inside
# @pytest.mark.parametrize("command_sequence", "managed_sequences")
def test_validate_json_definition_against_schema(
    managed_sequences: set[str],  # Accept set of names
    TOOLS_DIR: Path,
    tool_definition_schema: dict,
):
    """Validate each managed tool's JSON definition against the schema."""

    if not managed_sequences:
        pytest.skip("No managed tool names provided by the fixture.")

    validation_failures = []
    for tool_name in managed_sequences:
        # Assume sequence is just the tool name for now
        command_sequence = (tool_name,)

        # Helper to get ID
        def _command_sequence_to_id(parts: tuple[str, ...]) -> str:
            return "_".join(parts) if parts else "_EMPTY_"

        tool_id = _command_sequence_to_id(command_sequence)
        # tool_name is directly available
        json_file_path = TOOLS_DIR / tool_name / f"{tool_id}.json"

        log.debug(f"Validating JSON schema for: {json_file_path}")

        # Check if file exists
        if not json_file_path.is_file():
            # Log or track this, but don't fail the schema test itself
            log.warning(f"JSON file not found, skipping schema validation: {json_file_path}")
            continue  # Skip to next tool

        # Load the JSON instance data
        instance_data = None  # Initialize
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                instance_data = json.load(f)
        except json.JSONDecodeError as e:
            validation_failures.append(f"Error decoding JSON file {json_file_path}: {e}")
            continue  # Skip validation for this file
        except Exception as e:
            validation_failures.append(f"Unexpected error loading JSON file {json_file_path}: {e}")
            continue  # Skip validation for this file

        # Perform validation if data loaded successfully
        if instance_data is not None:
            try:
                jsonschema.validate(instance=instance_data, schema=tool_definition_schema)
                log.debug(f"Schema validation successful for {json_file_path}")
            except jsonschema.exceptions.ValidationError as e:
                validation_failures.append(f"Schema validation failed for {json_file_path}:\n{e}")
            except Exception as e:
                validation_failures.append(f"Unexpected error during schema validation for {json_file_path}: {e}")

    # Assert after checking all files
    assert not validation_failures, "\n".join(["JSON Schema validation errors encountered:"] + validation_failures)


# <<< ZEROTH LAW FOOTER >>>
