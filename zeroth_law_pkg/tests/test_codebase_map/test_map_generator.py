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
import os # Need os for environment variables

# Assuming the script is runnable and in the correct location relative to tests
# Adjust the path if necessary based on how tests are run
GENERATOR_SCRIPT = Path(__file__).parent.parent.parent / "tests/codebase_map/map_generator.py"
WORKSPACE_ROOT = Path(__file__).parent.parent.parent # Define workspace root for PYTHONPATH


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

    # Create a copy of the current environment and update PYTHONPATH
    env = os.environ.copy()
    # Add WORKSPACE_ROOT to PYTHONPATH to allow imports relative to project root
    # This ensures the subprocess can find 'tests.codebase_map.cli_utils'
    env['PYTHONPATH'] = str(WORKSPACE_ROOT) + os.pathsep + env.get('PYTHONPATH', '')

    # Use Popen to better capture stdout/stderr separately if needed
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env # Pass the modified environment to the subprocess
    )
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


class LookupError(Exception):
    """Custom exception for database lookup failures."""
    pass


# Helper to get signature hash for a function/method or class
def get_signature_hash(db_path: Path, item_type: str, item_name: str, module_path: str = None, class_name: str = None):
    if item_type not in ["function", "class"]:
        raise ValueError("item_type must be 'function' or 'class'")

    table = "functions" if item_type == "function" else "classes"
    sql = f"SELECT signature_hash FROM {table} WHERE name = ?"
    params = [item_name]

    if module_path:
        sql += " AND module_id = (SELECT id FROM modules WHERE path = ?)"
        params.append(module_path)
    if item_type == "function" and class_name:
        sql += " AND class_id = (SELECT id FROM classes WHERE name = ? AND module_id = (SELECT id FROM modules WHERE path = ?))"
        params.append(class_name)
        params.append(module_path)
    elif item_type == "function":
        sql += " AND class_id IS NULL"

    rows = query_db(db_path, sql, tuple(params))
    if not rows:
        raise LookupError(f"Could not find {item_type} '{item_name}' in the database.")
    if len(rows) > 1:
        # This might happen if not filtering by module/class appropriately
        raise LookupError(f"Found multiple entries for {item_type} '{item_name}'. Specify module/class?")
    return rows[0][0]


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


def test_detailed_signature_hashing(tmp_path):
    """Test signature hashing robustness across various code structures."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()
    test_file = src_dir / "sig_test.py"

    # --- Test Case 1: Body/Docstring/Comment changes should NOT affect hash ---
    content_v1 = """
def func_body_change(a: int) -> str:
    '''Initial docstring.'''
    # Initial comment
    return str(a) # Initial logic
"""
    test_file.write_text(content_v1)
    run_generator(db_file, src_dir)
    hash_v1 = get_signature_hash(db_file, "function", "func_body_change", "sig_test.py")
    assert hash_v1 is not None

    # Modify body, docstring, comment
    content_v2 = """
def func_body_change(a: int) -> str:
    '''Changed docstring.'''
    # Changed comment
    x = int(a) * 2 # Changed logic
    return f"Value: {x}"
"""
    time.sleep(0.1)
    test_file.write_text(content_v2)
    run_generator(db_file, src_dir)
    hash_v2 = get_signature_hash(db_file, "function", "func_body_change", "sig_test.py")
    assert hash_v2 == hash_v1, "Hash changed unexpectedly on body/doc/comment modification"

    # --- Test Case 2: Argument kind changes SHOULD affect hash ---
    content_v3 = """
def func_arg_kinds(a, /, b, *, c, d=1, **kwargs):
    pass
"""
    test_file.write_text(content_v3)
    run_generator(db_file, src_dir)
    hash_v3 = get_signature_hash(db_file, "function", "func_arg_kinds", "sig_test.py")

    content_v4 = """
def func_arg_kinds(a, b, *, c, d=1, **kwargs): # Removed positional-only marker
    pass
"""
    time.sleep(0.1)
    test_file.write_text(content_v4)
    run_generator(db_file, src_dir)
    hash_v4 = get_signature_hash(db_file, "function", "func_arg_kinds", "sig_test.py")
    assert hash_v4 != hash_v3, "Hash did not change for positional-only modification"

    content_v5 = """
def func_arg_kinds(a, b, c, d=1, **kwargs): # Removed keyword-only marker
    pass
"""
    time.sleep(0.1)
    test_file.write_text(content_v5)
    run_generator(db_file, src_dir)
    hash_v5 = get_signature_hash(db_file, "function", "func_arg_kinds", "sig_test.py")
    assert hash_v5 != hash_v4, "Hash did not change for keyword-only modification"

    content_v6 = """
def func_arg_kinds(a, b, c, d=1, *args, **kwargs): # Added *args
    pass
"""
    time.sleep(0.1)
    test_file.write_text(content_v6)
    run_generator(db_file, src_dir)
    hash_v6 = get_signature_hash(db_file, "function", "func_arg_kinds", "sig_test.py")
    assert hash_v6 != hash_v5, "Hash did not change when *args added"

    # --- Test Case 3: Return type changes SHOULD affect hash ---
    content_v7 = """
