"""
Custom test parameterization utilities.

This module provides pytest-compatible utilities for parameterized testing
without external dependencies.
"""

import random
import string
import logging
import functools
from typing import List, Dict, Any, Callable, Tuple, Union, Optional

logger = logging.getLogger(__name__)


def parametrize(argnames: Union[str, List[str]], argvalues: List[Any]):
    """
    A decorator for parameterized tests, similar to pytest.mark.parametrize.

    This provides a simplified version that works well with our custom test utilities.

    Args:
        argnames: Comma-separated string of argument names or list of argument names
        argvalues: List of argument value tuples, one for each test case

    Returns:
        Decorator function that generates multiple test cases
    """
    if isinstance(argnames, str):
        argnames = [x.strip() for x in argnames.split(",")]

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for values in argvalues:
                if not isinstance(values, (list, tuple)):
                    values = (values,)
                params = dict(zip(argnames, values))
                merged_kwargs = {**kwargs, **params}
                func(*args, **merged_kwargs)

        return wrapper

    return decorator


def generate_random_string(min_length: int = 1, max_length: int = 20) -> str:
    """
    Generate a random string with length between min_length and max_length.

    Args:
        min_length: Minimum length of the string
        max_length: Maximum length of the string

    Returns:
        A random string
    """
    length = random.randint(min_length, max_length)
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_int(min_value: int = 0, max_value: int = 100) -> int:
    """
    Generate a random integer between min_value and max_value.

    Args:
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)

    Returns:
        A random integer
    """
    return random.randint(min_value, max_value)


def generate_random_list(
    min_length: int = 0, max_length: int = 10, generator: Callable[[], Any] = None
) -> List[Any]:
    """
    Generate a random list with length between min_length and max_length.

    Args:
        min_length: Minimum length of the list
        max_length: Maximum length of the list
        generator: Function to generate each list element (defaults to random strings)

    Returns:
        A random list
    """
    if generator is None:
        generator = generate_random_string

    length = random.randint(min_length, max_length)
    return [generator() for _ in range(length)]


def property_test(num_examples: int = 100):
    """
    Run a property-based test multiple times with random inputs.

    Args:
        num_examples: Number of examples to generate

    Returns:
        Decorator function that runs the test multiple times
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(num_examples):
                func(*args, **kwargs)

        return wrapper

    return decorator
