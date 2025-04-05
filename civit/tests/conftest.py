"""
# PURPOSE: Configuration file for pytest to ensure proper import paths.

## DEPENDENCIES:
- pytest: For running tests.
- pathlib: For path operations.
- sys: For modifying import paths.

## TODO: None
"""

import sys
import os
import pytest
import json
import logging
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock
from .test_utils.mock_data_loader import (
    load_mock_model,
    load_mock_version_metadata,
    get_mock_response_for_url,
)
from tests.test_utils.network_guard import (
    mock_requests,
    disable_network,
    enable_network,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("civit.conftest")

# Add the project root directory to the Python path so tests can import modules
project_root = Path(__file__).parent.parent
src_path = project_root / "src"

# Add both project root and src directory to path if not already there
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

logger.info(f"Python path: {sys.path}")

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added path configuration to ensure tests can import from the project root directory
- Simplified testing approach to use only standard Python and pytest
- Removed all dependencies on external packages that cause import issues
- Added network guards to prevent real network calls during tests

## FUTURE TODOs:
- Consider adding fixture factories for common test cases.
"""

# Sample model data based on a real Civitai model
MOCK_MODEL_DATA = {
    "id": 1204563,
}


@pytest.fixture
def mock_civitai_data() -> Dict[str, Any]:
    """
    Provides mock data for Civitai model testing.

    Returns:
        Dict[str, Any]: A dictionary containing mock model data
    """
    return MOCK_MODEL_DATA.copy()


@pytest.fixture
def mock_model_data():
    """Fixture providing standard mock model data"""
    return load_mock_model()


@pytest.fixture
def mock_version_1447126():
    """Fixture providing mock data for version 1447126"""
    return load_mock_version_metadata("1447126")


@pytest.fixture
def mock_version_1436228():
    """Fixture providing mock data for version 1436228"""
    return load_mock_version_metadata("1436228")


@pytest.fixture
def mock_requests():
    """Fixture for mocking requests that returns proper mock data based on URL"""
    with patch("requests.get") as mock_get:

        def configure_mock_response(url, **kwargs):
            mock_response = MagicMock()
            mock_data = get_mock_response_for_url(url)

            if mock_data:
                mock_response.json.return_value = mock_data
                mock_response.status_code = 200

                # Set up headers for file download mocking
                if "download/models" in url:
                    file_info = next(
                        (
                            f
                            for f in mock_data.get("files", [])
                            if f.get("primary", False)
                        ),
                        None,
                    )
                    if file_info:
                        filename = file_info.get("name", "download.safetensors")
                        mock_response.headers = {
                            "content-disposition": f'filename="{filename}"',
                            "content-length": str(file_info.get("sizeKB", 1000) * 1024),
                        }
                        mock_response.iter_content.return_value = [b"mock file content"]
            else:
                # Default mock for unrecognized URLs
                mock_response.status_code = 404
                mock_response.json.side_effect = ValueError("No JSON data available")

            return mock_response

        mock_get.side_effect = configure_mock_response
        yield mock_get


@pytest.fixture
def temp_test_file(tmp_path):
    """Create a temporary test file for testing."""
    test_file = tmp_path / "test.zip"
    test_file.write_text("test content")
    return test_file


@pytest.fixture(autouse=True)
def no_network_access():
    """Automatically prevent real network access in all tests unless explicitly allowed."""
    disable_network()
    yield
    enable_network()


# The mock_requests fixture is already imported from network_guard.py
# No need to re-export it here as pytest will automatically discover it
