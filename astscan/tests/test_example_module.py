"""
# PURPOSE: Tests for the example_module.py

## INTERFACES:
 - TestExampleModule: Test class for example_module functions

## DEPENDENCIES:
 - unittest
 - astscan.example_module
"""

import unittest

from astscan.example_module import add_numbers, multiply_numbers


class TestExampleModule(unittest.TestCase):
    """Test class for example_module functions."""

    def test_add_numbers(self):
        """Test the add_numbers function."""
        result = add_numbers(2, 3)
        self.assertEqual(result, 5)

    def test_multiply_numbers(self):
        """Test the multiply_numbers function."""
        result = multiply_numbers(2, 3)
        self.assertEqual(result, 6)


if __name__ == "__main__":
    unittest.main()
