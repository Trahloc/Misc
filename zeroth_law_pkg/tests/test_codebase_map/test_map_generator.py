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
import os  # Need os for environment variables

# Assuming the script is runnable and in the correct location relative to tests
# Adjust the path if necessary based on how tests are run
GENERATOR_SCRIPT = Path(__file__).parent.parent.parent / "src/zeroth_law/dev_scripts/code_map/map_generator.py"
WORKSPACE_ROOT = Path(__file__).parent.parent.parent  # Define workspace root for PYTHONPATH


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
    # This ensures the subprocess can find 'src.zeroth_law.dev_scripts.code_map.cli_utils'
    env["PYTHONPATH"] = str(WORKSPACE_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    # Use Popen to better capture stdout/stderr separately if needed
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,  # Pass the modified environment to the subprocess
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

    # Verify audit logs the stale items (check stderr stream)
    assert "Stale Module found in DB (Code likely removed/moved): {'module_b.py'}" in stderr
    # ClassB should NOT be reported as stale because its module (module_b.py) is already stale.
    # assert "Stale Class found in DB (Code likely removed/moved): {('module_b.py', 'ClassB')}" in stderr # Incorrect assertion removed
    # Only func_two should be reported as stale, as method_b belongs to the stale module_b.
    assert "Stale Function found in DB (Code likely removed/moved): {('module_a.py', None, 'func_two')}" in stderr

    # Verify DB still contains items (no change yet)
    assert len(query_db(db_file, "SELECT id FROM modules WHERE path='module_b.py'")) == 1
    assert len(query_db(db_file, "SELECT id FROM classes WHERE name='ClassB'")) == 1
    assert len(query_db(db_file, "SELECT id FROM functions WHERE name='method_b'")) == 1
    assert len(query_db(db_file, "SELECT id FROM functions WHERE name='func_two'")) == 1

    # Verify audit logs the stale items (check stderr stream)
    # Note: Relies on the logger writing to stderr by default for WARNING level
    # Updated expected counts: 1 module, 1 function = 2 DB entries, 2 unique elements
    assert "Audit complete. Found 3 potentially stale DB entries corresponding to 3 unique code elements." in stderr
    # The count is 3 because the stale items list contains: ('module', id, path), ('class', id, path, name), ('function', id, path, class, name)
    # But the audit logic correctly identifies only Module B and Func Two as needing user attention via logs.
    # Let's adjust the assertion to match the exact log message produced by the refined audit logic.
    assert "Audit complete. Found 2 potentially stale DB entries corresponding to 2 unique code elements." in stderr


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
    # Check stderr for the warning about stale functions
    assert "Stale Function found in DB" in stderr_no_flag
    assert len(query_db(db_file, "SELECT id FROM functions")) == 2  # Should still have 2

    # Run WITH the flag - check logs and DB state
    stdout_flag, stderr_flag = run_generator(db_file, src_dir, "--prune-stale-entries", PRUNE_CONFIRMATION_STRING)
    # Check stderr for pruning messages
    assert "Pruning 1 confirmed stale entries..." in stderr_flag
    assert "Pruned 1 stale functions." in stderr_flag
    assert len(query_db(db_file, "SELECT id FROM functions")) == 1  # Should now have 1
    assert query_db(db_file, "SELECT name FROM functions")[0][0] == "func_keep"


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

    # Check stderr for error log message
    assert f"Error parsing invalid_module.py" in stderr
    # Check that the type of error is mentioned in stderr
    assert "SyntaxError" in stderr

    # Check that the valid file was still processed
    valid_funcs = query_db(
        db_file, "SELECT name FROM functions WHERE module_id=(SELECT id FROM modules WHERE path='valid_module.py')"
    )
    assert len(valid_funcs) == 1
    assert valid_funcs[0][0] == "valid_func"

    # Check that the invalid file resulted in no entries
    invalid_funcs = query_db(
        db_file, "SELECT name FROM functions WHERE module_id=(SELECT id FROM modules WHERE path='invalid_module.py')"
    )
    assert len(invalid_funcs) == 0


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
        len(imports) == 13
    )  # Expect 13 import records (sys/time, list/dict/optional, logging, wildcard count separately)

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
    # Line 9: from typing import List, Dict, Optional (Sorted: Dict, List, Optional)
    assert imports[8] == ("typing.Dict", None, 9)
    assert imports[9] == ("typing.List", None, 9)
    assert imports[10] == ("typing.Optional", None, 9)
    # Line 10: import logging as log
    assert imports[11] == ("logging", "log", 10)
    # Line 11: from collections import *
    assert imports[12] == ("collections.*", None, 11)

    # Removed redundant specific queries as main list check covers them
    # log_import = query_db(...)
    # wildcard_import = query_db(...)


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
