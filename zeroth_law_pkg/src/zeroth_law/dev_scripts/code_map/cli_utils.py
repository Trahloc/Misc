"""Command-line argument parsing utilities for codebase map scripts."""

import argparse
from pathlib import Path
import logging

log = logging.getLogger(__name__)


# Common default paths - resolve based on a detected project root
def detect_project_root() -> Path:
    """Attempt to detect the project root by looking for pyproject.toml."""
    cwd = Path.cwd()
    project_root = cwd
    for parent in [cwd] + list(cwd.parents):
        if (parent / "pyproject.toml").is_file() and (parent / "src").is_dir():
            project_root = parent
            log.debug(f"Detected project root: {project_root}")
            break
    else:
        log.warning(f"Could not detect project root via pyproject.toml, using CWD: {project_root}")
    return project_root


PROJECT_ROOT_DEFAULT = detect_project_root()
DB_PATH_DEFAULT = PROJECT_ROOT_DEFAULT / "tests" / "codebase_map" / "code_map.db"
SCHEMA_PATH_DEFAULT = PROJECT_ROOT_DEFAULT / "tests" / "codebase_map" / "schema.sql"


def add_common_db_arguments(parser: argparse.ArgumentParser):
    """Adds common database and schema path arguments to an ArgumentParser."""
    parser.add_argument("--db", type=Path, default=DB_PATH_DEFAULT, help=f"Database path (default: {DB_PATH_DEFAULT})")
    parser.add_argument(
        "--schema", type=Path, default=SCHEMA_PATH_DEFAULT, help=f"Schema path (default: {SCHEMA_PATH_DEFAULT})"
    )


def add_common_logging_arguments(parser: argparse.ArgumentParser):
    """Adds common logging arguments (--verbose, --debug-sql)."""
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging for the script.")
    parser.add_argument(
        "--debug-sql", action="store_true", help="Enable SQL query logging from sqlite-utils (implies verbose)."
    )


def configure_logging(args: argparse.Namespace):
    """Configures logging based on parsed arguments."""
    log_level = logging.DEBUG if args.verbose or args.debug_sql else logging.INFO
    # Use force=True to ensure configuration overrides any defaults
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s", force=True)
    # Control sqlite-utils verbosity separately
    logging.getLogger("sqlite_utils").setLevel(logging.DEBUG if args.debug_sql else logging.WARNING)

    log.info("Logging configured.")
    if log_level == logging.DEBUG:
        log.debug("Verbose logging enabled.")
    if args.debug_sql:
        log.debug("SQL query logging enabled.")


def resolve_paths(args: argparse.Namespace) -> argparse.Namespace:
    """Resolves common Path arguments to absolute paths and validates."""
    if hasattr(args, "db"):
        args.db = args.db.resolve()
        args.db.parent.mkdir(parents=True, exist_ok=True)  # Ensure DB directory exists
        log.info(f"Using Database Path: {args.db}")
    if hasattr(args, "schema"):
        args.schema = args.schema.resolve()
        if not args.schema.is_file():
            log.critical(f"Schema file does not exist: {args.schema}")
            raise FileNotFoundError(f"Schema file not found: {args.schema}")
        log.info(f"Using Schema Path: {args.schema}")
    if hasattr(args, "src"):
        args.src = args.src.resolve()
        if not args.src.is_dir():
            log.critical(f"Source directory does not exist: {args.src}")
            raise NotADirectoryError(f"Source directory not found: {args.src}")
        log.info(f"Using Source Directory: {args.src}")
    if hasattr(args, "output"):  # For reporter
        args.output = args.output.resolve()
        args.output.parent.mkdir(parents=True, exist_ok=True)  # Ensure output dir exists
        log.info(f"Using Output Path: {args.output}")

    return args
