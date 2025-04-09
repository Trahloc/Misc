# FILE: src/zeroth_law/cli.py
"""Command-line interface for the Zeroth Law audit tool."""

import importlib.metadata  # Keep for version
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import click  # Import Click
import structlog
from structlog.stdlib import BoundLogger

from .analyzer import analyze_file_compliance

# Import config loader first, it should always be importable relative to cli.py
from .config_loader import DEFAULT_CONFIG, ConfigError, load_config
from .file_finder import find_python_files
from .reporter import report_violations

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


# --- Logging Setup Function ---
def setup_logging(log_level: int, use_color: bool) -> None:
    """Configures logging using structlog (Simplified)."""
    # Define processors
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,  # Add logger name
        structlog.stdlib.add_log_level,  # Add level e.g. 'info'
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),  # Add timestamp
        structlog.processors.StackInfoRenderer(),  # Optional: Add stack info on exception
        structlog.processors.format_exc_info,  # Format exception info
        structlog.stdlib.PositionalArgumentsFormatter(),  # Format positional arguments into message
        # Main renderer - MUST BE LAST
        structlog.dev.ConsoleRenderer(colors=use_color),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging handler to use structlog
    # Get the root logger and set its level
    std_logging_logger = logging.getLogger()
    std_logging_logger.setLevel(log_level)

    # Remove existing handlers if any (e.g., from previous basicConfig)
    # This prevents duplicate output
    for handler in std_logging_logger.handlers[:]:
        std_logging_logger.removeHandler(handler)

    # Create a standard handler and add it
    handler = logging.StreamHandler(sys.stderr)
    # No formatter needed on the handler itself, structlog processors do the work
    std_logging_logger.addHandler(handler)


# Get a logger instance using structlog
log: BoundLogger = structlog.get_logger()

# --- Imports from project --- #

# Attempt imports, handle potential issues if run directly vs installed
# Define expected types first
AnalyzeFunctionType = Any
analyze_file_compliance: AnalyzeFunctionType

try:
    # Assuming when installed, these relative imports work
    # Try importing without type ignore first - use specific type if possible
    # Assuming analyze_file_compliance returns Dict[str, List[str]]
    from .analyzer.python.analyzer import analyze_file_compliance as analyze_func
    from .config_loader import load_config

    AnalyzeFunctionType = type(analyze_func)
    analyze_file_compliance = analyze_func
    from .file_finder import find_python_files
except ImportError:
    # If run as script/module directly, adjust path
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    try:
        # Re-import using the adjusted path
        from src.zeroth_law.analyzer.python.analyzer import analyze_file_compliance as analyze_func_alt
        from src.zeroth_law.config_loader import load_config

        AnalyzeFunctionType = type(analyze_func_alt)
        analyze_file_compliance = analyze_func_alt
        from src.zeroth_law.file_finder import find_python_files
    except ImportError as e:
        print(f"Failed to import necessary modules even after path adjustment: {e}", file=sys.stderr)
        sys.exit(3)  # Exit code indicating import failure


