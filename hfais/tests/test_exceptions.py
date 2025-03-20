import pytest
from hfais.exceptions import ZerothLawError

def test_custom_exception():
    """Test the ZerothLawError class."""
    with pytest.raises(ZerothLawError):
        raise ZerothLawError("Test error")