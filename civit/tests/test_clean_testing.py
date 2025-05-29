"""
# PURPOSE: Demonstrate property-based testing using Python's built-in mechanisms

## INTERFACES:
    - test_addition_commutative: Test that addition is commutative using multiple data points
    - test_string_operations: Test string operations using multiple data points
    - test_data_structures: Test data structure operations on various input types

## DEPENDENCIES:
    - pytest: Testing framework
    - random: For generating random test data
"""

import random
import string


def test_addition_commutative():
    """
    Test that addition is commutative for a variety of integer inputs.

    This uses multiple data points instead of Hypothesis.
    """
    # Test with predefined values
    test_cases = [(0, 0), (1, 1), (-1, 1), (1000, 2000), (-5, -10), (2**10, 2**20)]

    # Test with random values (20 pairs)
    for _ in range(20):
        x = random.randint(-10000, 10000)
        y = random.randint(-10000, 10000)
        test_cases.append((x, y))

    # Test all cases
    for x, y in test_cases:
        assert x + y == y + x, f"Addition should be commutative: {x} + {y} = {y} + {x}"


def test_string_operations():
    """
    Test string operations using multiple test cases.
    """
    # Generate test cases
    test_strings = [
        "",
        "hello",
        "Hello World",
        "Special $^&*() Characters",
        "Unicode: 中文, Español, Русский",
    ]

    # Add random strings
    for _ in range(5):
        length = random.randint(1, 30)
        random_string = "".join(random.choice(string.printable) for _ in range(length))
        test_strings.append(random_string)

    # Test string operations
    for s in test_strings:
        # Test string reversal property
        reversed_twice = s[::-1][::-1]
        assert reversed_twice == s, f"String reversed twice should equal original: {s}"

        # Test string concatenation property
        assert s + "" == s, (
            f"String concatenated with empty string should be unchanged: {s}"
        )

        # Test string length property
        assert len(s + "a") == len(s) + 1, (
            f"Adding a character should increase length by 1: {s}"
        )


def test_data_structures():
    """
    Test data structure operations with various input types.
    """
    # Test list operations
    list_test_cases = [
        [],
        [1, 2, 3],
        ["a", "b", "c"],
        [True, False, None],
        [1, "mixed", True, None],
    ]

    for lst in list_test_cases:
        # Test list reversal property
        assert list(reversed(list(reversed(lst)))) == lst, (
            f"List reversed twice should equal original: {lst}"
        )

        # Test list concatenation with empty list
        assert lst + [] == lst, (
            f"List concatenated with empty list should be unchanged: {lst}"
        )

        # Test list copy is distinct from original
        lst_copy = lst.copy()
        assert lst_copy == lst, f"List copy should equal original: {lst}"
        if lst:  # Only test non-empty lists
            if isinstance(lst[0], list):
                lst_copy[0].append(
                    42
                )  # Shallow copy, modifies both if list contains lists
            else:
                lst_copy[0] = 42  # This should not affect original list
                assert lst_copy != lst, (
                    f"Modifying copy should not affect original: {lst}"
                )


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Implemented property-based testing without requiring Hypothesis
- Added comprehensive test cases for various data types
- Used random test data generation for better coverage

## FUTURE TODOs:
- Expand the test suite with more properties
- Create a custom test data generator for domain-specific testing
"""
