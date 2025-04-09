# FILE: src/zeroth_law/cli.py
"""Command-line interface for the Zeroth Law audit tool."""

import importlib.metadata  # Keep for version
import logging
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click  # Import Click
import structlog
from structlog.stdlib import BoundLogger

# Import config loader first, it should always be importable relative to cli.py
from .config_loader import DEFAULT_CONFIG, load_config
from .file_finder import find_python_files

# Ensure src is discoverable for imports when run directly
# This might not be strictly necessary when installed, but helps during development
# Moved import attempts lower to be within functions that need them or after logging setup

# Setup basic logging config - will be adjusted by CLI args
# Log to stderr by default
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
# Get logger early, but structlog config happens in setup_logging
log_std = logging.getLogger("zeroth_law")


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
    std_logging_logger = logging.getLogger()  # Get root logger
    std_logging_logger.setLevel(log_level)

    # Remove existing handlers if any (e.g., from previous basicConfig)
    for handler in std_logging_logger.handlers[:]:
        std_logging_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    std_logging_logger.addHandler(handler)


# Get a structlog logger instance - this will now use the configured setup
log: BoundLogger = structlog.get_logger()


# --- Audit Logic (Moved from main cli group) ---


def run_audit(
    paths_to_check: list[Path],
    recursive: bool,
    config: dict[str, Any],
    analyzer_func: Callable | None = None,  # Added analyzer_func argument
) -> tuple[dict[Path, dict[str, list[str]]], bool]:
    """Run the audit on specified paths and log results using the loaded configuration."""
    # Import analyzer only if not provided
    if analyzer_func is None:
        try:
            from .analyzer.python.analyzer import analyze_file_compliance as default_analyzer

            analyzer_func = default_analyzer
        except ImportError:
            project_root = Path(__file__).resolve().parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            try:
                from src.zeroth_law.analyzer.python.analyzer import analyze_file_compliance as default_analyzer_alt

                analyzer_func = default_analyzer_alt
            except ImportError as e:
                log.critical("Failed to import default analyzer in run_audit", error=e)
                raise

    # Ensure analyzer_func is callable before proceeding
    if not callable(analyzer_func):
        raise TypeError("Analyzer function provided or loaded is not callable.")

    # Import file_finder (still needed)
    try:
        from .file_finder import find_python_files
    except ImportError:
        project_root = Path(__file__).resolve().parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        try:
            from src.zeroth_law.file_finder import find_python_files
        except ImportError as e:
            log.critical("Failed to import file_finder in run_audit", error=e)
            raise

    log.info("Starting audit on paths: %s (Recursive: %s)", [p.name for p in paths_to_check], recursive)
    log.info("Using configuration: %s", config)

    files_to_analyze: set[Path] = set()
    exclude_dirs_cfg = set(config.get("exclude_dirs", []))
    exclude_files_cfg = set(config.get("exclude_files", []))

    for path_item in paths_to_check:
        if path_item.is_file():
            if path_item.name.endswith(".py"):
                is_excluded = False
                for pattern in exclude_files_cfg:
                    if path_item.match(pattern):
                        log.debug("Excluding file due to pattern '%s': %s", pattern, path_item)
                        is_excluded = True
                        break
                if not is_excluded:
                    files_to_analyze.add(path_item)
            else:
                log.warning("Skipping non-Python file: %s", path_item)
        elif path_item.is_dir():
            # Apply exclude_dirs check *before* recursion/globbing
            is_dir_excluded = False
            for excluded_dir_name in exclude_dirs_cfg:
                # Check if the current dir name matches or is a subdirectory of an excluded dir
                # Using parts allows for checking parent directory names as well
                if excluded_dir_name in path_item.parts:
                    log.debug("Skipping excluded directory: %s", path_item)
                    is_dir_excluded = True
                    break
                # Also check if the dir name itself matches (e.g. exclude '.venv')
                if path_item.name == excluded_dir_name:
                    log.debug("Skipping excluded directory: %s", path_item)
                    is_dir_excluded = True
                    break
            if is_dir_excluded:
                continue  # Skip this directory entirely

            if recursive:
                log.debug("Recursively searching directory: %s", path_item)
                try:
                    # Pass excludes to find_python_files
                    found_files = find_python_files(path_item, exclude_dirs=exclude_dirs_cfg, exclude_files=exclude_files_cfg)
                    files_to_analyze.update(found_files)
                except FileNotFoundError:
                    log.warning("Directory not found during recursive search: %s", path_item)
            else:
                log.debug("Searching top-level of directory: %s", path_item)
                for py_file in path_item.glob("*.py"):
                    is_excluded = False
                    # Check file excludes
                    for pattern in exclude_files_cfg:
                        if py_file.match(pattern):
                            log.debug("Excluding file due to pattern '%s': %s", pattern, py_file)
                            is_excluded = True
                            break
                    if not is_excluded:
                        files_to_analyze.add(py_file)
        else:
            log.warning("Path is not a file or directory: %s", path_item)

    if not files_to_analyze:
        log.warning("No Python files found to analyze in the specified paths.")
        return {}, False

    log.info("Found %d Python files to analyze.", len(files_to_analyze))

    all_results: dict[Path, dict[str, list[str]]] = {}
    files_with_violations = 0
    cwd = Path.cwd()

    for file_path in sorted(list(files_to_analyze)):
        try:
            relative_path = file_path.relative_to(cwd)
        except ValueError:
            relative_path = file_path

        log.debug("Analyzing: %s", relative_path)
        try:
            # Use the provided/loaded analyzer_func
            violations = analyzer_func(
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
                all_results[relative_path] = {}
        except Exception as e:
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


# --- Git Hook Script Generation --- #
def generate_custom_hook_script() -> str:
    """Generates the content for the custom multi-project pre-commit hook."""
    # Re-import necessary components here
    try:
        from .git_utils import generate_custom_hook_script as generate_hook
    except ImportError:
        project_root = Path(__file__).resolve().parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        try:
            from src.zeroth_law.git_utils import generate_custom_hook_script as generate_hook
        except ImportError as e:
            log.critical("Failed to import git_utils in generate_custom_hook_script", error=e)
            raise
    return generate_hook()


# --- Click CLI Definition ---
_VERSION = "unknown"
try:
    _VERSION = importlib.metadata.version("zeroth_law")
except importlib.metadata.PackageNotFoundError:
    log.warning("Could not determine package version using importlib.metadata.")


# Shared callback for verbosity options
def _verbosity_callback(ctx: click.Context, param: click.Parameter, value: bool | None) -> None:
    if not value or ctx.resilient_parsing:
        return
    # Store the desired level based on flags
    if ctx.params.get("quiet"):
        ctx.meta["log_level_request"] = logging.WARNING
    elif ctx.params.get("debug"):
        ctx.meta["log_level_request"] = logging.DEBUG
    else:  # Default or -v
        ctx.meta["log_level_request"] = logging.INFO


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))  # Changed: Renamed to cli_group
@click.version_option(_VERSION, "-V", "--version", package_name="zeroth_law")
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress informational messages, show only warnings and errors.",
    expose_value=False,
    callback=_verbosity_callback,
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show informational messages (default).",
    expose_value=False,
    callback=_verbosity_callback,
)
@click.option(
    "-vv",
    "--debug",
    is_flag=True,
    help="Show detailed debug messages.",
    expose_value=False,
    callback=_verbosity_callback,
)
@click.option("-c", "--color", "--colour", is_flag=True, help="Enable colored logging output.")
@click.pass_context
def cli_group(ctx: click.Context, color: bool) -> None:
    """Zeroth Law Compliance Auditor.

    Run without a command to perform an audit on specified paths (or CWD).
    """
    # Setup logging early based on flags passed to the group
    log_level = ctx.meta.get("log_level_request", logging.INFO)
    setup_logging(log_level, color)
    # Store final log level and color for commands to use if needed
    ctx.meta["log_level"] = log_level
    ctx.meta["color"] = color
    log.debug("CLI group initialized", log_level=log_level, color=color)


