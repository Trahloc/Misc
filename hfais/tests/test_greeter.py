import pytest
from hfais.greeter import greet_user

def test_greet_user():
    """Test the greet_user function."""
    assert greet_user("Alice") == "Hello, Alice!"
    assert greet_user("Bob", formal=True) == "Greetings, Bob!"