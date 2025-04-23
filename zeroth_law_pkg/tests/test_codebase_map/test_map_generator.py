# FILE: tests/test_codebase_map/test_map_generator.py
"""
Tests for the codebase map generator script.
"""

import pytest
import sqlite3
from pathlib import Path
import time
import subprocess
import sys

# Assuming the script is runnable and in the correct location relative to tests
# Adjust the path if necessary based on how tests are run
GENERATOR_SCRIPT = Path(__file__).parent.parent.parent / "tests/codebase_map/map_generator.py"


# Helper function to run the generator script
def run_generator(db_path: Path, src_path: Path, *args, expect_fail: bool = False):
    cmd = [
        sys.executable,
        str(GENERATOR_SCRIPT),
        "--db",
        str(db_path),
        "--src",
        str(src_path),
        "-v",  # Add verbose flag to get debug logs potentially
    ]
    cmd.extend(args)
    # Use Popen to better capture stdout/stderr separately if needed
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    if not expect_fail and process.returncode != 0:
        print("Generator script failed unexpectedly:")
        print("RETURN CODE:", process.returncode)
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        raise subprocess.CalledProcessError(process.returncode, cmd, output=stdout, stderr=stderr)
    elif expect_fail and process.returncode == 0:
        print("Generator script succeeded but failure was expected:")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        raise AssertionError("Generator script succeeded unexpectedly.")

    # Return stdout and stderr for checking log messages
    return stdout, stderr


# Helper function to query the DB
def query_db(db_path: Path, sql: str, params=()):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


# --- Test Cases ---


def test_basic_generation(tmp_path):
    """Test generating the map for a simple file with module, class, function."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    # Create a simple test file
    test_file_path = src_dir / "module_one.py"
    test_file_path.write_text("""
class MyClass:
    def method_one(self, x: int) -> str:
        return str(x)

def top_level_func(y: bool):
    pass
""")

    # Run the generator
    run_generator(db_file, src_dir)

    # --- Assertions ---
    # Check module
    modules = query_db(db_file, "SELECT path FROM modules")
    assert len(modules) == 1
    assert modules[0][0] == "module_one.py"

    # Check class
    classes = query_db(
        db_file,
        "SELECT name FROM classes JOIN modules ON classes.module_id = modules.id WHERE modules.path = ?",
        ("module_one.py",),
    )
    assert len(classes) == 1
    assert classes[0][0] == "MyClass"

    # Check functions (method and top-level)
    functions = query_db(
        db_file,
        """
        SELECT f.name, c.name as class_name
        FROM functions f
        JOIN modules m ON f.module_id = m.id
        LEFT JOIN classes c ON f.class_id = c.id
        WHERE m.path = ?
        ORDER BY f.name
    """,
        ("module_one.py",),
    )

    assert len(functions) == 2
    # ('method_one', 'MyClass')
    assert functions[0][0] == "method_one"
    assert functions[0][1] == "MyClass"  # Check it's linked to the class
    # ('top_level_func', None)
    assert functions[1][0] == "top_level_func"
    assert functions[1][1] is None  # Check class_id is NULL


def test_signature_hash_update(tmp_path):
    """Test that the signature hash is updated when a function signature changes."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    test_file_path = src_dir / "module_two.py"
    initial_content = """
def func_to_change(a):
    pass
"""
    test_file_path.write_text(initial_content)

    # Run first time
    run_generator(db_file, src_dir)

    # Get initial hash
    initial_hash_rows = query_db(db_file, "SELECT signature_hash FROM functions WHERE name = ?", ("func_to_change",))
    assert len(initial_hash_rows) == 1
    initial_hash = initial_hash_rows[0][0]
    assert initial_hash is not None

    # Modify the file (change signature)
    time.sleep(0.1)  # Ensure timestamp changes slightly if needed
    modified_content = """
def func_to_change(a: int) -> None: # Added type hints
    pass
"""
    test_file_path.write_text(modified_content)

    # Run second time
    run_generator(db_file, src_dir)

    # Get updated hash
    updated_hash_rows = query_db(db_file, "SELECT signature_hash FROM functions WHERE name = ?", ("func_to_change",))
    assert len(updated_hash_rows) == 1
    updated_hash = updated_hash_rows[0][0]
    assert updated_hash is not None

    # Assert hash has changed
    assert initial_hash != updated_hash


def test_async_functions(tmp_path):
    """Test that async functions are correctly identified and stored."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    test_file_path = src_dir / "module_async.py"
    test_file_path.write_text("""
import asyncio

async def async_func_one():
    await asyncio.sleep(0)

class AsyncClass:
    async def async_method(self):
        pass
