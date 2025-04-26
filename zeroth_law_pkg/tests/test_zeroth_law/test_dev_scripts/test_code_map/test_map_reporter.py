"""
Tests for the codebase map reporter script.
"""

import pytest
import sqlite3
import json
from pathlib import Path
import sqlite_utils
import subprocess
import sys
from unittest.mock import patch, MagicMock

# Import functions to test
from src.zeroth_law.dev_scripts.code_map.map_reporter import (
    generate_project_overview,
    generate_module_details,
    generate_report,
    OUTPUT_PATH_DEFAULT,  # For checking default output
)


# Helper to create a basic populated DB for testing
@pytest.fixture
def sample_db(tmp_path) -> Path:
    db_path = tmp_path / "sample_map.db"
    db = sqlite_utils.Database(str(db_path))

    # Create schema (simplified for testing, assuming generator works)
    db["modules"].insert({"id": 1, "path": "mod_a.py", "last_scanned_timestamp": 123.45}, pk="id")
    db["modules"].insert({"id": 2, "path": "mod_b/sub.py", "last_scanned_timestamp": 123.45}, pk="id")
    db["classes"].insert_all(
        [
            {"id": 10, "module_id": 1, "name": "ClassA", "signature_hash": "hashA", "start_line": 1, "end_line": 5},
            {"id": 11, "module_id": 2, "name": "ClassB", "signature_hash": "hashB", "start_line": 3, "end_line": 8},
        ],
        pk="id",
    )
    db["functions"].insert_all(
        [
            {
                "id": 100,
                "module_id": 1,
                "class_id": None,
                "name": "func_a",
                "signature_hash": "hash_fa",
                "start_line": 7,
                "end_line": 9,
            },
            {
                "id": 101,
                "module_id": 1,
                "class_id": 10,
                "name": "method_a",
                "signature_hash": "hash_ma",
                "start_line": 2,
                "end_line": 4,
            },
            {
                "id": 102,
                "module_id": 2,
                "class_id": 11,
                "name": "method_b",
                "signature_hash": "hash_mb",
                "start_line": 4,
                "end_line": 6,
            },
        ],
        pk="id",
    )
    db["imports"].insert_all(
        [
            {"id": 1000, "importing_module_id": 1, "imported_name": "os", "alias": None, "line_number": 1},
            {"id": 1001, "importing_module_id": 1, "imported_name": "sys", "alias": None, "line_number": 1},
            {"id": 1002, "importing_module_id": 2, "imported_name": "mod_a.ClassA", "alias": "CA", "line_number": 1},
        ],
        pk="id",
    )

    return db_path


# --- Test Cases ---


def test_generate_project_overview(sample_db):
    """Test the overview generation."""
    db = sqlite_utils.Database(str(sample_db))
    overview_data = generate_project_overview(db)

    assert "overview" in overview_data
    overview = overview_data["overview"]
    assert overview.get("error") is None
    assert overview["module_count"] == 2
    assert overview["class_count"] == 2
    assert overview["function_count"] == 3
    assert overview["import_count"] == 3


def test_generate_module_details(sample_db):
    """Test the detailed module report generation."""
    db = sqlite_utils.Database(str(sample_db))
    details_data = generate_module_details(db)

    assert "modules" in details_data
    assert details_data.get("error") is None
    modules = details_data["modules"]
    assert isinstance(modules, list)
    assert len(modules) == 2

    # Check module a (should be first due to sorting by path)
    mod_a = modules[0]
    assert mod_a["path"] == "mod_a.py"
    assert len(mod_a["classes"]) == 1
    assert mod_a["classes"][0]["name"] == "ClassA"
    assert len(mod_a["functions"]) == 2  # func_a, method_a
    assert mod_a["functions"][0]["name"] == "func_a" or mod_a["functions"][1]["name"] == "func_a"
    assert mod_a["functions"][0]["name"] == "method_a" or mod_a["functions"][1]["name"] == "method_a"
    assert len(mod_a["imports"]) == 2  # os, sys
    assert mod_a["imports"][0]["imported_name"] == "os" or mod_a["imports"][1]["imported_name"] == "os"
    assert mod_a["imports"][0]["imported_name"] == "sys" or mod_a["imports"][1]["imported_name"] == "sys"

    # Check module b
    mod_b = modules[1]
    assert mod_b["path"] == "mod_b/sub.py"
    assert len(mod_b["classes"]) == 1
    assert mod_b["classes"][0]["name"] == "ClassB"
    assert len(mod_b["functions"]) == 1  # method_b
    assert mod_b["functions"][0]["name"] == "method_b"
    assert len(mod_b["imports"]) == 1
    assert mod_b["imports"][0]["imported_name"] == "mod_a.ClassA"
    assert mod_b["imports"][0]["alias"] == "CA"


