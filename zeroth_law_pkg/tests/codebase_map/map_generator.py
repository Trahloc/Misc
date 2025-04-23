# FILE: tests/codebase_map/map_generator.py
"""
# PURPOSE: Generates/updates the SQLite codebase map (`code_map.db`).
#          Uses AST to scan source files and populates the database.
"""

# --- IMPORTS ---
import ast
import sqlite3
import time
from pathlib import Path
import logging
import sys

# --- CONSTANTS ---
# Assuming this script runs from the project root (zeroth_law_pkg)
SRC_DIR = Path("src")
DB_PATH = Path("tests/codebase_map/code_map.db")
SCHEMA_PATH = Path("tests/codebase_map/schema.sql")

# --- LOGGING ---
# Basic logging setup for now
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# --- CORE FUNCTIONS ---


def connect_db(db_path: Path) -> sqlite3.Connection:
    """Connects to the SQLite database. Creates it if it doesn't exist."""
    log.info(f"Connecting to database: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_schema(conn: sqlite3.Connection, schema_path: Path):
    """Creates the database schema from the .sql file if tables don't exist."""
    log.info(f"Checking/creating schema from: {schema_path}")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='modules';")
    if cursor.fetchone():
        log.info("Schema (modules table) already exists.")
        return

    log.info("Schema not found. Creating tables...")
    try:
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
        log.info("Schema created successfully.")
    except Exception as e:
        log.error(f"Error creating schema: {e}")
        conn.rollback()
        raise


def find_python_files(src_dir: Path) -> list[Path]:
    """Finds all .py files within the source directory."""
    log.info(f"Scanning for Python files in: {src_dir}")
    python_files = list(src_dir.rglob("*.py"))
    log.info(f"Found {len(python_files)} Python files.")
    return python_files


def calculate_signature_hash(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> str:
    """Calculates a hash representing the signature of a function/class.
    (Implementation TBD - needs deterministic representation of params, types, etc.)
    """
    # Placeholder implementation
    signature_parts = []
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        signature_parts.append(f"def {node.name}(")
        for i, arg in enumerate(node.args.args):
            signature_parts.append(f"{',' if i > 0 else ''}{arg.arg}")
            if arg.annotation:
                signature_parts.append(f": {ast.unparse(arg.annotation)}")
        signature_parts.append(")")
        if node.returns:
            signature_parts.append(f" -> {ast.unparse(node.returns)}")
    elif isinstance(node, ast.ClassDef):
        signature_parts.append(f"class {node.name}:")
        # Basic hash for classes for now, maybe hash method signatures?
        pass
    # Simple hash for now - replace with something robust like hashlib.sha256
    return hex(hash("".join(signature_parts)))


def process_file(file_path: Path, conn: sqlite3.Connection, current_scan_timestamp: float):
    """Parses a single Python file using AST and updates the database."""
    relative_path = file_path.relative_to(SRC_DIR).as_posix()
    log.debug(f"Processing file: {relative_path}")
    cursor = conn.cursor()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        log.error(f"Error parsing {relative_path}: {e}")
        return  # Skip this file

    # 1. Update/Insert Module
    cursor.execute(
        "INSERT OR REPLACE INTO modules (path, last_scanned_timestamp) VALUES (?, ?)",
        (relative_path, current_scan_timestamp),
    )
    module_id = cursor.lastrowid
    # TODO: Keep track of visited functions/classes in this file to detect deletions later
    processed_in_file = set()

    # 2. Iterate through AST nodes
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            signature_hash = calculate_signature_hash(node)
            start_line = node.lineno
            end_line = node.end_lineno
            log.debug(f"  Found Class: {class_name} (Lines {start_line}-{end_line})")
            # TODO: Insert/Update class in DB, get class_id
            # TODO: Add (module_id, None, class_name) to processed_in_file

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check parent to determine if it's a method or module-level function
            parent_class_id = None
            # TODO: Determine parent_class_id if node is inside a ClassDef
            # (Requires tracking the current class context during walk)

            func_name = node.name
            signature_hash = calculate_signature_hash(node)
            start_line = node.lineno
            end_line = node.end_lineno
            log.debug(f"  Found Function: {func_name} (Lines {start_line}-{end_line}, Class ID: {parent_class_id})")
            # TODO: Insert/Update function in DB
            # TODO: Add (module_id, parent_class_id, func_name) to processed_in_file

    # 3. Detect Deletions within this module (Compare DB entries for module_id vs processed_in_file)
    # TODO: Query DB for all functions/classes with this module_id
    # TODO: Find items in DB not in processed_in_file
    # TODO: Flag these potential deletions (don't delete yet)


def generate_map(db_path: Path, schema_path: Path, src_dir: Path):
    """Main function to generate or update the codebase map."""
    conn = connect_db(db_path)
    try:
        create_schema(conn, schema_path)
        python_files = find_python_files(src_dir)
        current_scan_timestamp = time.time()

        for file_path in python_files:
            process_file(file_path, conn, current_scan_timestamp)

        conn.commit()
        log.info("Codebase map generation/update complete.")

        # TODO: Implement the deletion confirmation and execution step here or separately
        # Needs a mechanism to know which deletions were confirmed

    except Exception as e:
        log.error(f"An error occurred during map generation: {e}")
        conn.rollback()
    finally:
        conn.close()
        log.info("Database connection closed.")


# --- MAIN EXECUTION --- (Allow running as script)
if __name__ == "__main__":
    log.info("Starting Codebase Map Generator Script")
    # TODO: Add command-line arguments (e.g., for db path, src dir)
    generate_map(DB_PATH, SCHEMA_PATH, SRC_DIR)
    log.info("Codebase Map Generator Script Finished")
