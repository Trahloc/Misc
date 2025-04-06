"""
Example tests demonstrating how to use the No-Go test utilities.

These examples show how to write tests where a failure is the expected
and correct outcome, and should be reported as a success.
"""

import pytest
from tests.test_utils import nogo_test, expect_exception, assert_raises


def function_that_should_raise_value_error(value):
    """Example function that raises ValueError if value is negative."""
    if value < 0:
        raise ValueError("Value cannot be negative")
    return value


def function_that_should_raise_type_error(value):
    """Example function that raises TypeError if value is not an integer."""
    if not isinstance(value, int):
        raise TypeError("Value must be an integer")
    return value


# Example 1: Using pytest.raises directly
def test_value_error_with_pytest_raises():
    """Test that demonstrates using pytest.raises directly."""
    with pytest.raises(ValueError) as excinfo:
        function_that_should_raise_value_error(-1)
    assert "Value cannot be negative" in str(excinfo.value)


# Example 2: Using the nogo_test decorator
@nogo_test(ValueError, message="Value cannot be negative")
def test_value_error_with_nogo_decorator():
    """Test that demonstrates using the nogo_test decorator."""
    function_that_should_raise_value_error(-1)


# Example 3: Using the expect_exception decorator
@expect_exception(TypeError)
def test_type_error_with_expect_exception():
    """Test that demonstrates using the expect_exception decorator."""
    function_that_should_raise_type_error("not an integer")


# Example 4: Using assert_raises within a larger test
def test_multiple_validations_with_assert_raises():
    """Test that demonstrates using assert_raises within a larger test."""
    # First, test a valid case
    assert function_that_should_raise_value_error(10) == 10
    
    # Then, test an invalid case using assert_raises
    assert_raises(
        ValueError, 
        function_that_should_raise_value_error, 
        -5, 
        message="Value cannot be negative"
    )
    
    # Finally, test another valid case
    assert function_that_should_raise_value_error(0) == 0


# Example 5: Using pytest.mark.nogo directly
@pytest.mark.nogo
def test_with_nogo_marker():
    """Test that demonstrates using the nogo marker directly."""
    with pytest.raises(TypeError):
        function_that_should_raise_type_error("string value")


# Example 6: A test that should pass normally
def test_valid_cases():
    """Test that demonstrates normal passing tests."""
    assert function_that_should_raise_value_error(10) == 10
    assert function_that_should_raise_type_error(5) == 5 