# Modified run_audit to handle list of paths and recursive flag
def run_audit(paths_to_check: list[Path], recursive: bool, config: dict[str, Any]) -> tuple[dict[Path, dict[str, list[str]]], bool]:
    """Run the audit on specified paths and log results using the loaded configuration."""
    log.info("Starting audit on paths: %s (Recursive: %s)", [p.name for p in paths_to_check], recursive)
    log.info("Using configuration: %s", config)

    files_to_analyze: set[Path] = set()
    exclude_dirs_cfg = set(config.get("exclude_dirs", []))
    exclude_files_cfg = set(config.get("exclude_files", []))

    for path_item in paths_to_check:
        if path_item.is_file():
            if path_item.name.endswith(".py"):
                # Check if file matches exclude patterns before adding
                # Note: find_python_files handles this implicitly, but we need it here for direct files
                is_excluded = False
                for pattern in exclude_files_cfg:
                    if path_item.match(pattern):
                        log.debug(f"Excluding file due to pattern '{pattern}': {path_item}")
                        is_excluded = True
                        break
                if not is_excluded:
                    files_to_analyze.add(path_item)
            else:
                log.warning(f"Skipping non-Python file: {path_item}")
        elif path_item.is_dir():
            if recursive:
                log.debug(f"Recursively searching directory: {path_item}")
                try:
                    found_files = find_python_files(path_item, exclude_dirs=exclude_dirs_cfg, exclude_files=exclude_files_cfg)
                    files_to_analyze.update(found_files)
                except FileNotFoundError:
                    log.warning(f"Directory not found during recursive search: {path_item}")
            else:
                log.debug(f"Searching top-level of directory: {path_item}")
                # Non-recursive: just glob *.py in the immediate directory
                for py_file in path_item.glob("*.py"):
                    # Check excludes for top-level files too
                    is_excluded = False
                    for pattern in exclude_files_cfg:
                        if py_file.match(pattern):
                            log.debug(f"Excluding file due to pattern '{pattern}': {py_file}")
                            is_excluded = True
                            break
                    if not is_excluded:
                        # Check dir excludes for top-level scan? find_python_files did this.
                        # Simple check: is the file itself in an excluded dir name?
                        in_excluded_dir = False
                        for excluded_dir_name in exclude_dirs_cfg:
                            if excluded_dir_name in py_file.parts:
                                log.debug(f"Excluding file in excluded dir '{excluded_dir_name}': {py_file}")
                                in_excluded_dir = True
                                break
                        if not in_excluded_dir:
                            files_to_analyze.add(py_file)
        else:
            log.warning(f"Path is not a file or directory: {path_item}")

    if not files_to_analyze:
        log.warning("No Python files found to analyze in the specified paths.")
        return {}, False  # No violations found as no files were analyzed

    log.info("Found %d Python files to analyze.", len(files_to_analyze))

    all_results: dict[Path, dict[str, list[str]]] = {}
    files_with_violations = 0
    cwd = Path.cwd()  # Use for making result paths relative

    for file_path in sorted(list(files_to_analyze)):  # Sort for consistent output
        # Use relative path from CWD for reporting consistency
        try:
            relative_path = file_path.relative_to(cwd)
        except ValueError:
            relative_path = file_path  # Keep absolute if not relative to CWD

        log.debug("Analyzing: %s", relative_path)
        try:
            # Ensure analyze_file_compliance is callable
            if not callable(analyze_file_compliance):
                raise TypeError("analyze_file_compliance function not loaded correctly.")

            violations = analyze_file_compliance(
                file_path,
                max_complexity=config.get("max_complexity", 10),
                max_lines=config.get("max_lines", 100),
                max_params=config.get("max_parameters", 5),
                max_statements=config.get("max_statements", 50),
                ignore_rules=config.get("ignore_codes", []),  # Use ignore_codes from config
            )
            if violations:
                all_results[relative_path] = violations
                files_with_violations += 1
                log.warning(" -> Violations found in %s: %s", relative_path, list(violations.keys()))
            else:
                all_results[relative_path] = {}  # Explicitly mark compliant files
        except Exception as e:  # Keep broad exception for analysis errors
            log.exception(" -> ERROR analyzing file %s: %s", relative_path, e)
            all_results[relative_path] = {"analysis_error": [str(e)]}
            files_with_violations += 1

    log.warning("-" * 40)
    log.warning("Audit Summary:")
    log.info(" Total files analyzed: %d", len(files_to_analyze))
    log.warning(" Files with violations: %d", files_with_violations)
    log.info(" Compliant files: %d", len(files_to_analyze) - files_with_violations)
    log.warning("-" * 40)

    violations_found = files_with_violations > 0
    return all_results, violations_found


# --- Click CLI Definition ---
# Define version here for the option
_VERSION = importlib.metadata.version("zeroth_law")


