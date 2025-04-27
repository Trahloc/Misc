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

# --- CONSTANTS ---
# Remove old defaults, now handled by cli_utils or main block
# SRC_DIR_DEFAULT = Path("src")
# DB_PATH_DEFAULT = Path("tests/codebase_map/code_map.db")
# SCHEMA_PATH_DEFAULT = Path("tests/codebase_map/schema.sql")
PRUNE_CONFIRMATION_STRING = "Yes I have reviewed the content of the source files and determined these entries are stale"

# --- LOGGING SETUP (Explicit) ---
# Ensure logging is configured early and forcefully for the script itself
log = logging.getLogger("map_generator")  # Use a specific name?
# Remove the basicConfig call here if cli_utils handles it later in main?
# Or ensure this basicConfig uses force=True if kept.
# Let's try setting the level directly on the logger for now.
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# log = logging.getLogger(__name__)
# Attempt direct handler configuration:
handler = logging.StreamHandler(sys.stderr)  # Ensure output to stderr
formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s] %(message)s")
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.INFO)  # Default level, --verbose in main will set to DEBUG

# --- AST Visitor ---


class MapVisitor(ast.NodeVisitor):
    """Visits AST nodes to extract module, class, function, and import information."""

    def __init__(
        self,
        db: sqlite_utils.Database,
        module_path: str,
        module_id: int,
        current_scan_timestamp: float,
    ):
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

                # Positional-only args
                for arg in args_info.posonlyargs:
                    arg_str = arg.arg
                    if arg.annotation:
                        try:
                            arg_str += f":{ast.unparse(arg.annotation).strip()}"
                        except Exception:
                            arg_str += ":<unparse_error>"
                    args_repr.append(arg_str)
                if args_info.posonlyargs:
                    args_repr.append("/")  # Add positional-only marker if present

                # Regular args
                for arg in args_info.args:
                    arg_str = arg.arg
                    if arg.annotation:
                        try:
                            arg_str += f":{ast.unparse(arg.annotation).strip()}"
                        except Exception:
                            arg_str += ":<unparse_error>"
                    args_repr.append(arg_str)

                # Vararg (*args)
                if args_info.vararg:
                    arg_str = f"*{args_info.vararg.arg}"
                    if args_info.vararg.annotation:
                        try:
                            arg_str += f":{ast.unparse(args_info.vararg.annotation).strip()}"
                        except Exception:
                            arg_str += ":<unparse_error>"
                    args_repr.append(arg_str)
                    # Add keyword-only marker *if* vararg is present AND there are kwonlyargs
                    if args_info.kwonlyargs:
                        args_repr.append("*")
                elif args_info.kwonlyargs:  # Add keyword-only marker if no *args but kwonlyargs exist
                    args_repr.append("*")

                # Keyword-only args
                for arg in args_info.kwonlyargs:
                    arg_str = arg.arg
                    if arg.annotation:
                        try:
                            arg_str += f":{ast.unparse(arg.annotation).strip()}"
                        except Exception:
                            arg_str += ":<unparse_error>"
                    args_repr.append(arg_str)

                # Kwarg (**kwargs)
                if args_info.kwarg:
                    arg_str = f"**{args_info.kwarg.arg}"
                    if args_info.kwarg.annotation:
                        try:
                            arg_str += f":{ast.unparse(args_info.kwarg.annotation).strip()}"
                        except Exception:
                            arg_str += ":<unparse_error>"
                    args_repr.append(arg_str)

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

        table = self.db["classes"]

        # --- Explicit Check-then-Insert/Update Logic for Classes ---
        where_clause = "module_id = :module_id AND name = :name"
        params = {"module_id": self.module_id, "name": class_name}
        existing_rows = list(table.rows_where(where_clause, params))

        if existing_rows:
            # Update existing class
            existing_row = existing_rows[0]
            log.debug(f"  Updating existing class: {class_name} (ID: {existing_row['id']})")
            updates = {
                "signature_hash": signature_hash,
                "start_line": start_line,
                "end_line": end_line,
            }
            # Check if update is needed (e.g., hash changed)
            if (
                existing_row["signature_hash"] != signature_hash
                or existing_row["start_line"] != start_line
                or existing_row["end_line"] != end_line
            ):
                table.update(existing_row["id"], updates)
            self.current_class_id = existing_row["id"]  # Use existing ID
        else:
            # Insert new class
            log.debug(f"  Inserting new class: {class_name}")
            # Use column_order consistent with schema if needed, ensure pk='id' works for auto-inc
            inserted = table.insert(class_record, pk="id")
            self.current_class_id = inserted.last_pk  # Get new ID
        # --- End Explicit Logic ---

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
                log.error(
                    f"Unexpected error inserting function {func_name} in {self.module_path}: {e}",
                    exc_info=True,
                )
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


