"""
# PURPOSE

  Test suite for URL validation functionality.
  Ensures proper validation and normalization of civitai.com URLs.

## 1. INTERFACES

  TestUrlValidator: Test class for URL validation functionality
  TestUrlNormalizer: Test class for URL normalization functionality

## 2. DEPENDENCIES

  unittest: Python's unit testing framework
  url_validator: Local module containing URL validation functions
"""

import unittest
import sys
import os
import logging
from unittest.mock import patch

# Add parent directory to path so we can import our module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from url_validator import validate_url, normalize_url


class TestUrlValidator(unittest.TestCase):
    """
    CODE ENTITY PURPOSE:
        Test suite for URL validation functionality.
    """

    def setUp(self):
        """Disable logging during tests"""
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Re-enable logging after tests"""
        logging.disable(logging.NOTSET)

    def test_valid_url(self):
        """Test validation of correctly formatted civitai.com URLs"""
        valid_urls = [
            "https://civitai.com/models/1234",
            "https://civitai.com/images/5678",
            "https://www.civitai.com/models/1234",
        ]
        for url in valid_urls:
            self.assertTrue(validate_url(url), f"URL should be valid: {url}")

    def test_invalid_url(self):
        """Test validation of incorrectly formatted URLs"""
        invalid_urls = [
            "",  # empty string
            "not_a_url",  # not a URL
            "http://civitai.com/models/1234",  # HTTP instead of HTTPS
            "https://otherdomain.com/path",  # wrong domain
            "https://fake-civitai.com/models/1234",  # fake domain
        ]
        for url in invalid_urls:
            self.assertFalse(validate_url(url), f"URL should be invalid: {url}")

    @patch("url_validator.logging.error")
    def test_invalid_url_error_messages(self, mock_logging_error):
        """Test error messages for invalid URLs"""
        invalid_urls = [
            ("", "Invalid URL scheme or netloc: "),
            ("not_a_url", "Invalid URL scheme or netloc: not_a_url"),
            (
                "http://civitai.com/models/1234",
                "Invalid URL scheme or netloc: http://civitai.com/models/1234",
            ),
            (
                "https://otherdomain.com/path",
                "Invalid domain: otherdomain.com. Expected domain: civitai.com",
            ),
            (
                "https://fake-civitai.com/models/1234",
                "Invalid domain: fake-civitai.com. Expected domain: civitai.com",
            ),
            (
                "https://civitai.com/invalidpath",
                "Invalid URL path: /invalidpath. Expected path to start with /models/ or /images/",
            ),
        ]
        for url, expected_message in invalid_urls:
            validate_url(url)
            mock_logging_error.assert_called_with(expected_message)

    def test_edge_case_urls(self):
        """Test edge cases for URL validation"""
        edge_case_urls = [
            "https://civitai.com/models/1234?query=param",  # URL with query parameters
            "https://civitai.com/models/1234#fragment",  # URL with fragment
            "https://civitai.com/models/1234/",  # URL with trailing slash
        ]
        for url in edge_case_urls:
            self.assertTrue(validate_url(url), f"URL should be valid: {url}")


class TestUrlNormalizer(unittest.TestCase):
    """
    CODE ENTITY PURPOSE:
        Test suite for URL normalization functionality.
    """

    def setUp(self):
        """Disable logging during tests"""
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Re-enable logging after tests"""
        logging.disable(logging.NOTSET)

    def test_url_normalization(self):
        """Test normalization of valid URLs"""
        test_cases = [
            ("https://civitai.com/models/1234", "https://civitai.com/models/1234"),
            ("https://www.civitai.com/models/1234", "https://civitai.com/models/1234"),
        ]
        for input_url, expected_url in test_cases:
            self.assertEqual(normalize_url(input_url), expected_url)

    def test_invalid_url_normalization(self):
        """Test normalization of invalid URLs returns None"""
        invalid_urls = ["", "not_a_url", "http://otherdomain.com/path"]
        for url in invalid_urls:
            self.assertIsNone(normalize_url(url))

    def test_edge_case_normalization(self):
        """Test normalization of edge case URLs"""
        edge_case_urls = [
            (
                "https://civitai.com/models/1234?query=param",
                "https://civitai.com/models/1234",
            ),  # URL with query parameters
            (
                "https://civitai.com/models/1234#fragment",
                "https://civitai.com/models/1234",
            ),  # URL with fragment
            (
                "https://civitai.com/models/1234/",
                "https://civitai.com/models/1234",
            ),  # URL with trailing slash
        ]
        for input_url, expected_url in edge_case_urls:
            self.assertEqual(normalize_url(input_url), expected_url)


if __name__ == "__main__":
    unittest.main()

"""
## Current Known Errors

None - Initial implementation

## Improvements Made

- Created comprehensive test suite for URL validation
- Added tests for URL normalization
- Included edge cases and invalid inputs
- Properly handled logging during tests

## Future TODOs

- Add more test cases for specific civitai.com URL patterns
- Add tests for rate limiting functionality when implemented
- Consider adding mock tests for network-related functionality
"""
