# FILE: tests/codebase_map/map_reporter.py
"""
# PURPOSE: Generates JSON reports summarizing the Codebase Map database.
"""

import sqlite3
import json
import argparse
from pathlib import Path
import structlog
from typing import List, Dict, Tuple, Set
import sys
import sqlite_utils
from tabulate import tabulate

# --- CONSTANTS ---
DB_PATH_DEFAULT = Path("tests/codebase_map/code_map.db")
OUTPUT_PATH_DEFAULT = Path("tests/codebase_map/code_map_report.json")

# --- LOGGING ---
log = structlog.get_logger()

# --- Query Functions ---


def generate_project_overview(db: sqlite_utils.Database) -> dict:
    """Generates high-level counts of project elements."""
    log.info("Generating project overview...")
    overview = {}
    try:
        overview["module_count"] = db["modules"].count
        overview["class_count"] = db["classes"].count
        overview["function_count"] = db["functions"].count
        overview["import_count"] = db["imports"].count
    except BaseException as e:
        log.error(f"Error querying counts: {e}")
        # Return partial data or raise?
        overview["error"] = f"Error querying counts: {e}"
    return {"overview": overview}


def generate_module_details(db: sqlite_utils.Database) -> dict:
    """Generates detailed information for each module, including classes, functions, and imports."""
    log.info("Generating detailed module information...")
    modules_data = {}
    try:
        # Fetch all modules first
        modules = {
            row["id"]: {
                "path": row["path"],
                "last_scanned_timestamp": row["last_scanned_timestamp"],
                "classes": [],
                "functions": [],
                "imports": [],
            }
            for row in db["modules"].rows
        }

        # Fetch classes and group by module_id
        for row in db["classes"].rows:
            if row["module_id"] in modules:
                modules[row["module_id"]]["classes"].append(
                    {
                        "name": row["name"],
                        "signature_hash": row["signature_hash"],
                        "start_line": row["start_line"],
                        "end_line": row["end_line"],
                    }
                )

        # Fetch functions and group by module_id
        for row in db["functions"].rows:
            if row["module_id"] in modules:
                modules[row["module_id"]]["functions"].append(
                    {
                        "name": row["name"],
                        "class_id": row["class_id"],  # Keep for context, could resolve to class name later
                        "signature_hash": row["signature_hash"],
                        "start_line": row["start_line"],
                        "end_line": row["end_line"],
                    }
                )

        # Fetch imports and group by module_id
        for row in db["imports"].rows:
            if row["importing_module_id"] in modules:
                modules[row["importing_module_id"]]["imports"].append(
                    {
                        "imported_name": row["imported_name"],
                        "alias": row["alias"],
                        "line_number": row["line_number"],
                    }
                )

        # Convert dict keyed by id to list of module dicts for final output
        # Sort modules by path for consistent output
        modules_data = sorted(modules.values(), key=lambda x: x["path"])

    except BaseException as e:
        log.error(f"Error querying details: {e}")
        return {"error": f"Error querying details: {e}", "modules": list(modules_data)}

    return {"modules": modules_data}


def generate_report(db_path: Path, output_path: Path):
    """Connects to the DB, generates reports, and writes to JSON file."""
    log.info(f"Connecting to database: {db_path}")
    if not db_path.exists():
        log.error(f"Database file not found: {db_path}")
        sys.exit(1)

    db = sqlite_utils.Database(str(db_path))
    combined_report = {}

    try:
        combined_report.update(generate_project_overview(db))
        combined_report.update(generate_module_details(db))
        # Add more report sections here in the future

        log.info(f"Writing combined report to: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(combined_report, f, indent=4)
        log.info("Report generation complete.")

    except Exception as e:
        log.error(f"An error occurred during report generation: {e}", exc_info=True)
    finally:
        if db and db.conn:
            db.conn.close()
            log.info("Database connection closed.")


# --- MAIN EXECUTION --- (Allow running as script)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate JSON reports from the ZLF Codebase Map SQLite database.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Common DB and Logging Arguments
    # Reporter doesn't need schema arg, only DB
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH_DEFAULT,  # Use default from this file for now
        help=f"Database path (default: {DB_PATH_DEFAULT})",
    )
    add_common_logging_arguments(parser)

    # Reporter Specific Arguments
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH_DEFAULT,  # Use default from this file
        help=f"Output JSON file path (default: {OUTPUT_PATH_DEFAULT})",
    )

    # Parse Arguments
    args = parser.parse_args()

    # Configure Logging based on args
    configure_logging(args)

    log.info("Starting Codebase Map Reporter Script")
    log.debug(f"Raw Args: {args}")

    # Resolve and Validate Paths
    try:
        # Only resolve db and output for reporter
        if not args.db.exists():
            log.critical(f"Database file not found: {args.db.resolve()}")
            sys.exit(1)
        args = resolve_paths(args)  # Resolves db, output if present
    except (FileNotFoundError, NotADirectoryError) as e:
        log.critical(f"Path validation failed: {e}")
        sys.exit(1)

    # Call the main report generation function
    generate_report(args.db, args.output)
    log.info("Codebase Map Reporter Script Finished")
