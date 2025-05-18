# FILE: tests/test_zeroth_law/test_dev_scripts/test_code_map/test_map_generator.py
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
import logging

# Define workspace root relative to this test file
# Adjust parent count for new location: tests/test_zeroth_law/test_dev_scripts/test_code_map/test_this_file.py
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.parent  # Go up 5 levels
GENERATOR_SCRIPT = WORKSPACE_ROOT / "src" / "zeroth_law" / "dev_scripts" / "code_map" / "map_generator.py"
# Define schema path relative to workspace root
SCHEMA_FILE = WORKSPACE_ROOT / "src" / "zeroth_law" / "dev_scripts" / "code_map" / "schema.sql"
log = logging.getLogger(__name__)


# Helper function to run the generator script
def run_generator(db_path: Path, src_path: Path, *args, expect_fail: bool = False):
    # Resolve the script path explicitly here to be sure
    resolved_generator_script = GENERATOR_SCRIPT.resolve()
    resolved_schema_file = SCHEMA_FILE.resolve()

    cmd = [
        sys.executable,
        str(resolved_generator_script),  # Use resolved path
        "--db",
        str(db_path),
        "--src",
        str(src_path),
        "--schema",
        str(resolved_schema_file),  # Use resolved path
        "-v",
    ]
    cmd.extend(args)

    # Create a copy of the current environment and update PYTHONPATH
    env = os.environ.copy()
    # Add WORKSPACE_ROOT to PYTHONPATH to allow imports relative to project root
    # Use resolved path for WORKSPACE_ROOT in PYTHONPATH as well
    env["PYTHONPATH"] = str(WORKSPACE_ROOT.resolve()) + os.pathsep + env.get("PYTHONPATH", "")

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
def get_signature_hash(
    db_path: Path,
    item_type: str,
    item_name: str,
    module_path: str = None,
    class_name: str = None,
):
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
    test_file_path.write_text(
        """
class MyClass:
    def method_one(self, x: int) -> str:
        return str(x)

def top_level_func(y: bool):
    pass
"""
    )

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
    initial_hash_rows = query_db(
        db_file,
        "SELECT signature_hash FROM functions WHERE name = ?",
        ("func_to_change",),
    )
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
    updated_hash_rows = query_db(
        db_file,
        "SELECT signature_hash FROM functions WHERE name = ?",
        ("func_to_change",),
    )
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
    test_file_path.write_text(
        """
import asyncio

async def async_func_one():
    await asyncio.sleep(0)

class AsyncClass:
    async def async_method(self):
        pass
"""
    )

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
    # ('async_func_one', None)
    assert functions[0][0] == "async_func_one"
    assert functions[0][1] is None
    # ('async_method', 'AsyncClass')
    assert functions[1][0] == "async_method"
    assert functions[1][1] == "AsyncClass"

    # Optional: Check is_async flag if added to schema
    # async_flags = query_db(db_file, "SELECT name, is_async FROM functions WHERE module_id = (SELECT id FROM modules WHERE path = ?) ORDER BY name", ("module_async.py",))
    # assert async_flags == [('async_func_one', 1), ('async_method', 1)]


@pytest.mark.xfail(reason="Pruning/stale detection logic needs review")
def test_stale_entry_detection(tmp_path):
    """Test that entries for deleted files/functions/classes are marked or removed."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    file_to_delete = src_dir / "to_delete.py"
    file_to_modify = src_dir / "to_modify.py"

    file_to_delete.write_text(
        """
def func_in_deleted_file(): pass
class ClassInDeletedFile: pass
"""
    )
    file_to_modify.write_text(
        """
def func_present(): pass
def func_to_be_deleted(): pass
class ClassPresent: pass
class ClassToBeDeleted: pass
"""
    )

    # Initial run
    run_generator(db_file, src_dir)

    # Verify initial state
    assert len(query_db(db_file, "SELECT 1 FROM modules WHERE path=?", ("to_delete.py",))) == 1
    assert (
        len(
            query_db(
                db_file,
                "SELECT 1 FROM functions WHERE name=?",
                ("func_in_deleted_file",),
            )
        )
        == 1
    )
    assert len(query_db(db_file, "SELECT 1 FROM classes WHERE name=?", ("ClassInDeletedFile",))) == 1
    assert len(query_db(db_file, "SELECT 1 FROM functions WHERE name=?", ("func_to_be_deleted",))) == 1
    assert len(query_db(db_file, "SELECT 1 FROM classes WHERE name=?", ("ClassToBeDeleted",))) == 1

    # Modify the source: delete file, delete func/class from other file
    time.sleep(0.1)
    file_to_delete.unlink()
    file_to_modify.write_text(
        """
