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
from pathlib import Path
import click

# Use importlib.metadata for Python 3.8+ or pkg_resources as fallback
if sys.version_info >= (3, 8):
    from importlib import metadata as importlib_metadata
    def get_installed_packages():
        """Get installed packages using importlib.metadata."""
        return {dist.metadata["Name"].lower(): dist.version for dist in importlib_metadata.distributions()}
else:
    import pkg_resources
    def get_installed_packages():
        """Get installed packages using pkg_resources."""
        return {dist.project_name.lower(): dist.version for dist in pkg_resources.working_set}

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
    logger = ctx.obj['logger']
    
    # If no specific checks requested, do all checks
    if not any([deps, env, paths]):
        deps = env = paths = True
    
    try:
        if env:
            check_environment()
        
        if deps:
            check_dependencies()
            
        if paths:
            check_paths()
            
        click.echo("✅ All checks passed successfully!")
        logger.info("Environment check completed successfully")
    except Exception as e:
        error_msg = f"❌ Error during environment check: {str(e)}"
        click.echo(error_msg, err=True)
        logger.error(error_msg)
        ctx.exit(1)

def check_environment():
    """Check and display system and Python environment information."""
    click.echo("\n🔍 Environment Information:")
    click.echo(f"  • Python version: {sys.version.split()[0]}")
    click.echo(f"  • Python executable: {sys.executable}")
    click.echo(f"  • Operating system: {platform.system()} {platform.release()}")
    click.echo(f"  • Platform: {platform.platform()}")
    click.echo(f"  • Machine: {platform.machine()}")
    click.echo(f"  • Processor: {platform.processor() or 'Unknown'}")

def check_dependencies():
    """Check installed dependencies and their versions."""
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
            click.echo(f"  • {dep}: {installed_packages[dep]}")
        else:
            click.echo(f"  • {dep}: ❌ Not installed")
    
    # Now show all other dependencies
    click.echo("\n  Other dependencies:")
    for pkg, version in sorted(installed_packages.items()):
        if pkg not in key_deps:
            click.echo(f"  • {pkg}: {version}")

def check_paths():
    """Check and display important application paths."""
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
        status = "✅" if path.exists() else "⚠️ Not found"
        click.echo(f"  • {name}: {path} {status}")

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