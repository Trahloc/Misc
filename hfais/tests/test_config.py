import pytest
from hfais.config import DEFAULT_CONFIG

def test_config_exists():
    """Test that the DEFAULT_CONFIG object exists."""
    assert DEFAULT_CONFIG is not None