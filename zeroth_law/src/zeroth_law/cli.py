# FILE: src/zeroth_law/cli.py
"""Command-line interface for the Zeroth Law audit tool."""

import argparse
import importlib.metadata
import logging  # Import logging
import sys
from pathlib import Path
from typing import Any

# Import config loader first, it should always be importable relative to cli.py
from .config_loader import load_config

# Ensure src is discoverable for imports when run directly
# This might not be strictly necessary when installed, but helps during development
try:
    from .analyzer.python.analyzer import analyze_file_compliance  # type: ignore[attr-defined]
    from .file_finder import find_python_files
except ImportError:
    # If run as script/module directly, adjust path
    project_root = Path(__file__).resolve().parent.parent.parent
    # Only add to path if not already there to avoid duplicates
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    # Re-import using the adjusted path if relative fails
    try:
        # Re-import using the adjusted path
        from src.zeroth_law.analyzer.python.analyzer import analyze_file_compliance
        from src.zeroth_law.config_loader import load_config
        from src.zeroth_law.file_finder import find_python_files
    except ImportError as e:
        print(f"Failed to import necessary modules even after path adjustment: {e}", file=sys.stderr)
        sys.exit(3)  # Exit code indicating import failure

# Setup basic logging config - will be adjusted by CLI args
# Log to stderr by default
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
log = logging.getLogger("zeroth_law")  # Get a logger instance


def run_audit(start_dir: Path, config: dict[str, Any]) -> tuple[dict[Path, dict[str, list[str]]], bool]:
    """Run the audit and log results using the loaded configuration."""
    log.info("Starting audit in: %s", start_dir)
    try:
        exclude_dirs_cfg = config.get("exclude_dirs", [])
        exclude_files_cfg = config.get("exclude_files", [])

        python_files = find_python_files(start_dir, exclude_dirs=set(exclude_dirs_cfg), exclude_patterns=set(exclude_files_cfg))
    except FileNotFoundError as e:
        log.exception("Audit failed: %s", e)
        return {}, True

    log.info("Found %d Python files to analyze.", len(python_files))
    log.info("Using configuration: %s", config)

    all_results: dict[Path, dict[str, list[str]]] = {}
    files_with_violations = 0

    for file_path in python_files:
        relative_path = file_path.relative_to(start_dir)
        log.debug("Analyzing: %s", relative_path)
        try:
            violations = analyze_file_compliance(
                file_path,
                max_complexity=config.get("max_complexity", 10),
                max_lines=config.get("max_lines", 100),
            )
            if violations:
                all_results[relative_path] = violations
                files_with_violations += 1
                log.warning(" -> Violations found in %s: %s", relative_path, list(violations.keys()))
            else:
                all_results[relative_path] = {}
        except Exception as e:
            log.exception(" -> ERROR analyzing file %s: %s", relative_path, e)
            all_results[relative_path] = {"analysis_error": [str(e)]}
            files_with_violations += 1

    log.warning("-" * 40)
    log.warning("Audit Summary:")
    log.info(" Total files analyzed: %d", len(python_files))
    log.warning(" Files with violations: %d", files_with_violations)
    log.info(" Compliant files: %d", len(python_files) - files_with_violations)
    log.warning("-" * 40)

    violations_found = files_with_violations > 0
    return all_results, violations_found


def main() -> None:
    """Run the main CLI entry point."""
    parser = argparse.ArgumentParser(description="Zeroth Law Compliance Auditor.")

    parser.add_argument(
        "directory",
        nargs="?",  # Optional positional argument
        default=Path.cwd(),  # Default to current directory
        help="Directory to audit (default: current directory)",
        type=Path,
    )
    # --- Verbosity Arguments ---
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        dest="verbosity",
        const=logging.WARNING,
        help="Suppress informational messages, show only warnings and errors.",
    )
    verbosity_group.add_argument(
        "-v", "--verbose", action="store_const", dest="verbosity", const=logging.INFO, help="Show informational messages (default)."
    )
    verbosity_group.add_argument("-vv", action="store_const", dest="verbosity", const=logging.DEBUG, help="Show detailed debug messages.")
    # --- End Verbosity ---
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {importlib.metadata.version('zeroth_law')}",
        help="Show program's version number and exit.",
    )

    args = parser.parse_args()

    log_level = args.verbosity or logging.INFO
    log.setLevel(log_level)

    audit_dir = args.directory.resolve()

    try:
        config = load_config()
    except FileNotFoundError as e:
        log.error("Configuration error: %s", e)
        sys.exit(2)
    except ImportError as e:
        log.error("Configuration error: %s", e)
        sys.exit(2)
    except Exception as e:
        log.exception("Unexpected error loading configuration: %s", e)
        sys.exit(2)

    results, violations_found = run_audit(audit_dir, config)

    if violations_found:
        log.warning("\nDetailed Violations:")
        for file, violations in results.items():
            if violations:
                log.warning("\nFile: %s", file)
                for category, issues in violations.items():
                    log.warning("  %s:", category.capitalize())
                    for issue in issues:
                        issue_str = str(issue).replace("\n", "\\n")
                        log.warning("    - %s", issue_str)
        sys.exit(1)
    else:
        log.info("Project is compliant!")
        sys.exit(0)


if __name__ == "__main__":
    main()

# <<< ZEROTH LAW FOOTER >>>