def func_return_type(x): # No return type
    return x
"""
    test_file.write_text(content_v7)
    run_generator(db_file, src_dir)
    hash_v7 = get_signature_hash(db_file, "function", "func_return_type", "sig_test.py")

    content_v8 = """
def func_return_type(x) -> int: # Added return type
    return x
"""
    time.sleep(0.1)
    test_file.write_text(content_v8)
    run_generator(db_file, src_dir)
    hash_v8 = get_signature_hash(db_file, "function", "func_return_type", "sig_test.py")
    assert hash_v8 != hash_v7, "Hash did not change when return type added"

    content_v9 = """
def func_return_type(x) -> str: # Changed return type
    return x
"""
    time.sleep(0.1)
    test_file.write_text(content_v9)
    run_generator(db_file, src_dir)
    hash_v9 = get_signature_hash(db_file, "function", "func_return_type", "sig_test.py")
    assert hash_v9 != hash_v8, "Hash did not change when return type changed"

    # --- Test Case 4: Decorator changes SHOULD affect hash ---
    content_v10 = """
def my_decorator(f): return f

def func_decorated(p):
    pass
"""
    test_file.write_text(content_v10)
    run_generator(db_file, src_dir)
    hash_v10 = get_signature_hash(db_file, "function", "func_decorated", "sig_test.py")

    content_v11 = """
def my_decorator(f): return f

@my_decorator
def func_decorated(p): # Added decorator
    pass
"""
    time.sleep(0.1)
    test_file.write_text(content_v11)
    run_generator(db_file, src_dir)
    hash_v11 = get_signature_hash(db_file, "function", "func_decorated", "sig_test.py")
    assert hash_v11 != hash_v10, "Hash did not change when decorator added"

    content_v12 = """
def my_decorator(f): return f
def another_decorator(f): return f

@another_decorator # Changed decorator
@my_decorator
def func_decorated(p):
    pass
"""
    time.sleep(0.1)
    test_file.write_text(content_v12)
    run_generator(db_file, src_dir)
    hash_v12 = get_signature_hash(db_file, "function", "func_decorated", "sig_test.py")
    assert hash_v12 != hash_v11, "Hash did not change when decorator changed/added"

    # --- Test Case 5: Class signature changes SHOULD affect hash ---
    content_v13 = """
class BaseClass: pass
class Meta(type): pass

class TargetClass: # No base, no meta
    pass
"""
    test_file.write_text(content_v13)
    run_generator(db_file, src_dir)
    hash_v13 = get_signature_hash(db_file, "class", "TargetClass", "sig_test.py")

    content_v14 = """
class BaseClass: pass
class Meta(type): pass

class TargetClass(BaseClass): # Added base class
    pass
"""
    time.sleep(0.1)
    test_file.write_text(content_v14)
    run_generator(db_file, src_dir)
    hash_v14 = get_signature_hash(db_file, "class", "TargetClass", "sig_test.py")
    assert hash_v14 != hash_v13, "Class hash did not change when base class added"

    content_v15 = """
class BaseClass: pass
class Meta(type): pass

class TargetClass(BaseClass, metaclass=Meta): # Added metaclass
    pass
"""
    time.sleep(0.1)
    test_file.write_text(content_v15)
    run_generator(db_file, src_dir)
    hash_v15 = get_signature_hash(db_file, "class", "TargetClass", "sig_test.py")
    assert hash_v15 != hash_v14, "Class hash did not change when metaclass added"

    # --- Test Case 6: Annotation/Decorator Parsing Errors ---
    # Note: Requires map_generator to handle ast.unparse errors gracefully
    # Check if the implementation adds '<unparse_error>' or similar placeholder
    # This test assumes the generator *completes* but stores a specific error marker

    # Example: Unparseable annotation (e.g., invalid syntax within annotation)
    content_v16 = """
# Type Alias that might be tricky or invalid in some contexts
ComplexType = list[lambda x: x**2] # Simplified, real cases might be more complex

def func_bad_annotation(a: ComplexType):
    pass
"""
    test_file.write_text(content_v16)
    # We expect the generator to run, but the hash might be based on the error marker
    run_generator(db_file, src_dir)
    hash_v16 = get_signature_hash(db_file, "function", "func_bad_annotation", "sig_test.py")
    # The exact assertion depends on how map_generator handles this.
    # If it uses a placeholder like '<unparse_error:annotation>', we could check for its hash.
    # For now, just assert it produced *some* hash. A more specific check
    # requires knowing the exact error handling strategy in map_generator.py
    assert hash_v16 is not None, "Generator failed or didn't produce hash for bad annotation"

    # Example: Unparseable decorator
    content_v17 = """
@some_module.attribute[invalid_syntax]()
def func_bad_decorator():
    pass
"""
    test_file.write_text(content_v17)
    run_generator(db_file, src_dir)
    hash_v17 = get_signature_hash(db_file, "function", "func_bad_decorator", "sig_test.py")
    assert hash_v17 is not None, "Generator failed or didn't produce hash for bad decorator"


# TODO: Add test_nested_classes_functions (if needed/supported)