""")

    run_generator(db_file, src_dir)

    # Assert async function and method exist
    functions = query_db(
        db_file,
        """
        SELECT f.name, c.name as class_name
        FROM functions f
        JOIN modules m ON f.module_id = m.id
        LEFT JOIN classes c ON f.class_id = c.id
        WHERE m.path = ?
        ORDER BY f.name
    """,
        ("module_async.py",),
    )

    assert len(functions) == 2
    assert functions[0][0] == "async_func_one"
    assert functions[0][1] is None  # Module level
    assert functions[1][0] == "async_method"
    assert functions[1][1] == "AsyncClass"  # Method


def test_stale_entry_detection(tmp_path):
    """Test that stale entries (deleted files/functions) are detected and logged."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    # Create initial files
    file_a_path = src_dir / "module_a.py"
    file_a_path.write_text("""
def func_one(): pass
def func_two(): pass
""")
    file_b_path = src_dir / "module_b.py"
    file_b_path.write_text("""
class ClassB:
    def method_b(self): pass
""")

    # Initial run
    run_generator(db_file, src_dir)

    # Verify initial state
    assert len(query_db(db_file, "SELECT id FROM modules")) == 2
    assert len(query_db(db_file, "SELECT id FROM classes")) == 1
    assert len(query_db(db_file, "SELECT id FROM functions")) == 3

    # Modify structure: delete file_b, remove func_two from file_a
    file_b_path.unlink()
    file_a_path.write_text("""
def func_one(): pass # func_two removed
""")

    # Second run - capture output
    stdout, stderr = run_generator(db_file, src_dir)
    output = stdout + stderr  # Combine for easier checking

    # Verify database STILL contains the old items (no pruning yet)
    assert len(query_db(db_file, "SELECT id FROM modules WHERE path='module_b.py'")) == 1
    assert len(query_db(db_file, "SELECT id FROM classes WHERE name='ClassB'")) == 1
    assert len(query_db(db_file, "SELECT id FROM functions WHERE name='method_b'")) == 1
    assert len(query_db(db_file, "SELECT id FROM functions WHERE name='func_two'")) == 1

    # Verify audit logs the stale items (check combined stdout/stderr)
    # Note: Relies on the logger writing to stderr by default for WARNING level
    assert "Stale Modules found in DB (not in scan): {'module_b.py'}" in output
    # Query expects (path, class_name, func_name)
    assert "Stale Functions found in DB (not in scan): {('module_a.py', None, 'func_two')" in output
    # ClassB and method_b are implicitly stale because module_b is stale, check they appear too
    assert "Stale Classes found in DB (not in scan): {('module_b.py', 'ClassB')" in output
    assert "Stale Functions found in DB (not in scan): {('module_b.py', 'ClassB', 'method_b')" in output
    assert "Audit complete. Stale entries found require manual verification" in output


def test_pruning_mechanism(tmp_path):
    """Test that stale entries are deleted only when the prune flag is set."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    # Create initial file
    file_path = src_dir / "module_prune.py"
    file_path.write_text("""
def func_keep(): pass
def func_delete(): pass
""")

    # Initial run
    run_generator(db_file, src_dir)
    assert len(query_db(db_file, "SELECT id FROM functions")) == 2

    # Modify file (remove func_delete)
    file_path.write_text("""