# Shared callback for verbosity options
def _verbosity_callback(ctx: click.Context, param: click.Parameter, value: bool | None) -> None:
    if not value or ctx.resilient_parsing:
        return
    # Determine log level based on which flag was passed (or default)
    if ctx.params.get("quiet"):
        log_level = logging.WARNING
    elif ctx.params.get("debug"):
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO  # Default
    ctx.meta["log_level"] = log_level


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(_VERSION, "-V", "--version", package_name="zeroth_law")
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress informational messages, show only warnings and errors.",
    expose_value=False,  # Let callback handle it
    callback=_verbosity_callback,
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show informational messages (mutually exclusive with -q, -vv).",
    expose_value=False,  # Let callback handle it
    callback=_verbosity_callback,
    # Note: Click doesn't have built-in mutually exclusive groups like argparse.
    # We rely on the callback logic; passing multiple is not an error but last one wins effectively.
)
@click.option(
    "-vv",
    "--debug",
    is_flag=True,
    help="Show detailed debug messages (mutually exclusive with -q, -v).",
    expose_value=False,  # Let callback handle it
    callback=_verbosity_callback,
)
@click.option("-r", "--recursive", is_flag=True, help="Recursively search directories for Python files.")
@click.option("-c", "--color", "--colour", is_flag=True, help="Enable colored logging output.")
@click.pass_context  # Pass context object (ctx)
def cli(ctx: click.Context, paths: tuple[Path, ...], recursive: bool, color: bool) -> None:
    """Zeroth Law Compliance Auditor."""
    # Setup logging using collected level and color flag
    log_level = ctx.meta.get("log_level", logging.INFO)  # Get level from callback or default
    setup_logging(log_level, color)

    # Handle default path if none provided
    paths_list = list(paths) if paths else [Path.cwd()]
    # Paths are already resolved by click.Path(exists=True)

    try:
        config = load_config()
    except FileNotFoundError as e:
        log.error("Configuration error: %s", e, exc_info=True if log_level <= logging.DEBUG else False)
        ctx.exit(2)
    except ImportError as e:  # For missing TOML lib
        log.error("Configuration error: %s", e)
        ctx.exit(2)
    except Exception as e:
        log.exception("Unexpected error loading configuration: %s", e)
        ctx.exit(2)

    # Pass paths and recursive flag to run_audit
    # Use paths_list here
    results, violations_found = run_audit(paths_to_check=paths_list, recursive=recursive, config=config)

    # Debug: Log the full results dictionary
    log.debug("Full results from run_audit: %s", results)

    if violations_found:
        log.warning("\nDetailed Violations:")
        # Sort results for consistent output
        for file, violations in sorted(results.items()):
            if violations:
                log.warning("\nFile: %s", file)
                for category, issues in sorted(violations.items()):  # Sort categories
                    log.warning("  %s:", category.capitalize())
                    for issue in issues:  # Keep original order of issues within category
                        # Issue might be a tuple or string, handle gracefully
                        issue_str = str(issue)
                        # Simple newline handling for logging
                        if "\n" in issue_str:
                            log.warning("    - %s [...]", issue_str.split("\n")[0])  # Log only first line
                        else:
                            log.warning("    - %s", issue_str)
        ctx.exit(1)
    else:
        log.info("Project is compliant!")
        ctx.exit(0)


