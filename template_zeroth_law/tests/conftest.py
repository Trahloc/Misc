"""
# PURPOSE: Configure pytest for the template_zeroth_law project.

## INTERFACES:
 - pytest_configure: Configure pytest to add the project root to Python path and set up secure temp directories
 - pytest_ignore_collect: Intelligent discernment for ignoring files
 - pytest_sessionfinish: Clean up temporary pytest installations
 - base_fixture: Shared test resource example

## DEPENDENCIES:
 - pytest
 - sys
 - pathlib
 - tempfile
 - os
 - subprocess
"""
import sys
import os
import subprocess
from pathlib import Path
import tempfile
import pytest


def pytest_configure(config):
    """
    PURPOSE: Add the project root to the Python path and configure tmpfs-based temp directory.

    PARAMS:
        config: The pytest configuration object

    RETURNS:
        None
    """
    # Get the project root directory (where this conftest.py is located)
    root_dir = Path(__file__).parent.parent  # Adjusted to point to the project root

    # Add the project root to the Python path if it's not already there
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    # Configure pytest-asyncio default fixture loop scope
    config.option.asyncio_default_fixture_loop_scope = "function"

    # Use XDG_RUNTIME_DIR for secure temporary directories
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        raise EnvironmentError(
            "XDG_RUNTIME_DIR is not set. This violates the Zeroth Law's prohibition on fallbacks for internal code."
        )

    temp_dir = tempfile.mkdtemp(prefix="pytest-", dir=runtime_dir)
    os.chmod(temp_dir, 0o700)  # Secure permissions

    # Set pytest to use our secure tmpfs directory
    config.option.basetemp = Path(temp_dir)


def pytest_ignore_collect(collection_path):
    """
    PURPOSE: Intelligent discernment for ignoring files during test collection.

    PARAMS:
        collection_path: The path to check

    RETURNS:
        bool: True if the path should be ignored, False otherwise
    """
    path_str = str(collection_path)

    # Debug: Print path being considered
    print(f"Considering path: {path_str}")

    # Only ignore specific patterns, be less restrictive
    if "non_testable" in path_str:
        print(f"Ignoring path (non_testable): {path_str}")
        return True

    # Only ignore .old files within the project, not entire .old directory
    if "template_zeroth_law/.old/" in path_str:
        print(f"Ignoring path (.old/): {path_str}")
        return True

    # Ignore files in the designated templates directory
    if "template_zeroth_law/src/template_zeroth_law/templates" in path_str:
        print(f"Ignoring path (templates): {path_str}")
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
        result = subprocess.run(
            ["pip", "list"], capture_output=True, text=True, check=True
        )
        temp_dir = str(session.config.option.basetemp)
        for line in result.stdout.split("\n"):
            if temp_dir in line:
                package = line.split()[0]
                subprocess.run(["pip", "uninstall", "-y", package], check=True)

        if Path(temp_dir).exists():
            subprocess.run(["rm", "-rf", temp_dir], check=True)
    except subprocess.CalledProcessError:
        print("Warning: Failed to clean up temporary pytest installations")


# Add any shared fixtures here
@pytest.fixture(scope="session")
def base_fixture():
    """
    PURPOSE: Basic fixture example for shared test resources.

    RETURNS: None - placeholder for actual test resources.
    """
    return None


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Removed fallback logic for secure temp directory setup
 - Refined file ignoring logic to align with project purpose
 - Retained session cleanup and shared fixture functionality

## FUTURE TODOs:
 - Add more shared fixtures as needed.
"""