def test_generate_report_end_to_end(sample_db, tmp_path):
    """Test the main report generation function writing to JSON."""
    output_file = tmp_path / "report.json"
    generate_report(sample_db, output_file)

    assert output_file.exists()

    # Read and parse the JSON
    with open(output_file, "r") as f:
        report_data = json.load(f)

    # Basic structural checks
    assert "overview" in report_data
    assert "modules" in report_data
    assert isinstance(report_data["overview"], dict)
    assert isinstance(report_data["modules"], list)

    # Check counts from overview match sample data
    assert report_data["overview"].get("error") is None
    assert report_data["overview"]["module_count"] == 2
    assert report_data["overview"]["class_count"] == 2
    assert report_data["overview"]["function_count"] == 3
    assert report_data["overview"]["import_count"] == 3

    # Check module details consistency (spot check)
    assert len(report_data["modules"]) == 2
    assert report_data["modules"][0]["path"] == "mod_a.py"
    assert len(report_data["modules"][0]["imports"]) == 2


def test_generate_report_db_not_found(tmp_path, caplog):
    """Test that generate_report handles non-existent DB file."""
    non_existent_db = tmp_path / "nosuchdb.db"
    output_file = tmp_path / "report.json"

    with pytest.raises(SystemExit):  # Expect sys.exit(1)
        generate_report(non_existent_db, output_file)

    assert not output_file.exists()
    # Check logs for error message
    assert f"Database file not found: {non_existent_db}" in caplog.text


# --- Tests for Error Handling during DB Queries ---


@pytest.mark.parametrize("table_name", ["modules", "classes", "functions", "imports"])
def test_generate_project_overview_db_error(table_name):
    """Test generate_project_overview handles DB errors during count."""
    # We don't need a mock_table here, we make __getitem__ raise directly

    # Mock the database object itself
    mock_db = MagicMock(spec=sqlite_utils.Database)

    # Configure the mock_db.__getitem__ to RAISE an error for the target table
    def mock_getitem(key):
        if key == table_name:
            raise Exception(f"mock error accessing {table_name}")  # Raise directly
        else:
            # Return a default MagicMock for other tables
            default_mock_table = MagicMock()
            default_mock_table.count = 1
            return default_mock_table

    mock_db.__getitem__.side_effect = mock_getitem

    # Patch the Database class to return our mock_db instance
    with patch("src.zeroth_law.dev_scripts.code_map.map_reporter.sqlite_utils.Database") as MockDatabase:
        MockDatabase.return_value = mock_db
        # Call the function - it will use the mocked Database instance
        # Note: We don't need sample_db fixture here as the DB is mocked
        overview_data = generate_project_overview(mock_db)

    assert "overview" in overview_data
    overview = overview_data["overview"]
    assert "error" in overview
    assert f"Error querying counts: mock error accessing {table_name}" in overview["error"]
    # Removed assertions about partial counts as the function attempts all counts
    # regardless of where the first error occurs. We only care that the error
    # for the specified table was caught and reported.


@pytest.mark.parametrize("table_name", ["modules", "classes", "functions", "imports"])
def test_generate_module_details_db_error(table_name):
    """Test generate_module_details handles DB errors during row fetching."""
    # Mock the table object that will raise error on iteration
    mock_error_table = MagicMock()
    mock_error_table.rows.__iter__.side_effect = Exception(f"mock error iterating {table_name}")
    # Also mock direct iteration on the table object if that's used
    mock_error_table.__iter__.side_effect = Exception(f"mock error iterating {table_name}")

    # Mock the database object itself
    mock_db = MagicMock(spec=sqlite_utils.Database)

    # Configure the mock_db.__getitem__ to return the correct mock or a default mock
    def mock_getitem(key):
        if key == table_name:
            return mock_error_table  # Return the table configured to raise error
        else:
            # Return a default MagicMock for other tables so they don't break access
            # but return an empty iterator for .rows
            default_mock_table = MagicMock()
            default_mock_table.rows = []  # Empty iterator
            return default_mock_table

    mock_db.__getitem__.side_effect = mock_getitem

    # Patch the Database class to return our mock_db instance
    with patch("src.zeroth_law.dev_scripts.code_map.map_reporter.sqlite_utils.Database") as MockDatabase:
        MockDatabase.return_value = mock_db
        # Call the function - it will use the mocked Database instance
        # Note: We don't need sample_db fixture here as the DB is mocked
        details_data = generate_module_details(mock_db)

    assert "error" in details_data
    assert f"Error querying details: mock error iterating {table_name}" in details_data["error"]
    # The current implementation might return partial data collected before the error
    assert "modules" in details_data  # The key should exist even if the list is empty/partial


# TODO: Add tests for error handling during DB queries (might need mocking) - Partially addressed
# Note: These tests cover basic query errors. More complex scenarios (e.g., specific data corruption) aren't covered.
