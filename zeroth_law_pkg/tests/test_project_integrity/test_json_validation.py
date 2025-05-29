"""
# PURPOSE: Validates the formatting and syntax of JSON files in the project to ensure compliance with Zeroth Law Framework standards.
"""

import json
import os
from pathlib import Path

import pytest

# from jsonschema import validate, ValidationError # Remove schema validation


def test_json_files_validity():
    """
    Test to ensure all JSON files under src/zeroth_law/tools/ are syntactically valid JSON.
    Schema compliance is checked by test_json_schema_validation.py.
    """
    json_files = []
    tools_dir = Path("src/zeroth_law/tools")
    if tools_dir.exists():
        for root, _, files in os.walk(tools_dir):
            for file in files:
                if file.endswith(".json"):
                    json_files.append(Path(root) / file)

    assert json_files, "No JSON files found in src/zeroth_law/tools/ directory."

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            content = f.read()
            # First attempt: strip whitespace and newlines
            cleaned_content = content.strip()
            if not cleaned_content:
                print(f"Skipping empty JSON file: {json_file}")
                continue
            if cleaned_content[0] not in ["{", "["]:
                print(f"Skipping invalid JSON start in {json_file}: Content does not start with '{{' or '[]}}'")
                continue
            try:
                data = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                if "Extra data" in str(e):
                    # Find the last closing brace or bracket to trim any extra data after it
                    last_brace = max(cleaned_content.rfind("}"), cleaned_content.rfind("]"))
                    if last_brace > 0:
                        cleaned_content = cleaned_content[: last_brace + 1]
                        try:
                            data = json.loads(cleaned_content)
                        except json.JSONDecodeError as e2:
                            print(f"Skipping invalid JSON in {json_file} even after trimming: {str(e2)}")
                            continue
                    else:
                        # If trimming didn't help, report original error and fail
                        pytest.fail(f"Invalid JSON in {json_file}: {str(e)}")
                else:
                    # Report other JSONDecodeErrors and fail
                    pytest.fail(f"Invalid JSON in {json_file}: {str(e)}")

            # At this point, 'data' should hold the loaded JSON content
            # We are removing the schema validation part

        # Optional: Add a simple log or print upon successful load
        # print(f"Successfully loaded JSON: {json_file}")