def func_present(): pass # func_to_be_deleted removed
class ClassPresent: pass # ClassToBeDeleted removed
"""
    )

    # Run generator again (should prune)
    # Modify the run_generator call if pruning requires a specific flag
    # For example: run_generator(db_file, src_dir, "--prune")
    run_generator(db_file, src_dir)  # Assume pruning is default or handled internally

    # Verify pruning
    # Using COUNT(*) as a simpler check for non-existence
    assert query_db(db_file, "SELECT COUNT(*) FROM modules WHERE path=?", ("to_delete.py",))[0][0] == 0
    assert (
        query_db(
            db_file,
            "SELECT COUNT(*) FROM functions WHERE name=?",
            ("func_in_deleted_file",),
        )[0][0]
        == 0
    )
    assert (
        query_db(
            db_file,
            "SELECT COUNT(*) FROM classes WHERE name=?",
            ("ClassInDeletedFile",),
        )[0][0]
        == 0
    )
    assert (
        query_db(
            db_file,
            "SELECT COUNT(*) FROM functions WHERE name=?",
            ("func_to_be_deleted",),
        )[0][0]
        == 0
    )
    assert query_db(db_file, "SELECT COUNT(*) FROM classes WHERE name=?", ("ClassToBeDeleted",))[0][0] == 0

    # Verify remaining items still exist
    assert query_db(db_file, "SELECT COUNT(*) FROM modules WHERE path=?", ("to_modify.py",))[0][0] == 1
    assert query_db(db_file, "SELECT COUNT(*) FROM functions WHERE name=?", ("func_present",))[0][0] == 1
    assert query_db(db_file, "SELECT COUNT(*) FROM classes WHERE name=?", ("ClassPresent",))[0][0] == 1


@pytest.mark.xfail(reason="Pruning logic for non-processed files needs review")
def test_pruning_mechanism(tmp_path):
    """More focused test on the pruning mechanism itself."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    # Create files
    file1 = src_dir / "file1.py"
    file2 = src_dir / "sub" / "file2.py"
    (src_dir / "sub").mkdir()
    file1.write_text("def func1(): pass")
    file2.write_text("class Class2: pass")

    # Run 1: Populate
    run_generator(db_file, src_dir)
    assert query_db(db_file, "SELECT COUNT(*) FROM modules")[0][0] == 2
    assert query_db(db_file, "SELECT COUNT(*) FROM functions")[0][0] == 1
    assert query_db(db_file, "SELECT COUNT(*) FROM classes")[0][0] == 1

    # Simulate passage of time for timestamp check
    time.sleep(0.1)

    # Run 2: Only process file1, file2 should be marked stale/pruned
    run_generator(db_file, file1.parent)  # Run only on the parent of file1

    # Check file2 module, function, class are gone
    assert query_db(db_file, "SELECT COUNT(*) FROM modules WHERE path=?", ("sub/file2.py",))[0][0] == 0
    assert query_db(db_file, "SELECT COUNT(*) FROM classes WHERE name=?", ("Class2",))[0][0] == 0

    # Check file1 stuff remains
    assert query_db(db_file, "SELECT COUNT(*) FROM modules WHERE path=?", ("file1.py",))[0][0] == 1
    assert query_db(db_file, "SELECT COUNT(*) FROM functions WHERE name=?", ("func1",))[0][0] == 1


def test_parsing_error_handling(tmp_path):
    """Test that the script handles Python files with syntax errors gracefully."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    # File with valid syntax
    valid_file = src_dir / "valid.py"
    valid_file.write_text("def good_func(): pass")

    # File with syntax error
    invalid_file = src_dir / "invalid.py"
    invalid_file.write_text("def bad_func(:")  # Syntax error

    # Run the generator - expect it to complete but log errors
    stdout, stderr = run_generator(db_file, src_dir, expect_fail=False)  # Don't fail the run

    # Check that the valid file was processed
    assert query_db(db_file, "SELECT COUNT(*) FROM modules WHERE path=?", ("valid.py",))[0][0] == 1
    assert query_db(db_file, "SELECT COUNT(*) FROM functions WHERE name=?", ("good_func",))[0][0] == 1

    # Check that the invalid file is NOT in the modules table (or marked as error)
    # Depending on implementation, it might be excluded or have an error flag.
    # Let's assume exclusion for now.
    assert query_db(db_file, "SELECT COUNT(*) FROM modules WHERE path=?", ("invalid.py",))[0][0] == 0

    # Check stderr or logs for the parsing error message
    # This depends on the script's logging implementation
    # Example: Check stderr
    assert "Error parsing" in stderr
    assert "invalid.py" in stderr


@pytest.mark.xfail(reason="Import storage format for relative/aliased imports needs review")
def test_import_tracking(tmp_path):
    """Test tracking of import statements."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()

    # Create files with various import types
    file_a = src_dir / "file_a.py"
    file_b = src_dir / "file_b.py"
    file_c = src_dir / "sub" / "file_c.py"
    (src_dir / "sub").mkdir()

    file_a.write_text(
        """
import os
import sys as system
"""
    )
    file_b.write_text(
        """
from pathlib import Path
from file_a import system
from .sub.file_c import AnotherClass # Relative import
"""
    )
    file_c.write_text(
        """
class AnotherClass: pass
"""
    )

    run_generator(db_file, src_dir)

    # Check imports for file_a
    imports_a = query_db(
        db_file,
        "SELECT imported_name, alias FROM imports WHERE importing_module_id = (SELECT id FROM modules WHERE path = ?) ORDER BY imported_name",
        ("file_a.py",),
    )
    assert imports_a == [("os", None), ("sys", "system")]

    # Check imports for file_b
    imports_b = query_db(
        db_file,
        "SELECT imported_name, alias FROM imports WHERE importing_module_id = (SELECT id FROM modules WHERE path = ?) ORDER BY imported_name",
        ("file_b.py",),
    )
    # Note: Relative import might be resolved/stored differently depending on implementation
    # Assuming it stores the intended full path or the relative path itself.
    # Let's assume it stores the provided string for now.
    assert imports_b == [
        (".sub.file_c", "AnotherClass"),  # Check how relative imports are stored
        ("file_a", "system"),
        ("pathlib", "Path"),
    ]

    # Check imports for file_c (should be none)
    imports_c = query_db(
        db_file,
        "SELECT imported_name, alias FROM imports WHERE importing_module_id = (SELECT id FROM modules WHERE path = ?)",
        ("sub/file_c.py",),
    )
    assert imports_c == []


