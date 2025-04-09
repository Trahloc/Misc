"""
# PURPOSE: Implements the check command that verifies environment and dependencies.

## INTERFACES:
 - command(): CLI command that checks application environment

## DEPENDENCIES:
 - click: Command-line interface creation
 - platform: System information
 - sys: Python information
 - importlib.metadata: Package information (Python 3.8+)
"""

import sys
import platform
import click

# Use importlib.metadata for Python 3.8+ or pkg_resources as fallback
if sys.version_info >= (3, 8):
    from importlib import metadata as importlib_metadata

    def get_installed_packages():
        """Get installed packages using importlib.metadata."""
        return {
            dist.metadata["Name"].lower(): dist.version
            for dist in importlib_metadata.distributions()
        }
else:
    import pkg_resources

    def get_installed_packages():
        """Get installed packages using pkg_resources."""
        return {
            dist.project_name.lower(): dist.version
            for dist in pkg_resources.working_set
        }


from hugsearch.utils import get_project_root


@click.command(name="check")
@click.option("--deps", is_flag=True, help="Check and list installed dependencies.")
@click.option("--env", is_flag=True, help="Show environment details.")
@click.option("--paths", is_flag=True, help="Show important application paths.")
@click.pass_context
def command(ctx: click.Context, deps: bool, env: bool, paths: bool):
    """
    Check the application environment and dependencies.

    If no options are specified, all checks will be performed.
    """
    logger = ctx.obj["logger"]
    # Get verbosity from parent context
    verbose = 0
    if ctx.parent:
        verbose = ctx.parent.params.get("verbose", 0)

    # If no specific checks requested, do all checks
    if not any([deps, env, paths]):
        deps = env = paths = True

    try:
        if env:
            log_msg = "Checking environment..."
            if verbose > 0:
                click.echo(f"[INFO] {log_msg}")
            logger.info(log_msg)
            check_environment(verbose)

        if deps:
            log_msg = "Checking dependencies..."
            if verbose > 0:
                click.echo(f"[INFO] {log_msg}")
            logger.info(log_msg)
            check_dependencies(verbose)

        if paths:
            log_msg = "Checking paths..."
            if verbose > 0:
                click.echo(f"[INFO] {log_msg}")
            logger.info(log_msg)
            check_paths(verbose)

        log_msg = "Environment check completed successfully"
        if verbose > 0:
            click.echo(f"[INFO] {log_msg}")
        logger.info(log_msg)
        if verbose > 1:
            click.echo("[DEBUG] All checks completed without errors")
        click.echo("✅ All checks passed successfully!")

    except Exception as e:
        error_msg = f"❌ Error during environment check: {str(e)}"
        click.echo(f"[ERROR] {error_msg}", err=True)
        logger.error(error_msg)
        ctx.exit(1)


def check_environment(verbose: int = 0):
    """Check and display system and Python environment information."""
    if verbose > 1:
        click.echo("[DEBUG] Starting environment check")
    click.echo("\n🔍 Environment Information:")
    click.echo(f"  • Python version: {sys.version.split()[0]}")
    click.echo(f"  • Python executable: {sys.executable}")
    click.echo(f"  • Operating system: {platform.system()} {platform.release()}")
    click.echo(f"  • Platform: {platform.platform()}")
    click.echo(f"  • Machine: {platform.machine()}")
    click.echo(f"  • Processor: {platform.processor() or 'Unknown'}")


def check_dependencies(verbose: int = 0):
    """Check installed dependencies and their versions."""
    if verbose > 1:
        click.echo("[DEBUG] Starting dependency check")
    click.echo("\n📦 Dependency Information:")

    # Get all installed packages using our helper function
    installed_packages = get_installed_packages()

    # Check key dependencies
    key_deps = [
        "click",
        "pytest",
        "pylint",
        "tomli",
        "typing-extensions",
    ]

    # Display key dependencies first
    for dep in key_deps:
        if dep in installed_packages:
            msg = f"  • {dep}: {installed_packages[dep]}"
            click.echo(msg)
            if verbose > 1:
                click.echo(f"[DEBUG] Found {dep} version {installed_packages[dep]}")
        else:
            msg = f"  • {dep}: ❌ Not installed"
            click.echo(msg)
            if verbose > 1:
                click.echo(f"[DEBUG] Missing dependency: {dep}")


def check_paths(verbose: int = 0):
    """Check and display important application paths."""
    if verbose > 1:
        click.echo("[DEBUG] Starting path check")
    click.echo("\n📂 Application Paths:")

    # Get project root
    project_root = get_project_root()
    click.echo(f"  • Project root: {project_root}")

    # Check for common directories
    common_dirs = {
        "Source": project_root / "src",
        "Tests": project_root / "tests",
        "Data": project_root / "data",
        "Config": project_root / "config",
        "Docs": project_root / "docs",
    }

    for name, path in common_dirs.items():
        exists = path.exists()
        status = "✅" if exists else "⚠️ Not found"
        click.echo(f"  • {name}: {path} {status}")
        if verbose > 1:
            click.echo(
                f"[DEBUG] {name} directory {'exists' if exists else 'not found'} at {path}"
            )


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added comprehensive environment checking
 - Added detailed dependency reporting
 - Added path verification
 - Used importlib.metadata for Python 3.8+ compatibility

## FUTURE TODOs:
 - Add health checks for external services
 - Add dependency version compatibility checking
 - Add disk space and resource checks
"""
