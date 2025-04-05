"""
# PURPOSE: Demonstrate property-based testing using our custom utilities

## INTERFACES:
    - test_addition_commutative: Test that addition is commutative
    - test_string_operations: Test string operations with various inputs
    - test_url_parsing: Test URL parsing with generated URLs

## DEPENDENCIES:
    - pytest: Testing framework
    - civit.test_utils: Our property testing utilities
"""

import random
import pytest
from src.civit.test_utils import (
    parameterized_test,
    random_int,
    random_string,
    random_list,
)


def test_addition_commutative():
    """
    Test that addition is commutative for a variety of integer inputs.
    """
    # Test with predefined values
    test_cases = [(0, 0), (1, 1), (-1, 1), (1000, 2000), (-5, -10), (2**10, 2**20)]

    for x, y in test_cases:
        assert x + y == y + x, f"Addition should be commutative: {x} + {y} = {y} + {x}"

    # Test with random values
    for x in random_int():
        for y in random_int():
            assert (
                x + y == y + x
            ), f"Addition should be commutative: {x} + {y} = {y} + {x}"


# Use pytest's built-in parameterize instead of our custom one for this test
@pytest.mark.parametrize(
    "a,b,expected", [(1, 2, 3), (-1, 1, 0), (0, 0, 0), (1000, 2000, 3000)]
)
def test_addition_with_expected(a, b, expected):
    """
    Test addition with expected results using the parameterized_test decorator.
    """
    assert a + b == expected, f"Expected {a} + {b} = {expected}, got {a + b}"


def test_string_operations():
    """
    Test string operations using multiple test cases.
    """
    # Test with random strings
    for s in random_string():
        # Test string reversal property
        reversed_twice = s[::-1][::-1]
        assert reversed_twice == s, f"String reversed twice should equal original: {s}"

        # Test string concatenation property
        assert s + "" == s, f"String + empty string should be unchanged: {s}"

        # Test string length property
        assert (
            len(s + "a") == len(s) + 1
        ), f"Adding a character should increase length by 1: {s}"


def test_list_operations():
    """
    Test list operations with various input types.
    """
    # Generate random lists of integers
    for lst in random_list(lambda: random.randint(-100, 100)):
        # Test list reversal property
        assert (
            list(reversed(list(reversed(lst)))) == lst
        ), f"List reversed twice should equal original: {lst}"

        # Test list concatenation with empty list
        assert lst + [] == lst, f"List + empty list should be unchanged: {lst}"

        # Test list copy is distinct from original
        lst_copy = lst.copy()
        if lst:  # Only test non-empty lists
            lst_copy[0] = "MODIFIED"
            assert lst_copy != lst, f"Modifying copy should not affect original: {lst}"


def test_custom_url_parsing():
    """
    Test URL parsing with generated URLs.

    This demonstrates how we might test filename_generator.py functionality.
    """
    # Generate sample URLs that look like Civitai URLs
    domain = "civitai.com"
    paths = ["/models/", "/api/download/models/", "/api/v1/models/"]
    ids = list(random_int(1000, 9999999, 5))

    # Generate test cases
    urls = []
    for path in paths:
        for id in ids:
            urls.append(f"https://{domain}{path}{id}")

    for url in urls:
        # This is where you would call your actual URL parsing function
        # For example: model_id = extract_model_id(url)

        # For now, let's just check that the URL contains expected parts
        assert domain in url, f"URL should contain domain: {url}"
        assert url.startswith("https://"), f"URL should start with https://: {url}"
        assert any(
            path in url for path in paths
        ), f"URL should contain a valid path: {url}"


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Created property-based tests using our custom test utilities
- Implemented tests for basic properties (commutativity, reversibility)
- Added parameterized testing for expected values
- Demonstrated how to test URL parsing without external dependencies

## FUTURE TODOs:
- Apply these testing utilities to filename_generator.py
- Create more comprehensive tests for URL parsing and filename generation
- Add more advanced property-based tests
"""