@pytest.mark.xfail(reason="Signature hashing for default value change needs review")
def test_detailed_signature_hashing(tmp_path):
    """Test that different aspects of signature change the hash."""
    src_dir = tmp_path / "src"
    db_file = tmp_path / "test_map.db"
    src_dir.mkdir()
    test_file_path = src_dir / "sig_test.py"

    # 1. Base function
    content1 = "def func(a): pass"
    test_file_path.write_text(content1)
    run_generator(db_file, src_dir)
    hash1 = get_signature_hash(db_file, "function", "func", module_path="sig_test.py")

    # 2. Add type hint to arg
    time.sleep(0.1)
    content2 = "def func(a: int): pass"
    test_file_path.write_text(content2)
    run_generator(db_file, src_dir)
    hash2 = get_signature_hash(db_file, "function", "func", module_path="sig_test.py")
    assert hash1 != hash2

    # 3. Add return type hint
    time.sleep(0.1)
    content3 = "def func(a: int) -> None: pass"
    test_file_path.write_text(content3)
    run_generator(db_file, src_dir)
    hash3 = get_signature_hash(db_file, "function", "func", module_path="sig_test.py")
    assert hash2 != hash3

    # 4. Change argument name
    time.sleep(0.1)
    content4 = "def func(b: int) -> None: pass"
    test_file_path.write_text(content4)
    run_generator(db_file, src_dir)
    hash4 = get_signature_hash(db_file, "function", "func", module_path="sig_test.py")
    # Changing only the name might or might not change hash depending on implementation
    # Let's assume it *does* for robustness
    assert hash3 != hash4

    # 5. Add default value
    time.sleep(0.1)
    content5 = "def func(b: int = 0) -> None: pass"
    test_file_path.write_text(content5)
    run_generator(db_file, src_dir)
    hash5 = get_signature_hash(db_file, "function", "func", module_path="sig_test.py")
    assert hash4 != hash5

    # 6. Change default value
    time.sleep(0.1)
    content6 = "def func(b: int = 1) -> None: pass"
    test_file_path.write_text(content6)
    run_generator(db_file, src_dir)
    hash6 = get_signature_hash(db_file, "function", "func", module_path="sig_test.py")
    assert hash5 != hash6

    # 7. Make it async
    time.sleep(0.1)
    content7 = "async def func(b: int = 1) -> None: pass"
    test_file_path.write_text(content7)
    run_generator(db_file, src_dir)
    hash7 = get_signature_hash(db_file, "function", "func", module_path="sig_test.py")
    assert hash6 != hash7

    # Test class signatures
    class_content1 = "class MyCls: pass"
    test_file_path.write_text(class_content1)
    run_generator(db_file, src_dir)
    class_hash1 = get_signature_hash(db_file, "class", "MyCls", module_path="sig_test.py")

    # Add inheritance
    time.sleep(0.1)
    class_content2 = "class MyCls(object): pass"
    test_file_path.write_text(class_content2)
    run_generator(db_file, src_dir)
    class_hash2 = get_signature_hash(db_file, "class", "MyCls", module_path="sig_test.py")
    assert class_hash1 != class_hash2

    # Add metaclass
    time.sleep(0.1)
    class_content3 = "class MyMeta(type): pass\nclass MyCls(object, metaclass=MyMeta): pass"
    test_file_path.write_text(class_content3)
    run_generator(db_file, src_dir)
    class_hash3 = get_signature_hash(db_file, "class", "MyCls", module_path="sig_test.py")
    assert class_hash2 != class_hash3


# <<< ZEROTH LAW FOOTER >>>
