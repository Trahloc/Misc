# FILE_LOCATION: conftest.py
"""
# PURPOSE: Configure pytest for the zeroth_law project.

## INTERFACES:
 - pytest_configure: Configure pytest to add the project root to Python path
 - pytest_ignore_collect: Ignore cookiecutter template files
 - pytest_sessionfinish: Clean up temporary pytest installations

## DEPENDENCIES:
 - pytest
 - sys
 - pathlib
 - subprocess
 - tempfile
"""
import sys
import subprocess
from pathlib import Path
import tempfile
import pytest
import os


def pytest_configure(config):
    """
    PURPOSE: Add the project root to the Python path and configure tmpfs-based temp directory

    PARAMS:
        config: The pytest configuration object

    RETURNS:
        None
    """
    # Get the project root directory (where this conftest.py is located)
    root_dir = Path(__file__).parent

    # Add the project root to the Python path if it's not already there
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    # Use XDG_RUNTIME_DIR if available (RAM-based on most Linux systems)
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        temp_dir = tempfile.mkdtemp(prefix="pytest-", dir=runtime_dir)
    else:
        # Fallback to system default if XDG_RUNTIME_DIR is not available
        temp_dir = tempfile.mkdtemp(prefix="pytest-")

    os.chmod(temp_dir, 0o700)  # Secure permissions

    # Set pytest to use our secure tmpfs directory
    config.option.basetemp = Path(temp_dir)


def pytest_ignore_collect(path):
    """
    PURPOSE: Ignore cookiecutter template files during test collection.

    PARAMS:
        path: The path to check

    RETURNS:
        bool: True if the path should be ignored, False otherwise
    """
    # Convert path to string for easier checking
    path_str = str(path)

    # Ignore files in cookiecutter template directories
    if "cookiecutter-template" in path_str:
        return True

    # Ignore files with Jinja2 template syntax
    if "{{" in path_str and "}}" in path_str:
        return True

    return False


def pytest_sessionfinish(session, exitstatus):
    """
    PURPOSE: Clean up temporary pytest installations after the test session.

    PARAMS:
        session: The pytest session object
        exitstatus: The exit status of the test run

    RETURNS:
        None
    """
    try:
        # Get list of temporary pytest packages
        result = subprocess.run(
            ["pip", "list"], capture_output=True, text=True, check=True
        )

        # Find and uninstall temporary pytest packages
        temp_dir = str(session.config.option.basetemp)
        for line in result.stdout.split("\n"):
            if temp_dir in line:
                package = line.split()[0]
                subprocess.run(["pip", "uninstall", "-y", package], check=True)

        # Clean up the temporary directory
        if Path(temp_dir).exists():
            subprocess.run(["rm", "-rf", temp_dir], check=True)

    except subprocess.CalledProcessError:
        # Log error but don't fail the tests if cleanup fails
        print("Warning: Failed to clean up temporary pytest installations")


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added Python path configuration for pytest
 - Ensures tests can import the project modules without needing PYTHONPATH
 - Added proper cookiecutter template file ignoring

## FUTURE TODOs:
 - None
"""