def func_keep(): pass
""")

    # Run WITHOUT providing the flag - check logs and DB state
    stdout_no_flag, stderr_no_flag = run_generator(db_file, src_dir)
    output_no_flag = stdout_no_flag + stderr_no_flag
    assert "Stale Function found in DB" in output_no_flag
    assert "Pruning" not in output_no_flag  # Ensure pruning wasn't attempted
    assert len(query_db(db_file, "SELECT id FROM functions")) == 2  # Both still there

    # Run WITH INCORRECT confirmation string
    stdout_wrong, stderr_wrong = run_generator(db_file, src_dir, "--prune-stale-entries", "Oops wrong string")
    output_wrong = stdout_wrong + stderr_wrong
    assert "Pruning confirmation string MISMATCHED" in output_wrong
    assert "Pruning WILL NOT occur" in output_wrong
    assert "Pruning skipped due to confirmation string mismatch" in output_wrong
    assert len(query_db(db_file, "SELECT id FROM functions")) == 2  # Still no deletion

    # Run WITH CORRECT confirmation string
    stdout_prune, stderr_prune = run_generator(db_file, src_dir, "--prune-stale-entries", PRUNE_CONFIRMATION_STRING)
    output_prune = stdout_prune + stderr_prune
    assert "Pruning confirmation string matched." in output_prune
    assert "Stale Function found in DB" in output_prune  # Audit still happens
    assert "Pruning 1 confirmed stale entries..." in output_prune
    assert "Pruned 1 stale functions." in output_prune
    assert "Pruning complete." in output_prune

    # Verify func_delete is GONE from DB
    assert len(query_db(db_file, "SELECT id FROM functions WHERE name = 'func_delete'")) == 0
    assert len(query_db(db_file, "SELECT id FROM functions WHERE name = 'func_keep'")) == 1
    assert len(query_db(db_file, "SELECT id FROM functions")) == 1  # Only one left


# Import constant for use in test
from tests.codebase_map.map_generator import PRUNE_CONFIRMATION_STRING


def test_parsing_error_handling(tmp_path):
    """Test that the generator handles syntax errors in files gracefully."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    # Create one valid file
    valid_file = src_dir / "valid_module.py"
    valid_file.write_text("""
def valid_func(): pass
""")

    # Create one file with a syntax error
    invalid_file = src_dir / "invalid_module.py"
    invalid_file.write_text("""
def invalid_func(:
    pass
""")

    # Run the generator - expect it to finish (return code 0) but log errors
    stdout, stderr = run_generator(db_file, src_dir)
    output = stdout + stderr

    # Check for error log message
    assert f"Error parsing invalid_module.py" in output
    assert "SyntaxError" in output  # Check that the type of error is mentioned

    # Check that the valid file WAS processed
    modules = query_db(db_file, "SELECT path FROM modules")
    assert len(modules) == 1
    assert modules[0][0] == "valid_module.py"

    functions = query_db(db_file, "SELECT name FROM functions")
    assert len(functions) == 1
    assert functions[0][0] == "valid_func"

    # Ensure the invalid file didn't create partial entries
    assert len(query_db(db_file, "SELECT path FROM modules WHERE path = ?", ("invalid_module.py",))) == 0


def test_import_tracking(tmp_path):
    """Test that various import styles are correctly recorded in the imports table."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    # Create a test file with various imports
    test_file_path = src_dir / "module_imports.py"
    test_file_path.write_text("""
import os
import sys, time # Multiple imports on one line
import pandas as pd
from pathlib import Path
from . import local_util
from .subdir import sub_util as su
from ..parent_mod import parent_func
from typing import List, Dict, Optional # Multiple from imports
import logging as log
from collections import *
""")

    # Run the generator
    run_generator(db_file, src_dir)

    # Query the imports table
    imports = query_db(
        db_file,
        """
        SELECT imported_name, alias, line_number
        FROM imports i
        JOIN modules m ON i.importing_module_id = m.id
        WHERE m.path = ?
        ORDER BY line_number, imported_name -- Order for deterministic testing
    """,
        ("module_imports.py",),
    )

    # Assertions (based on the order in the file)
    assert (
        len(imports) == 11
    )  # Expect 11 import records (sys, time count separately, list, dict, optional count separately)

    # Line 2: import os
    assert imports[0] == ("os", None, 2)
    # Line 3: import sys, time
    assert imports[1] == ("sys", None, 3)
    assert imports[2] == ("time", None, 3)
    # Line 4: import pandas as pd
    assert imports[3] == ("pandas", "pd", 4)
    # Line 5: from pathlib import Path
    assert imports[4] == ("pathlib.Path", None, 5)
    # Line 6: from . import local_util
    assert imports[5] == (".local_util", None, 6)
    # Line 7: from .subdir import sub_util as su
    assert imports[6] == (".subdir.sub_util", "su", 7)
    # Line 8: from ..parent_mod import parent_func
    assert imports[7] == ("..parent_mod.parent_func", None, 8)
    # Line 9: from typing import List, Dict, Optional
    assert imports[8] == ("typing.Dict", None, 9)
    assert imports[9] == ("typing.List", None, 9)
    assert imports[10] == ("typing.Optional", None, 9)
    # Line 10: import logging as log (This will be index 11 after sorting)
    # assert imports[11] == ("logging", "log", 10) # Re-querying for clarity below
    # Line 11: from collections import *
    # assert imports[12] == ("collections.*", None, 11) # Re-querying for clarity below

    # Query specifically for the aliased logging and wildcard import
    log_import = query_db(
        db_file, "SELECT imported_name, alias, line_number FROM imports WHERE imported_name = ?", ("logging",)
    )
    assert log_import[0] == ("logging", "log", 10)

    wildcard_import = query_db(
        db_file, "SELECT imported_name, alias, line_number FROM imports WHERE imported_name = ?", ("collections.*",)
    )
    assert wildcard_import[0] == ("collections.*", None, 11)


# TODO: Add test_nested_classes_functions (if needed/supported)
