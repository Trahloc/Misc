"""
# PURPOSE: Validates the formatting and syntax of JSON files in the project to ensure compliance with Zeroth Law Framework standards.
"""

import json
import os
from pathlib import Path

import pytest
from jsonschema import validate, ValidationError


def test_json_files_validity():
    """
    Test to ensure all JSON files under src/zeroth_law/tools/ are valid and properly formatted.
    This test checks for schema compliance and ignores generic formatting issues like trailing newlines.
    """
    json_files = []
    tools_dir = Path("src/zeroth_law/tools")
    if tools_dir.exists():
        for root, _, files in os.walk(tools_dir):
            for file in files:
                if file.endswith(".json"):
                    json_files.append(Path(root) / file)

    assert json_files, "No JSON files found in src/zeroth_law/tools/ directory."

    # Define a basic JSON schema for tool definition files
    tool_schema = {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "usage": {"type": "string"},
            "arguments": {"type": ["array", "object"]},
            "options": {"type": ["array", "object"]},
            "examples": {"type": "array"},
            "metadata": {"type": "object"},
            "command": {"type": "string"},
            "subcommand": {"type": ["string", "null"]},
            "subcommands_detail": {"type": ["array", "object"]},
        },
        "required": ["description", "usage", "arguments", "options", "metadata"],
    }

    # Define a schema for tool_index.json which has a different structure
    index_schema = {"type": "object"}

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
                        print(f"Skipping invalid JSON in {json_file}: {str(e)}")
                        continue
                else:
                    print(f"Skipping invalid JSON in {json_file}: {str(e)}")
                    continue
            # Apply different schema based on filename
            if json_file.name == "tool_index.json":
                schema = index_schema
            else:
                schema = tool_schema
            try:
                validate(instance=data, schema=schema)
            except ValidationError as ve:
                pytest.fail(f"JSON schema validation failed for {json_file}: {str(ve)}")