@cli.command("install-git-hook")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="Path to the Git repository root.",
    show_default=True,
)
@click.pass_context
def install_git_hook(ctx, git_root: str):
    """Install the custom multi-project pre-commit hook script.

    Generates and installs a script to .git/hooks/pre-commit that dispatches
    to project-specific .pre-commit-config.yaml files.
    Warns if a root config exists, suggesting this is for multi-project repos.
    """
    log.debug("Install git hook command called", git_root=git_root)
    git_root_path = Path(git_root).resolve()

    # 1. Verify it's a git repo by checking for .git dir
    dot_git_path = git_root_path / ".git"
    if not dot_git_path.is_dir():
        log.error("Target directory is not a valid Git repository root.", path=str(git_root_path))
        click.echo(f"Error: Directory '{git_root_path}' does not contain a .git directory.", err=True)
        ctx.exit(1)

    hooks_dir = dot_git_path / "hooks"
    hook_file_path = hooks_dir / "pre-commit"

    # 2. Generate script content
    try:
        script_content = generate_custom_hook_script()
        if not script_content.startswith("#!/usr/bin/env bash"):
            raise ValueError("Generated script content seems invalid.")  # Basic sanity check
    except Exception as e:
        log.exception("Failed to generate custom hook script content.")
        click.echo(f"Error: Failed to generate hook script: {e}", err=True)
        ctx.exit(1)

    # 3. Write script to hook file
    try:
        hooks_dir.mkdir(exist_ok=True)  # Ensure hooks directory exists
        with open(hook_file_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        log.info("Custom hook script written successfully.", path=str(hook_file_path))
    except OSError as e:
        log.exception("Failed to write pre-commit hook script.", path=str(hook_file_path))
        click.echo(f"Error: Could not write hook file to '{hook_file_path}': {e}", err=True)
        ctx.exit(1)

    # 4. Make script executable
    try:
        # Set executable permissions for user, group, others (ugo+x)
        current_permissions = os.stat(hook_file_path).st_mode
        os.chmod(hook_file_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        log.info("Set execute permissions on hook script.", path=str(hook_file_path))
    except OSError as e:
        log.exception("Failed to set execute permission on hook script.", path=str(hook_file_path))
        click.echo(f"Error: Could not set execute permission on '{hook_file_path}': {e}", err=True)
        # Don't exit, maybe user can fix manually, but warn
        click.echo("Warning: Please manually ensure the hook script is executable (`chmod +x ...`).", err=True)

    click.echo(f"Successfully installed Zeroth Law custom pre-commit hook to: {hook_file_path}")

    # 5. Check for root config and issue warning
    root_config_path = git_root_path / ".pre-commit-config.yaml"
    if root_config_path.is_file():
        log.warning("Root pre-commit config found during custom hook installation.")
        click.echo("-" * 20, err=True)
        click.echo("WARNING: Found '.pre-commit-config.yaml' at the Git root.", err=True)
        click.echo("         The Zeroth Law custom multi-project hook has been installed.", err=True)
        click.echo("         This hook prioritizes project-specific configs in subdirectories.", err=True)
        click.echo("         If this repository IS NOT intended as a multi-project monorepo,", err=True)
        click.echo("         you should restore the standard pre-commit hook behavior.", err=True)
        click.echo("         Consider running: zeroth-law restore-git-hooks", err=True)
        click.echo("-" * 20, err=True)


@cli.command("restore-git-hooks")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="Path to the Git repository root.",
    show_default=True,
)
@click.pass_context
def restore_git_hooks(ctx, git_root: str):
    """Restore the default pre-commit hook script.

    Runs `pre-commit install` to overwrite any custom hook script.
    Use this if the repository is not a multi-project monorepo.
    """
    log.debug("Restore git hooks command called", git_root=git_root)
    git_root_path = Path(git_root).resolve()

    # Verify it's a git repo first
    dot_git_path = git_root_path / ".git"
    if not dot_git_path.is_dir():
        log.error("Target directory is not a valid Git repository root.", path=str(git_root_path))
        click.echo(f"Error: Directory '{git_root_path}' does not contain a .git directory.", err=True)
        ctx.exit(1)

    try:
        log.info("Running pre-commit install...", cwd=str(git_root_path))
        result = subprocess.run(
            ["pre-commit", "install"],
            capture_output=True,
            text=True,
            check=True,
            cwd=git_root_path,
            errors="ignore",
        )
        log.info("pre-commit install completed.", output=result.stdout.strip())
        click.echo("Successfully restored default pre-commit hooks.")
        if result.stdout.strip():
            click.echo(result.stdout.strip())  # Show pre-commit output

    except FileNotFoundError:
        log.error("'pre-commit' command not found. Is pre-commit installed and in PATH?")
        click.echo("Error: 'pre-commit' command not found. Is it installed in your environment?", err=True)
        ctx.exit(1)
    except subprocess.CalledProcessError as e:
        log.error("'pre-commit install' failed.", stderr=e.stderr.strip())
        click.echo(f"Error running 'pre-commit install': {e.stderr.strip()}", err=True)
        ctx.exit(1)
    except Exception as e:
        log.exception(f"Unexpected error restoring git hooks in {git_root_path}: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)
        ctx.exit(1)


# Remove old argparse main function
# def main() -> None: ...

if __name__ == "__main__":
    cli()

# <<< ZEROTH LAW FOOTER >>>
