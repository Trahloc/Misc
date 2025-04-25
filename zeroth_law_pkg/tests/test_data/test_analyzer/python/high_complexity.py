# File: tests/python/test_data/zeroth_law/analyzer/python/high_complexity.py
"""Module docstring."""


def complex_function(a, b, c, d, e, f):
    """A complex function to test threshold."""
    if a:
        if b:
            if c:
                print(1)
            elif d:
                print(2)
            else:
                print(3)
        elif e:
            for i in range(10):
                if i % 2 == 0:
                    print(i)
    elif f:
        while True:
            try:
                assert a is not None
                break
            except AssertionError:
                pass
    return 0


# <<< ZEROTH LAW FOOTER >>>
