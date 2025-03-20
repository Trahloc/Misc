"""
# PURPOSE: Configure pytest for the project

## INTERFACES: None - pytest uses this file automatically

## DEPENDENCIES: pytest
"""

import pytest

# Add any shared fixtures here
@pytest.fixture(scope="session")
def base_fixture():
    """
    PURPOSE: Basic fixture example for shared test resources

    RETURNS: None - placeholder for actual test resources
    """
    return None