# New default command for auditing
@cli_group.command("audit")
@click.argument(
    "paths",
    nargs=-1,  # 0 or more arguments
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True),
)
@click.option("-r", "--recursive", is_flag=True, help="Recursively search directories for Python files.")
@click.pass_context
def audit_command(ctx: click.Context, paths: tuple[Path, ...], recursive: bool) -> None:
    """Perform compliance audit on specified PATHS (default: CWD)."""
    log_level = ctx.meta["log_level"]
    # Handle default path if none provided
    paths_list = list(paths) if paths else [Path.cwd()]
    log.debug("Audit command called", paths=paths_list, recursive=recursive)

    try:
        config = load_config()
    except FileNotFoundError as e:
        log.error("Configuration error: %s", e, exc_info=True if log_level <= logging.DEBUG else False)
        ctx.exit(2)
    except ImportError as e:
        log.error("Configuration error: %s", e)
        ctx.exit(2)
    except Exception as e:
        log.exception("Unexpected error loading configuration: %s", e)
        ctx.exit(2)

    # Pass arguments to run_audit (analyzer_func will use its default)
    results, violations_found = run_audit(paths_to_check=paths_list, recursive=recursive, config=config)

    if violations_found:
        log.warning("\nDetailed Violations:")
        for file, violations in sorted(results.items()):
            if violations:
                log.warning("\nFile: %s", file)
                for category, issues in sorted(violations.items()):
                    log.warning("  %s:", category.capitalize())
                    for issue in issues:
                        issue_str = str(issue)
                        if "\n" in issue_str:
                            log.warning("    - %s [...]", issue_str.split("\n")[0])
                        else:
                            log.warning("    - %s", issue_str)
        ctx.exit(1)
    else:
        log.info("Project is compliant!")
        ctx.exit(0)


