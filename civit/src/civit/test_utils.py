"""
# PURPOSE: Test utilities for property-based testing.

## INTERFACES:
    - parameterized_test: Decorator for parameterized tests
    - random_int: Generate random integers
    - random_string: Generate random strings
    - random_list: Generate random lists

## DEPENDENCIES:
    - random: For random number generation
    - string: For string constants
    - typing: For type annotations
"""

import random
import string
import functools
from typing import List, Callable, Any, TypeVar, Generator, Tuple, Union, Optional

T = TypeVar("T")


def parameterized_test(test_cases):
    """
    Parameterize a test function with multiple test cases.

    Args:
        test_cases: List of tuples containing test case parameters

    Returns:
        Decorated test function that runs for each test case
    """

    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            for i, test_case in enumerate(test_cases):
                try:
                    if isinstance(test_case, tuple):
                        test_func(*args, *test_case, **kwargs)
                    else:
                        test_func(*args, test_case, **kwargs)
                except Exception as e:
                    print(f"Failed on test case {i}: {test_case}")
                    raise

        return wrapper

    return decorator


def random_int(
    min_val: int = -1000, max_val: int = 1000, count: int = 10
) -> Generator[int, None, None]:
    """
    Generate random integers within the given range.

    Args:
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)
        count: Number of values to generate

    Returns:
        Generator yielding random integers
    """
    for _ in range(count):
        yield random.randint(min_val, max_val)


def random_string(
    min_length: int = 0, max_length: int = 20, count: int = 10
) -> Generator[str, None, None]:
    """
    Generate random strings with varying lengths.

    Args:
        min_length: Minimum string length
        max_length: Maximum string length
        count: Number of strings to generate

    Returns:
        Generator yielding random strings
    """
    for _ in range(count):
        length = random.randint(min_length, max_length)
        yield "".join(
            random.choice(string.ascii_letters + string.digits) for _ in range(length)
        )


def random_list(
    element_generator: Optional[Callable[[], T]] = None,
    min_length: int = 0,
    max_length: int = 10,
    count: int = 5,
) -> Generator[List[T], None, None]:
    """
    Generate random lists with varying lengths.

    Args:
        element_generator: Function to generate list elements
        min_length: Minimum list length
        max_length: Maximum list length
        count: Number of lists to generate

    Returns:
        Generator yielding random lists
    """
    if element_generator is None:
        # Default to generating random integers
        element_generator = lambda: random.randint(-100, 100)

    for _ in range(count):
        length = random.randint(min_length, max_length)
        yield [element_generator() for _ in range(length)]