def process_file(
    file_path: Path,
    src_dir: Path,
    db: sqlite_utils.Database,
    current_scan_timestamp: float,
) -> set:
    """Parses a single Python file using AST and updates the database via the visitor."""
    # Use the provided src_dir to calculate the relative path
    relative_path = file_path.relative_to(src_dir).as_posix()
    log.debug(f"Processing file: {relative_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        err_type = type(e).__name__
        # Log a simpler message, including the error type name
        log.error(f"Error parsing {relative_path}. Type: {err_type}")
        # Log the full exception details at DEBUG level if needed
        log.debug(f"Full parsing error for {relative_path}", exc_info=True)
        return set()  # Skip this file, return empty set

    # 1. Upsert Module and get ID
    module_record = {
        "path": relative_path,
        "last_scanned_timestamp": current_scan_timestamp,
    }
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
    # Add the module itself to the set of processed items for auditing
    visitor.processed_in_scan.add(("module", relative_path, None, None))
    visitor.visit(tree)

    return visitor.processed_in_scan


def audit_database_against_scan(db: sqlite_utils.Database, processed_in_scan: set) -> list:
    """Compares DB state with the scan results to find potentially stale items (Audit Step).
    Returns a list of tuples representing stale items: e.g., ('module', id, path) or ('class', id, path, name)
    """
    log.info("Auditing database against current scan to find potentially stale entries...")
    stale_items = []
    stale_module_ids = set()
    stale_class_ids = set()

    # --- Check Modules --- Get all modules from DB first
    db_modules = {row["path"]: row["id"] for row in db["modules"].rows}
    processed_modules_paths = {item[1] for item in processed_in_scan if item[0] == "module"}
    stale_module_paths = set(db_modules.keys()) - processed_modules_paths

    if stale_module_paths:
        log.warning(f"Stale Module found in DB (Code likely removed/moved): {stale_module_paths}")
        for mpath in stale_module_paths:
            mid = db_modules[mpath]
            stale_module_ids.add(mid)
            stale_items.append(("module", mid, mpath))  # Store ID for deletion

    # --- Check Classes --- Query classes whose module is NOT stale
    non_stale_module_ids_tuple = tuple(set(db_modules.values()) - stale_module_ids)
    if not non_stale_module_ids_tuple:  # Handle case where ALL modules are stale or DB is empty
        log.debug("Skipping class audit: No non-stale modules found.")
        db_classes_tuples = {}
    else:
        db_classes_query = f"""
        SELECT c.id, m.path, c.name
        FROM classes c JOIN modules m ON c.module_id = m.id
        WHERE m.id IN ({",".join("?" * len(non_stale_module_ids_tuple))})
        """
        db_classes_tuples = {
            (row["path"], row["name"]): row["id"] for row in db.query(db_classes_query, non_stale_module_ids_tuple)
        }

    processed_classes_tuples = {(item[1], item[2]) for item in processed_in_scan if item[0] == "class"}
    stale_class_tuples = set(db_classes_tuples.keys()) - processed_classes_tuples

    if stale_class_tuples:
        log.warning(f"Stale Class found in DB (Code likely removed/moved): {stale_class_tuples}")
        for cpath, cname in stale_class_tuples:
            cid = db_classes_tuples[(cpath, cname)]
            stale_class_ids.add(cid)
            stale_items.append(("class", cid, cpath, cname))  # Store ID

    # --- Check Functions --- Query functions whose module AND class (if applicable) are NOT stale
    non_stale_class_ids_tuple = tuple(stale_class_ids)

    if not non_stale_module_ids_tuple:  # Handle case where ALL modules are stale or DB is empty
        log.debug("Skipping function audit: No non-stale modules found.")
        db_functions_tuples = {}
    else:
        # Start query, filtering by non-stale modules
        db_functions_query = f"""
        SELECT f.id, m.path, c.name as class_name, f.name
        FROM functions f
        JOIN modules m ON f.module_id = m.id
        LEFT JOIN classes c ON f.class_id = c.id
        WHERE m.id IN ({",".join("?" * len(non_stale_module_ids_tuple))})
        """
        params = list(non_stale_module_ids_tuple)

        # Add filter for non-stale classes (only if there ARE stale classes)
        if stale_class_ids:
            db_functions_query += f"""
            AND (f.class_id IS NULL OR f.class_id NOT IN ({",".join("?" * len(non_stale_class_ids_tuple))})
            """
            params.extend(non_stale_class_ids_tuple)

        db_functions_tuples = {
            (row["path"], row["class_name"], row["name"]): row["id"]
            for row in db.query(db_functions_query, tuple(params))
        }

    processed_functions_tuples = {(item[1], item[2], item[3]) for item in processed_in_scan if item[0] == "function"}
    stale_function_tuples = set(db_functions_tuples.keys()) - processed_functions_tuples

    if stale_function_tuples:
        log.warning(f"Stale Function found in DB (Code likely removed/moved): {stale_function_tuples}")
        for fpath, fcname, fname in stale_function_tuples:
            fid = db_functions_tuples[(fpath, fcname, fname)]
            # We don't need to add function IDs to a set for further checks
            stale_items.append(("function", fid, fpath, fcname, fname))  # Store ID

    # --- Final Summary --- (Modified log message slightly for clarity)
    if stale_items:
        # Count unique types of stale items found (ignoring IDs)
        unique_stale_elements = {tuple(item[2:]) for item in stale_items}  # Get unique (path, class, func) tuples
        log.warning(
            f'Audit complete. Found {len(stale_items)} potentially stale DB entries corresponding to {len(unique_stale_elements)} unique code elements. Verify these were intentionally removed/moved. Rerun with --prune-stale-entries "<confirmation_string>" to remove them.'
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
                db.conn.execute(
                    f"DELETE FROM functions WHERE id IN ({placeholders})",
                    stale_function_ids,
                )
                log.info(f"Pruned {len(stale_function_ids)} stale functions.")

            if stale_class_ids:
                placeholders = ", ".join("?" * len(stale_class_ids))
                # Note: Functions depending on these classes should already be caught or Cascade delete handles it if schema allows
                db.conn.execute(f"DELETE FROM classes WHERE id IN ({placeholders})", stale_class_ids)
                log.info(f"Pruned {len(stale_class_ids)} stale classes.")

            if stale_module_ids:
                placeholders = ", ".join("?" * len(stale_module_ids))
                # Note: Classes/Functions depending on these modules should already be caught or Cascade delete handles it
                db.conn.execute(
                    f"DELETE FROM modules WHERE id IN ({placeholders})",
                    stale_module_ids,
                )
                log.info(f"Pruned {len(stale_module_ids)} stale modules.")
        log.info("Pruning complete.")
    except Exception as e:
        log.error(f"Error during pruning: {e}", exc_info=True)
        # Transaction context manager handles rollback
        raise  # Re-raise the error


def generate_map(
    db_path: Path,
    schema_path: Path,
    src_dir: Path,
    prune_confirmation: str | None = None,
):
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
                # Pass src_dir to process_file
                processed_in_file = process_file(file_path, src_dir, db, current_scan_timestamp)
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
def main():
    parser = argparse.ArgumentParser(description="Generate or update the codebase map database.")
    # Define arguments directly using argparse
    parser.add_argument(
        "--db",
        type=Path,
        default="code_map.db",  # Simplified default path
        help="Path to the SQLite database file (default: code_map.db in CWD)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,  # Schema creation is now conditional
        help="Path to the schema.sql file (optional, used if db doesn't exist)",
    )
    parser.add_argument(
        "--src",
        type=Path,
        default="src",  # Default to relative src directory
        help="Path to the source directory to scan (default: ./src)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Prune stale entries from the database after scanning.",
    )
    parser.add_argument(
        "--confirm-prune",
        type=str,
        default=None,
        help=f"Required confirmation string to execute pruning: '{PRUNE_CONFIRMATION_STRING}'",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose DEBUG logging.")

    args = parser.parse_args()

    # Configure logging based on args
    log_level = logging.DEBUG if args.verbose else logging.INFO
    log.setLevel(log_level)
    # If using cli_utils configure_logging previously, ensure handlers are setup:
    if not log.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s] %(message)s")
        handler.setFormatter(formatter)
        log.addHandler(handler)
    log.info(f"Logging level set to: {logging.getLevelName(log_level)}")

    # Resolve paths relative to CWD (or use absolute paths if provided)
    db_path = args.db.resolve()
    src_path = args.src.resolve()
    schema_path = args.schema.resolve() if args.schema else None  # Resolve only if provided

    log.info(f"Using database: {db_path}")
    log.info(f"Scanning source: {src_path}")
    if schema_path:
        log.info(f"Using schema: {schema_path}")

    # --- Core Logic (using parsed args) ---
    try:
        # Ensure src directory exists
        if not src_path.is_dir():
            log.error(f"Source directory not found: {src_path}")
            sys.exit(1)

        # Auto-detect project root if needed (e.g., for relative path calculations within visitor?)
        # If generate_map handles paths correctly relative to src_path, this might not be needed here.
        # project_root = detect_project_root(src_path)
        # log.info(f"Detected project root: {project_root}")

        generate_map(
            db_path=db_path,
            schema_path=schema_path,  # Pass resolved schema path
            src_dir=src_path,  # Pass resolved src path
            prune_confirmation=args.confirm_prune if args.prune else None,
        )
        log.info("Codebase map generation complete.")
    except sqlite3.Error as e:
        log.exception("Database error during map generation:")
        sys.exit(1)
    except FileNotFoundError as e:
        log.error(f"File not found error: {e}")
        sys.exit(1)
    except Exception as e:
        log.exception("An unexpected error occurred:")
        sys.exit(1)


if __name__ == "__main__":
    main()


# <<< ZEROTH LAW FOOTER >>>

# This file makes src/zeroth_law a Python package
# (Comment added by ZLT)

# Additional Notes:
# - Consider adding more robust error handling.
# - Ensure schema handling is correct if DB doesn't exist.
# - Default paths might need adjustment based on typical usage.
