"""
Pytest configuration.

This file contains pytest configuration and fixtures.
"""

import os
import sys
import logging
import pytest
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Remove manual sys.path manipulation, rely on pyproject.toml for pytest
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))


def pytest_configure(config):
    """
    Configure pytest before test collection.

    This function sets up custom markers and ensures proper testing environment.

    Args:
        config: The pytest configuration object
    """
    logger.info(f"Python path: {sys.path}")

    # Add any markers or custom configurations
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require integration with external services",
    )
    config.addinivalue_line(
        "markers",
        "parametrize: marks tests that use custom parameterization",
    )


def pytest_addoption(parser):
    """Add custom command line options to pytest."""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests",
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests",
    )


def pytest_collection_modifyitems(config, items: List):
    """
    Modify test collection to handle test categories.

    Args:
        config: pytest configuration
        items: List of collected test items
    """
    # Skip slow tests unless --run-slow is specified
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    # Skip integration tests unless --run-integration is specified
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(
            reason="need --run-integration option to run"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
