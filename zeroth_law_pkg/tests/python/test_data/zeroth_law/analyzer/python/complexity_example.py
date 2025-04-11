# File: tests/python/test_data/zeroth_law/analyzer/python/complexity_example.py
"""Module docstring."""


def complex_function(x: int, y: int, z: int) -> int:
    """This function has high cyclomatic complexity."""
    if x > 0:
        if y > 0:
            if z > 0:
                return 1
            return 2
        if z > 0:
            return 3
        return 4
    if y > 0:
        if z > 0:
            return 5
        return 6
    if z > 0:
        return 7
    return 8


# <<< ZEROTH LAW FOOTER >>>
