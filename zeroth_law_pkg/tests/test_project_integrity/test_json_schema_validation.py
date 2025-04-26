# FILE: tests/test_zeroth_law/test_tool_defs/test_json_schema_validation.py
"""
Tests to validate tool definition JSON files against the ZLT tool schema.
Relies on fixtures from the root conftest.py for managed sequences and paths.
"""

import json
import logging
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest

# Removed outdated relative import:
# from .conftest import command_sequence_to_id
# Fixtures like 'managed_sequences', 'TOOLS_DIR', 'ZLT_SCHEMA_PATH' are session-scoped
# and automatically provided by the root conftest.py.

log = logging.getLogger(__name__)


# Helper function to get project root (assuming test runs from workspace root)
def get_project_root():
    # A more robust way might involve searching upwards or using a fixture
    # For now, assume current working directory is workspace root or use relative path logic
    return Path(__file__).resolve().parents[2]  # tests/test_project_integrity -> tests -> workspace


PROJECT_ROOT = get_project_root()
FIX_JSON_WHITESPACE_SCRIPT = PROJECT_ROOT / "src" / "zeroth_law" / "dev_scripts" / "fix_json_whitespace.py"
FIX_JSON_SCHEMA_SCRIPT = PROJECT_ROOT / "src" / "zeroth_law" / "dev_scripts" / "fix_json_schema.py"


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
    # WORKSPACE_ROOT: Path, # Using locally derived PROJECT_ROOT for script paths
):
    """Validate each managed tool's JSON definition against the schema."""

    if not managed_sequences:
        pytest.skip("No managed tool names provided by the fixture.")

    # Check if fix scripts exist
    if not FIX_JSON_WHITESPACE_SCRIPT.is_file():
        pytest.fail(f"Fix script not found: {FIX_JSON_WHITESPACE_SCRIPT}")
    if not FIX_JSON_SCHEMA_SCRIPT.is_file():
        pytest.fail(f"Fix script not found: {FIX_JSON_SCHEMA_SCRIPT}")

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

        instance_data = None
        attempted_fix = False
        fix_script_used = None

        # --- Attempt 1: Load and Validate ---
        try:
            # Initial Load attempt
            try:
                with open(json_file_path, "r", encoding="utf-8") as f:
                    instance_data = json.load(f)
            except json.JSONDecodeError as initial_decode_error:
                log.warning(
                    f"Initial JSON decode failed for {json_file_path}: {initial_decode_error}. Attempting whitespace fix..."
                )
                fix_script_used = FIX_JSON_WHITESPACE_SCRIPT
                # Attempt whitespace fix
                result = subprocess.run(
                    [sys.executable, str(fix_script_used), str(json_file_path)],
                    capture_output=True,
                    text=True,
                    check=False,  # Don't check=True, handle exit code
                    cwd=PROJECT_ROOT,  # Run from project root
                )
                log.info(
                    f"Whitespace Fix Script Output for {json_file_path.name}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )
                if result.returncode != 0:
                    log.error(f"Whitespace fix script failed for {json_file_path} with code {result.returncode}")
                    # Don't retry load if fix script itself failed
                    raise initial_decode_error  # Re-raise original error

                attempted_fix = True
                # Retry load after whitespace fix
                try:
                    with open(json_file_path, "r", encoding="utf-8") as f:
                        instance_data = json.load(f)
                    log.info(f"Successfully loaded {json_file_path} after whitespace fix.")
                except json.JSONDecodeError as retry_decode_error:
                    log.error(
                        f"JSON decode still failed for {json_file_path} after whitespace fix: {retry_decode_error}"
                    )
                    validation_failures.append(
                        f"FATAL: Decode error persists after whitespace fix for {json_file_path}: {retry_decode_error}"
                    )
                    continue  # Skip to next file

            # Initial Validation attempt (if load succeeded)
            jsonschema.validate(instance=instance_data, schema=tool_definition_schema)
            log.debug(f"Schema validation successful for {json_file_path} (initial pass)")

        except jsonschema.exceptions.ValidationError as initial_validation_error:
            log.warning(
                f"Initial schema validation failed for {json_file_path}: {initial_validation_error.message}. Attempting schema structure fix..."
            )
            fix_script_used = FIX_JSON_SCHEMA_SCRIPT
            # Attempt schema structure fix
            result = subprocess.run(
                [sys.executable, str(fix_script_used), str(json_file_path)],
                capture_output=True,
                text=True,
                check=False,  # Don't check=True, handle exit code
                cwd=PROJECT_ROOT,  # Run from project root
            )
            log.info(
                f"Schema Fix Script Output for {json_file_path.name}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
            if result.returncode != 0:
                log.error(f"Schema fix script failed for {json_file_path} with code {result.returncode}")
                # Fall through to report original error if fix script failed
                validation_failures.append(
                    f"FAILED FIX ATTEMPT (Script Error {result.returncode}): Schema validation failed for {json_file_path}:\n{initial_validation_error.message}"
                )
                continue  # Skip to next file

            attempted_fix = True
            # Retry load and validation after schema fix
            try:
                with open(json_file_path, "r", encoding="utf-8") as f:
                    retry_instance_data = json.load(f)
                jsonschema.validate(instance=retry_instance_data, schema=tool_definition_schema)
                log.info(f"Successfully validated {json_file_path} after schema fix script.")
                # If successful after fix, don't add to failures
            except json.JSONDecodeError as retry_load_error:
                log.error(f"FATAL: Load failed after schema fix for {json_file_path}: {retry_load_error}")
                validation_failures.append(
                    f"FATAL: Load failed after schema fix for {json_file_path}: {retry_load_error}\nOriginal Error: {initial_validation_error.message}"
                )
            except jsonschema.exceptions.ValidationError as retry_validation_error:
                log.error(
                    f"Schema validation still failed for {json_file_path} after fix attempt: {retry_validation_error.message}"
                )
                validation_failures.append(
                    f"FAILED FIX ATTEMPT: Schema validation failed for {json_file_path} after running {fix_script_used.name}:\n"
                    f"  Retry Error: {retry_validation_error.message}\n"
                    f"  Original Error: {initial_validation_error.message}\n"
                    f"---> ACTION REQUIRED (AI): Manual intervention needed.\n"
                    f"     1. Read the help text: src/zeroth_law/tools/{tool_name}/{tool_id}.txt\n"
                    f"     2. Read this JSON file: {json_file_path.relative_to(PROJECT_ROOT)}\n"
                    f"     3. Correct the JSON structure based ONLY on the .txt, following schema guidelines: tools/zlt_schema_guidelines.md\n"
                    f"     4. AFTER correcting structure, run: uv run python scripts/update_json_crc_tool.py --file {json_file_path.relative_to(PROJECT_ROOT)}\n"
                    f"     5. Re-run pytest for this file."
                )
            except Exception as retry_general_error:
                log.exception(f"Unexpected error during retry for {json_file_path}: {retry_general_error}")
                validation_failures.append(
                    f"FATAL: Unexpected error during retry for {json_file_path}: {retry_general_error}\nOriginal Error: {initial_validation_error.message}"
                )

        except Exception as general_error:
            # Catch other potential errors during initial load/validation
            log.exception(f"Unexpected general error processing {json_file_path}: {general_error}")
            validation_failures.append(f"FATAL: Unexpected error processing {json_file_path}: {general_error}")
            continue  # Skip to next file

    # Assert after checking all files
    assert not validation_failures, "\n".join(["JSON Schema validation errors encountered:"] + validation_failures)


# <<< ZEROTH LAW FOOTER >>>
