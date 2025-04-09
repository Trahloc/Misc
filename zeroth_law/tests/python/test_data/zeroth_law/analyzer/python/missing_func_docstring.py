# <<< ZEROTH LAW HEADER >>>
# FILE: missing_func_docstring.py
"""Module docstring."""


def function_without_docstring(x: int) -> int:
    # No docstring here
    return x * 2


def function_with_docstring(y: int) -> int:
    """This one is fine."""
    return y + 1


# <<< ZEROTH LAW FOOTER >>>
