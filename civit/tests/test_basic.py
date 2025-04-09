"""
Basic tests to verify the test environment is working correctly.
"""

import pytest
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def test_environment_setup():
    """Test that the environment is set up correctly."""
    # Check that we have the project in the path
    project_root = Path(__file__).parent.parent
    assert str(project_root) in sys.path, "Project root not in path"

    # Test logging
    logger.info("Test environment is working")

    # This is a simple assertion that will always pass
    assert True, "Basic assertion works"


def test_import_modules():
    """Test that we can import our modules."""
    try:
        # Try to import modules from src.civit
        from civit.test_utils import get_current_test_name
        from civit.filename_generator import sanitize_filename

        # If we get here, the imports worked
        assert callable(
            get_current_test_name
        ), "get_current_test_name should be callable"
        assert callable(sanitize_filename), "sanitize_filename should be callable"
    except ImportError as e:
        pytest.fail(f"Failed to import modules: {e}")
