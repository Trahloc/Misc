# FILE: tests/codebase_map/map_generator.py
"""
# PURPOSE: Generates/updates the SQLite codebase map (`code_map.db`).
#          Uses AST to scan source files and populates the database using sqlite-utils.
"""

# --- IMPORTS ---
import ast
import sqlite3
import time
import hashlib
from pathlib import Path
import logging
import sys
import argparse
import sqlite_utils  # Added dependency

# --- Imports for Refactoring ---
from tests.codebase_map.cli_utils import (
    add_common_db_arguments,
    add_common_logging_arguments,
    configure_logging,
    resolve_paths,
    detect_project_root,  # Import the root detection function
)
# --- End Imports for Refactoring ---

# --- CONSTANTS ---
# Remove old defaults, now handled by cli_utils or main block
# SRC_DIR_DEFAULT = Path("src")
# DB_PATH_DEFAULT = Path("tests/codebase_map/code_map.db")
# SCHEMA_PATH_DEFAULT = Path("tests/codebase_map/schema.sql")
PRUNE_CONFIRMATION_STRING = "Yes I have reviewed the content of the source files and determined these entries are stale"

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# --- AST Visitor ---


class MapVisitor(ast.NodeVisitor):
    """Visits AST nodes to extract module, class, function, and import information."""

    def __init__(self, db: sqlite_utils.Database, module_path: str, module_id: int, current_scan_timestamp: float):
        self.db = db
        self.module_path = module_path
        self.module_id = module_id
        self.current_scan_timestamp = current_scan_timestamp
        self.current_class_id = None
        self.current_class_name = None
        # Track items found in this specific scan pass: (type, path, class_name, func_name)
        self.processed_in_scan = set()
        # Visitor adds module to processed set, not init
        # self.processed_in_scan.add(("module", module_path, None, None))

    def _calculate_signature_hash(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> str:
        """Calculates a SHA256 hash representing the structural signature (excluding body/comments/docstrings)."""
        signature_parts = []

        try:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Function/Method Signature
                if isinstance(node, ast.AsyncFunctionDef):
                    signature_parts.append("async")
                signature_parts.append("def")
                signature_parts.append(node.name)

                # Arguments (simplified representation: name:annotation)
                args_repr = []
                args_info = node.args
                # Combine all arg types for consistent processing
                all_args = args_info.posonlyargs + args_info.args + args_info.kwonlyargs
                for arg in all_args:
                    arg_str = arg.arg
                    if arg.annotation:
                        try:
                            arg_str += f":{ast.unparse(arg.annotation).strip()}"
                        except Exception:
                            arg_str += ":<unparse_error>"  # Handle annotation unparsing error
                    args_repr.append(arg_str)
                if args_info.vararg:
                    arg_str = f"*{args_info.vararg.arg}"
                    if args_info.vararg.annotation:
                        try:
                            arg_str += f":{ast.unparse(args_info.vararg.annotation).strip()}"
                        except Exception:
                            arg_str += ":<unparse_error>"
                    args_repr.append(arg_str)  # Corrected indentation
                if args_info.kwarg:
                    arg_str = f"**{args_info.kwarg.arg}"
                    if args_info.kwarg.annotation:
                        try:
                            arg_str += f":{ast.unparse(args_info.kwarg.annotation).strip()}"
                        except Exception:
                            arg_str += ":<unparse_error>"
                    args_repr.append(arg_str)  # Corrected indentation

                signature_parts.append(f"({','.join(args_repr)})")  # Join args

                # Return Type
                if node.returns:
                    try:
                        signature_parts.append(f"->{ast.unparse(node.returns).strip()}")
                    except Exception:
                        signature_parts.append("-><unparse_error>")

                # Decorators (sorted)
                decorator_reprs = []
                for d in node.decorator_list:
                    try:
                        decorator_reprs.append(f"@{ast.unparse(d).strip()}")
                    except Exception:
                        decorator_reprs.append("@<unparse_error>")
                signature_parts.extend(sorted(decorator_reprs))

            elif isinstance(node, ast.ClassDef):
                # Class Signature
                signature_parts.append("class")
                signature_parts.append(node.name)

                # Bases and Keywords (sorted together for consistency)
                parent_reprs = []
                for b in node.bases:
                    try:
                        parent_reprs.append(ast.unparse(b).strip())
                    except Exception:
                        parent_reprs.append("<unparse_error_base>")
                for k in node.keywords:
                    kw_val_str = "<unparse_error_kw_val>"
                    try:
                        kw_val_str = ast.unparse(k.value).strip()
                    except Exception:
                        pass
                    parent_reprs.append(f"{k.arg}={kw_val_str}")  # k.arg should exist
                if parent_reprs:
                    signature_parts.append(f"({','.join(sorted(parent_reprs))})")

                # Decorators (sorted)
                decorator_reprs = []
                for d in node.decorator_list:
                    try:
                        decorator_reprs.append(f"@{ast.unparse(d).strip()}")
                    except Exception:
                        decorator_reprs.append("@<unparse_error>")
                signature_parts.extend(sorted(decorator_reprs))

        except Exception as e:
            log.error(
                f"Error building signature for node {getattr(node, 'name', 'UNKNOWN')} in {self.module_path}: {e}",
                exc_info=True,
            )
            # Fallback to simple hash if detailed parsing fails?
            # For now, just return a hash of the error message or a fixed value
            return hashlib.sha256(f"error: {e}".encode()).hexdigest()

        # Join all parts with a delimiter and hash
        canonical_string = "|".join(signature_parts)
        log.debug(f"  Node: {getattr(node, 'name', 'N/A')}, Canonical Signature String: {canonical_string}")
        return hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()

    def visit_ClassDef(self, node: ast.ClassDef):
        """Process Class Definitions."""
        class_name = node.name
        signature_hash = self._calculate_signature_hash(node)
        start_line = node.lineno
        end_line = node.end_lineno
        log.debug(f"  Found Class: {class_name} (Lines {start_line}-{end_line}) in {self.module_path}")

        class_record = {
            "module_id": self.module_id,
            "name": class_name,
            "signature_hash": signature_hash,
            "start_line": start_line,
            "end_line": end_line,
        }

        # Upsert class and get its ID
        table = self.db["classes"]
        result = table.upsert(
            class_record,
            pk=("id"),
            # Match existing record based on unique constraint
            # Use alter=True in case we add columns later, though not strictly needed now
            alter=True,
            column_order=["id", "module_id", "name", "signature_hash", "start_line", "end_line"],
        )
        self.current_class_id = result.last_pk
        self.current_class_name = class_name
        self.processed_in_scan.add(("class", self.module_path, class_name, None))

        # Visit child nodes (methods, nested classes)
        self.generic_visit(node)

        # Reset class context after visiting children
        self.current_class_id = None
        self.current_class_name = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Process Function Definitions."""
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Process Async Function Definitions."""
        self._process_function(node)

    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Common logic for processing sync and async functions."""
        func_name = node.name
        signature_hash = self._calculate_signature_hash(node)
        start_line = node.lineno
        end_line = node.end_lineno

        log.debug(
            f"  Found Function: {func_name} (Lines {start_line}-{end_line}, Class: {self.current_class_name}) in {self.module_path}"
        )

        func_record = {
            "module_id": self.module_id,
            "class_id": self.current_class_id,  # Will be None for module-level functions
            "name": func_name,
            "signature_hash": signature_hash,
            "start_line": start_line,
            "end_line": end_line,
        }

        table = self.db["functions"]

        # --- Explicit Check-then-Insert/Update Logic for Functions ---
        where_clause = "module_id = :module_id AND name = :name"
        params = {"module_id": self.module_id, "name": func_name}
        if self.current_class_id is None:
            where_clause += " AND class_id IS NULL"
        else:
            where_clause += " AND class_id = :class_id"
            params["class_id"] = self.current_class_id

        existing_rows = list(table.rows_where(where_clause, params))

        if existing_rows:
            # Update existing function (assuming only one match due to UNIQUE constraint)
            existing_row = existing_rows[0]
            log.debug(f"  Updating existing function: {func_name} (ID: {existing_row['id']})")
            updates = {
                "signature_hash": signature_hash,
                "start_line": start_line,
                "end_line": end_line,
            }
            # Only update if hash changed
            if existing_row["signature_hash"] != signature_hash:
                table.update(existing_row["id"], updates)
        else:
            # Insert new function
            log.debug(f"  Inserting new function: {func_name}")
            try:
                # Ensure func_record has necessary keys (module_id, class_id, name, etc.)
                # ID is handled by pk='id' on insert
                table.insert(func_record, pk="id")
            except sqlite3.IntegrityError as e:
                log.error(
                    f"IntegrityError inserting function {func_name} (Class: {self.current_class_name}) in {self.module_path} (Module ID: {self.module_id}, Class ID: {self.current_class_id}): {e}",
                    exc_info=True,
                )
            except Exception as e:
                log.error(f"Unexpected error inserting function {func_name} in {self.module_path}: {e}", exc_info=True)
        # --- End Explicit Logic ---

        self.processed_in_scan.add(("function", self.module_path, self.current_class_name, func_name))

        # Visit child nodes (nested functions/classes, although less common)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """Process regular import statements (e.g., import os, import pandas as pd)."""
        line_number = node.lineno
        for alias in node.names:
            imported_name = alias.name
            alias_name = alias.asname
            log.debug(f"  Found Import: {imported_name} as {alias_name} (Line {line_number}) in {self.module_path}")
            import_record = {
                "importing_module_id": self.module_id,
                "imported_name": imported_name,
                "alias": alias_name,
                "line_number": line_number,
            }
            # Use insert() instead of upsert() as we want to record each occurrence
            self.db["imports"].insert(import_record, pk="id")
            # Note: We don't add imports to processed_in_scan as they aren't structural elements we prune
        self.generic_visit(node)  # Continue visit in case of nested imports (unlikely)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Process 'from ... import ...' statements (e.g., from pathlib import Path).
        Handles relative imports partially by storing the leading dots.
        """
        line_number = node.lineno
        module_name = node.module if node.module else ""  # Relative imports might have None
        # Add leading dots for relative imports
        relative_prefix = "." * node.level
        base_import_path = f"{relative_prefix}{module_name}"

        for alias in node.names:
            imported_symbol = alias.name
            alias_name = alias.asname

            # Construct the full imported name (e.g., pathlib.Path or .utils.helper_func)
            # For 'from . import foo', module_name is None, symbol is foo -> .foo
            # For 'from .module import bar', module_name is module, symbol is bar -> .module.bar
            full_imported_name = (
                f"{base_import_path}.{imported_symbol}" if module_name else f"{relative_prefix}{imported_symbol}"
            )
            # Handle 'from module import *' -> stores 'module.*'
            if imported_symbol == "*":
                full_imported_name = f"{base_import_path}.*"

            log.debug(
                f"  Found From Import: {full_imported_name} as {alias_name} (Line {line_number}) in {self.module_path}"
            )
            import_record = {
                "importing_module_id": self.module_id,
                "imported_name": full_imported_name,
                "alias": alias_name,
                "line_number": line_number,
            }
            self.db["imports"].insert(import_record, pk="id")
        self.generic_visit(node)


# --- CORE FUNCTIONS ---


def connect_db(db_path: Path) -> sqlite_utils.Database:
    """Connects to the SQLite database using sqlite-utils."""
    log.info(f"Connecting to database: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite_utils.Database(str(db_path))  # sqlite-utils expects string path
    # Ensure foreign keys are enabled for the connection used by sqlite-utils
    db.conn.execute("PRAGMA foreign_keys = ON;")
    return db


def create_schema(db: sqlite_utils.Database, schema_path: Path):
    """Creates the database schema from the .sql file if tables don't exist."""
    log.info(f"Checking/creating schema from: {schema_path}")
    existing_tables = db.table_names()
    if "modules" in existing_tables and "classes" in existing_tables and "functions" in existing_tables:
        log.info("Schema tables already exist.")
        return

    log.info("Schema not found or incomplete. Creating/recreating tables...")
    try:
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        db.conn.executescript(schema_sql)  # Use underlying connection for executescript
        db.conn.commit()
        log.info("Schema created successfully.")
    except Exception as e:
        log.error(f"Error creating schema: {e}")
        db.conn.rollback()
        raise


def find_python_files(src_dir: Path) -> list[Path]:
    """Finds all .py files within the source directory."""
    log.info(f"Scanning for Python files in: {src_dir}")
    python_files = list(src_dir.rglob("*.py"))
    log.info(f"Found {len(python_files)} Python files.")
    return python_files


def process_file(file_path: Path, db: sqlite_utils.Database, current_scan_timestamp: float) -> set:
    """Parses a single Python file using AST and updates the database via the visitor."""
    relative_path = file_path.relative_to(SRC_DIR_DEFAULT).as_posix()  # Assume SRC_DIR_DEFAULT for relative path calc
    log.debug(f"Processing file: {relative_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        log.error(f"Error parsing {relative_path}: {e}")
        return set()  # Skip this file, return empty set

    # 1. Upsert Module and get ID
    module_record = {"path": relative_path, "last_scanned_timestamp": current_scan_timestamp}
    modules_table = db["modules"]

    try:
        # --- Explicit Check-then-Insert/Update for Modules ---
        existing_rows = list(modules_table.rows_where("path = ?", [relative_path]))

        if existing_rows:
            # Update existing module timestamp
            module_id = existing_rows[0]["id"]
            log.debug(f"  Updating existing module: {relative_path} (ID: {module_id})")
            modules_table.update(module_id, {"last_scanned_timestamp": current_scan_timestamp})
        else:
            # Insert new module
            log.debug(f"  Inserting new module: {relative_path}")
            inserted = modules_table.insert(module_record, pk="id")
            module_id = inserted.last_pk
        # --- End Explicit Logic ---

        log.debug(f"  Module {relative_path} processed/found with ID: {module_id}")

    except Exception as e:
        log.error(f"Error processing module: {relative_path} - {e}")
        return set()  # Skip this file, return empty set

    # 2. Visit nodes to populate classes and functions
    visitor = MapVisitor(db, relative_path, module_id, current_scan_timestamp)
    visitor.visit(tree)

    return visitor.processed_in_scan


def audit_database_against_scan(db: sqlite_utils.Database, processed_in_scan: set) -> list:
    """Compares DB state with the scan results to find potentially stale items (Audit Step).
    Returns a list of tuples representing stale items: e.g., ('module', path) or ('class', path, name)
    """
    log.info("Auditing database against current scan to find potentially stale entries...")
    stale_items = []

    # Check modules
    db_modules = {(row["id"], row["path"]) for row in db["modules"].rows}
    processed_modules_paths = {item[1] for item in processed_in_scan if item[0] == "module"}
    stale_modules = {(mid, mpath) for mid, mpath in db_modules if mpath not in processed_modules_paths}
    if stale_modules:
        stale_module_paths = {mpath for _, mpath in stale_modules}
        log.warning(f"Stale Module found in DB (Code likely removed/moved): {stale_module_paths}")
        stale_items.extend([("module", mid, mpath) for mid, mpath in stale_modules])  # Store ID for deletion

    # Check classes
    db_classes_query = """
    SELECT c.id, m.path, c.name
    FROM classes c JOIN modules m ON c.module_id = m.id
    """
    db_classes = {(row["id"], row["path"], row["name"]) for row in db.query(db_classes_query)}
    processed_classes = {(item[1], item[2]) for item in processed_in_scan if item[0] == "class"}
    stale_classes = {
        (cid, cpath, cname)
        for cid, cpath, cname in db_classes
        if (cpath, cname) not in processed_classes and cpath not in stale_module_paths
    }
    if stale_classes:
        stale_class_tuples = {(cpath, cname) for _, cpath, cname in stale_classes}
        log.warning(f"Stale Class found in DB (Code likely removed/moved): {stale_class_tuples}")
        stale_items.extend([("class", cid, cpath, cname) for cid, cpath, cname in stale_classes])  # Store ID

    # Check functions
    db_functions_query = """
    SELECT f.id, m.path, c.name as class_name, f.name
    FROM functions f
    JOIN modules m ON f.module_id = m.id
    LEFT JOIN classes c ON f.class_id = c.id
    """
    db_functions = {(row["id"], row["path"], row["class_name"], row["name"]) for row in db.query(db_functions_query)}
    processed_functions = {(item[1], item[2], item[3]) for item in processed_in_scan if item[0] == "function"}
    # Exclude functions whose module or class is already marked stale
    stale_class_ids = {cid for type, cid, *_ in stale_items if type == "class"}
    stale_functions = {
        (fid, fpath, fcname, fname)
        for fid, fpath, fcname, fname in db_functions
        if (fpath, fcname, fname) not in processed_functions
        and fpath not in stale_module_paths
        and not (
            fcname
            and any(
                c[1] == fid
                for c in db.query(f"SELECT class_id from functions where id={fid}")
                if c["class_id"] in stale_class_ids
            )
        )  # Check if function's class_id is stale
    }

    if stale_functions:
        stale_func_tuples = {(fpath, fcname, fname) for _, fpath, fcname, fname in stale_functions}
        log.warning(f"Stale Function found in DB (Code likely removed/moved): {stale_func_tuples}")
        stale_items.extend(
            [("function", fid, fpath, fcname, fname) for fid, fpath, fcname, fname in stale_functions]
        )  # Store ID

    if stale_items:
        log.warning(
            f'Audit complete. Found {len(stale_items)} stale entries. Verify these code elements were intentionally removed or moved. If confirmed, rerun with --prune-stale-entries "{PRUNE_CONFIRMATION_STRING}" to remove them from the database map.'
        )
    else:
        log.info("Audit complete. No stale entries found in database.")
    return stale_items  # Return list of stale items with IDs


def prune_stale_entries(db: sqlite_utils.Database, stale_items: list):
    """Executes DELETE statements for confirmed stale items."""
    if not stale_items:
        return

    log.info(f"Pruning {len(stale_items)} confirmed stale entries...")
    stale_function_ids = [item[1] for item in stale_items if item[0] == "function"]
    stale_class_ids = [item[1] for item in stale_items if item[0] == "class"]
    stale_module_ids = [item[1] for item in stale_items if item[0] == "module"]

    try:
        with db.conn:
            # Delete in reverse order of dependency (functions, classes, modules)
            if stale_function_ids:
                # Use parameter substitution to avoid SQL injection vulnerabilities
                placeholders = ", ".join("?" * len(stale_function_ids))
                db.conn.execute(f"DELETE FROM functions WHERE id IN ({placeholders})", stale_function_ids)
                log.info(f"Pruned {len(stale_function_ids)} stale functions.")

            if stale_class_ids:
                placeholders = ", ".join("?" * len(stale_class_ids))
                # Note: Functions depending on these classes should already be caught or Cascade delete handles it if schema allows
                db.conn.execute(f"DELETE FROM classes WHERE id IN ({placeholders})", stale_class_ids)
                log.info(f"Pruned {len(stale_class_ids)} stale classes.")

            if stale_module_ids:
                placeholders = ", ".join("?" * len(stale_module_ids))
                # Note: Classes/Functions depending on these modules should already be caught or Cascade delete handles it
                db.conn.execute(f"DELETE FROM modules WHERE id IN ({placeholders})", stale_module_ids)
                log.info(f"Pruned {len(stale_module_ids)} stale modules.")
        log.info("Pruning complete.")
    except Exception as e:
        log.error(f"Error during pruning: {e}", exc_info=True)
        # Transaction context manager handles rollback
        raise  # Re-raise the error


def generate_map(db_path: Path, schema_path: Path, src_dir: Path, prune_confirmation: str | None = None):
    """Main function to generate or update the codebase map."""
    db = connect_db(db_path)
    prune_confirmed = False
    if prune_confirmation:
        if prune_confirmation == PRUNE_CONFIRMATION_STRING:
            prune_confirmed = True
            log.info("Pruning confirmation string matched.")
        else:
            log.error(
                f"Pruning confirmation string MISMATCHED. Expected: '{PRUNE_CONFIRMATION_STRING}'. Received: '{prune_confirmation}'. Pruning WILL NOT occur."
            )

    try:
        create_schema(db, schema_path)
        python_files = find_python_files(src_dir)
        current_scan_timestamp = time.time()
        all_processed_in_scan = set()

        # --- Population Phase ---
        log.info("Starting database population phase...")
        # Use transaction for bulk upserts
        # Using db.conn context manager for transaction
        with db.conn:
            for file_path in python_files:
                processed_in_file = process_file(file_path, db, current_scan_timestamp)
                all_processed_in_scan.update(processed_in_file)
        log.info("Database population complete.")

        # --- Audit Phase ---
        stale_items = audit_database_against_scan(db, all_processed_in_scan)

        # --- Pruning Phase (Conditional) ---
        if prune_confirmed:
            if stale_items:
                prune_stale_entries(db, stale_items)
            else:
                log.info("Pruning requested and confirmed, but no stale entries were found.")
        elif stale_items:
            log.warning(
                'Stale entries detected but pruning was not requested or confirmed. Run with --prune-stale-entries "<confirmation_string>" to remove them after verification.'
            )
        # If not prune_confirmed and prune_confirmation was provided but wrong:
        elif prune_confirmation:
            log.warning("Pruning skipped due to confirmation string mismatch.")

    except Exception as e:
        log.error(f"An error occurred during map generation: {e}", exc_info=True)
        # Rollback is handled by the transaction context manager or explicit call if outside
    finally:
        if db and db.conn:
            db.conn.close()
            log.info("Database connection closed.")


# --- MAIN EXECUTION --- (Allow running as script)
if __name__ == "__main__":
    # Define defaults here before parser uses them
    # These might need adjustment based on where the script is expected to be run from
    # Assuming script might be run from project root or tests/codebase_map
    _default_src_dir = Path("src")
    _default_db_path = Path("tests/codebase_map/code_map.db")
    _default_schema_path = Path("tests/codebase_map/schema.sql")

    parser = argparse.ArgumentParser(
        description="Generate/Update the ZLF Codebase Map SQLite database.",
    )
    parser.add_argument(
        "--src", type=Path, default=_default_src_dir, help=f"Source directory to scan (default: {_default_src_dir})"
    )
    parser.add_argument(
        "--db", type=Path, default=_default_db_path, help=f"Database file path (default: {_default_db_path})"
    )
    parser.add_argument(
        "--schema", type=Path, default=_default_schema_path, help=f"Schema file path (default: {_default_schema_path})"
    )
    parser.add_argument(
        "--prune-stale-entries",
        type=str,
        default=None,
        help=f"REQUIRED confirmation string to delete stale entries: '{PRUNE_CONFIRMATION_STRING}'",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)  # Set root logger level too
        log.debug("Verbose logging enabled.")

    log.info("Starting Codebase Map Generator Script")
    # IMPORTANT: The global SRC_DIR_DEFAULT used in process_file needs the runtime value
    # We should ideally pass args.src down instead of relying on a global.
    # For now, update the global, but this is a refactoring target.
    SRC_DIR_DEFAULT = args.src
    generate_map(args.db, args.schema, args.src, prune_confirmation=args.prune_stale_entries)
    log.info("Codebase Map Generator Script Finished")