# Attach other commands to the group
@cli_group.command("install-git-hook")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="Path to the Git repository root.",
    show_default=True,
)
@click.pass_context
def install_git_hook(ctx, git_root: str):
    """Install the custom multi-project pre-commit hook script."""
    # Setup logging using level from context
    log_level = ctx.meta.get("log_level", logging.INFO)
    color = ctx.meta.get("color", False)
    setup_logging(log_level, color)  # Re-setup in case command is run standalone
    log.debug("Install git hook command called", git_root=git_root)
    git_root_path = Path(git_root).resolve()

    dot_git_path = git_root_path / ".git"
    if not dot_git_path.is_dir():
        log.error("Target directory is not a valid Git repository root.", path=str(git_root_path))
        click.echo(f"Error: Directory '{git_root_path}' does not contain a .git directory.", err=True)
        ctx.exit(1)

    hooks_dir = dot_git_path / "hooks"
    hook_file_path = hooks_dir / "pre-commit"

    try:
        script_content = generate_custom_hook_script()
        if not script_content.startswith("#!/usr/bin/env bash"):
            raise ValueError("Generated script content seems invalid.")
    except Exception as e:
        log.exception("Failed to generate custom hook script content.")
        click.echo(f"Error: Failed to generate hook script: {e}", err=True)
        ctx.exit(1)

    try:
        hooks_dir.mkdir(exist_ok=True)
        with open(hook_file_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        log.info("Custom hook script written successfully.", path=str(hook_file_path))
    except OSError as e:
        log.exception("Failed to write pre-commit hook script.", path=str(hook_file_path))
        click.echo(f"Error: Could not write hook file to '{hook_file_path}': {e}", err=True)
        ctx.exit(1)

    try:
        current_permissions = os.stat(hook_file_path).st_mode
        os.chmod(hook_file_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        log.info("Set execute permissions on hook script.", path=str(hook_file_path))
    except OSError as e:
        log.exception("Failed to set execute permission on hook script.", path=str(hook_file_path))
        click.echo(f"Error: Could not set execute permission on '{hook_file_path}': {e}", err=True)
        click.echo("Warning: Please manually ensure the hook script is executable (`chmod +x ...`).", err=True)

    click.echo(f"Successfully installed Zeroth Law custom pre-commit hook to: {hook_file_path}")

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


@cli_group.command("restore-git-hooks")
@click.option(
    "--git-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="Path to the Git repository root.",
    show_default=True,
)
@click.pass_context
def restore_git_hooks(ctx, git_root: str):
    """Restore the default pre-commit hook script."""
    log_level = ctx.meta.get("log_level", logging.INFO)
    color = ctx.meta.get("color", False)
    setup_logging(log_level, color)
    log.debug("Restore git hooks command called", git_root=git_root)
    git_root_path = Path(git_root).resolve()

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
            click.echo(result.stdout.strip())

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


# Make the audit command the default if no other command is given
# This requires a bit more setup usually, but let's keep it explicit for now
# with the 'audit' command name.


if __name__ == "__main__":
    cli_group()  # Changed: Call the renamed group function

# <<< ZEROTH LAW FOOTER >>>
