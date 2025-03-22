# FILE_LOCATION: hugsearch/conftest.py
"""
# PURPOSE: Configure pytest for the hugsearch project.

## INTERFACES:
 - pytest_configure: Configure pytest to add the project root to Python path

## DEPENDENCIES:
 - pytest
 - sys
 - pathlib
"""
import sys
from pathlib import Path
import pytest

def pytest_configure(config):
    """
    PURPOSE: Add the project root to the Python path.

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

@pytest.fixture(scope="function")
async def test_db(tmp_path):
    """
    PURPOSE: Create a temporary test database that cleans up after itself

    PARAMS:
        tmp_path: pytest fixture providing a temporary directory

    RETURNS:
        Path: Path to the temporary database file
    """
    db_path = tmp_path / "test.db"
    yield db_path

    # Cleanup: Remove the database file after the test
    if db_path.exists():
        db_path.unlink()

# Add any other shared fixtures here
@pytest.fixture(scope="session")
def base_fixture():
    """
    PURPOSE: Basic fixture example for shared test resources

    RETURNS: None - placeholder for actual test resources
    """
    return None

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added Python path configuration for pytest
 - Ensures tests can import the project modules without needing PYTHONPATH

## FUTURE TODOs:
 - None
"""