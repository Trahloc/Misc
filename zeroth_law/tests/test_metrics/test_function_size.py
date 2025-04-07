"""
# PURPOSE: Test function size metrics calculation

## INTERFACES:
  - test_simple_function: Test size calculation for a simple function
  - test_function_with_docstring: Test size calculation with docstring
  - test_function_with_comments: Test size calculation with comments
  - test_multiline_function: Test size calculation for multi-line function

## DEPENDENCIES:
    pytest
    ast
"""

import ast
from textwrap import dedent
from zeroth_law.metrics.function_size import calculate_function_size_metrics
from zeroth_law.utils.config import load_config


def test_simple_function():
    """Test line counting for a simple function without docstring."""
    code = dedent(
        """
    def simple_function():
        x = 1
        y = 2
        return x + y
    """
    ).strip()

    tree = ast.parse(code)
    func_node = tree.body[0]
    metrics = calculate_function_size_metrics(func_node)

    assert metrics["lines"] == 4  # def line + 3 body lines
    assert metrics["max_lines"] == 30  # Default from config
    assert not metrics["exceeds_max_lines"]


def test_function_with_docstring():
    """Test line counting for a function with a docstring."""
    code = dedent(
        '''
    def documented_function():
        """This is a docstring.
        It spans multiple lines.
        Three lines total."""
        x = 1
        return x
    '''
    ).strip()

    tree = ast.parse(code)
    func_node = tree.body[0]
    metrics = calculate_function_size_metrics(func_node)

    assert metrics["lines"] == 3  # def line + 2 body lines (excluding 3-line docstring)
    assert metrics["max_lines"] == 30  # Default from config
    assert not metrics["exceeds_max_lines"]


def test_function_with_comments():
    """Test line counting for a function with comments."""
    code = dedent(
        """
    def commented_function():
        # This is a comment
        x = 1
        # Another comment
        y = 2
        return x + y
    """
    ).strip()

    tree = ast.parse(code)
    func_node = tree.body[0]
    metrics = calculate_function_size_metrics(func_node)

    assert metrics["lines"] == 6  # def line + 5 body lines (including comment lines)
    assert metrics["max_lines"] == 30  # Default from config
    assert not metrics["exceeds_max_lines"]


def test_multiline_function():
    """Test line counting for a function with many lines."""
    code = dedent(
        """
    def long_function():
        x = 1
        y = 2
        z = 3
        a = 4
        b = 5
        c = 6
        d = 7
        e = 8
        f = 9
        g = 10
        h = 11
        i = 12
        j = 13
        k = 14
        l = 15
        m = 16
        n = 17
        o = 18
        p = 19
        q = 20
        r = 21
        s = 22
        t = 23
        u = 24
        v = 25
        w = 26
        x = 27
        y = 28
        z = 29
        return x + y + z
    """
    ).strip()

    tree = ast.parse(code)
    func_node = tree.body[0]
    metrics = calculate_function_size_metrics(func_node)

    assert metrics["lines"] == 31  # def line + 30 body lines
    assert metrics["max_lines"] == 30  # Default from config
    assert metrics["exceeds_max_lines"]  # This function exceeds the limit


def test_empty_function():
    """Test line counting for an empty function."""
    code = "def empty_function(): pass"

    tree = ast.parse(code)
    func_node = tree.body[0]
    metrics = calculate_function_size_metrics(func_node)

    assert metrics["lines"] == 1  # just the def line
    assert metrics["max_lines"] == 30  # Default from config
    assert not metrics["exceeds_max_lines"]


def test_single_line_function():
    """Test line counting for a single-line function."""
    code = "def one_liner(): return 42"

    tree = ast.parse(code)
    func_node = tree.body[0]
    metrics = calculate_function_size_metrics(func_node)

    assert metrics["lines"] == 1  # just the def line
    assert metrics["max_lines"] == 30  # Default from config
    assert not metrics["exceeds_max_lines"]


def test_respects_config():
    """Test that function size metrics respect provided configuration."""
    code = dedent(
        """
    def long_function():
        x = 1
        y = 2
        z = 3
        a = 4
        b = 5
        c = 6
        d = 7
        e = 8
        f = 9
        g = 10
        h = 11
        i = 12
        j = 13
        k = 14
        l = 15
        m = 16
        n = 17
        o = 18
        p = 19
        q = 20
        r = 21
        s = 22
        t = 23
        u = 24
        v = 25
        w = 26
        x = 27
        y = 28
        z = 29
        return x + y + z
    """
    ).strip()

    tree = ast.parse(code)
    func_node = tree.body[0]

    # Test with default config (30 lines)
    metrics = calculate_function_size_metrics(func_node)
    assert metrics["lines"] == 31
    assert metrics["max_lines"] == 30
    assert metrics["exceeds_max_lines"]

    # Test with custom config (50 lines)
    custom_config = {"max_function_lines": 50}
    metrics = calculate_function_size_metrics(func_node, custom_config)
    assert metrics["lines"] == 31
    assert metrics["max_lines"] == 50
    assert not metrics["exceeds_max_lines"]
