import unittest
from unittest.mock import patch, MagicMock
import logging
import os
from civit.signal_handler import signal_handler
from civit.logging_setup import setup_logging, JsonFormatter
from civit.api_key import get_api_key
from civit.model_info import get_model_info
from civit.url_extraction import extract_model_id, extract_download_url
import pytest
from tests.test_utils import silent_errors


class TestSignalHandler(unittest.TestCase):
    """
    Test suite for signal handling functionality.
    """

    @patch("sys.exit")
    @patch("logging.info")
    def test_signal_handler(self, mock_logging_info, mock_sys_exit):
        """Test signal handler function"""
        signal_handler(2, None)
        mock_logging_info.assert_called_once_with(
            "\nDownload interrupted. Cleaning up..."
        )
        mock_sys_exit.assert_called_once_with(1)


class TestLoggingSetup(unittest.TestCase):
    """
    Test suite for logging setup functionality.
    """

    @patch("logging.basicConfig")
    def test_setup_logging(self, mock_basicConfig):
        """Test logging setup with different verbosity levels"""
        setup_logging(0)
        mock_basicConfig.assert_called_with(
            level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        setup_logging(1)
        mock_basicConfig.assert_called_with(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        setup_logging(2)
        mock_basicConfig.assert_called_with(
            level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
        )


class TestApiKey(unittest.TestCase):
    """
    Test suite for API key retrieval functionality.
    """

    @patch("os.environ.get")
    @patch("logging.error")
    def test_get_api_key(self, mock_logging_error, mock_environ_get):
        """Test API key retrieval from environment variable"""
        mock_environ_get.return_value = "test_api_key"
        self.assertEqual(get_api_key(), "test_api_key")
        mock_environ_get.return_value = None
        self.assertIsNone(get_api_key())
        mock_logging_error.assert_called_once_with(
            "CIVITAPI environment variable not set. Please set it with:\n"
            "export CIVITAPI=your_api_key_here\n"
            "You can get an API key from: https://civitai.com/user/account"
        )


class TestModelInfo(unittest.TestCase):
    """
    Test suite for model information retrieval functionality.
    """

    @silent_errors(logger_names=["civit.model_info"])
    @patch("requests.get")
    def test_get_model_info(self, mock_get):
        """Test successful model information retrieval"""
        # Setup mock success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"modelVersions": [{"id": 1234}]}
        mock_get.return_value = mock_response

        # Test successful API call
        result = get_model_info("1234")
        self.assertEqual(result, {"modelVersions": [{"id": 1234}]})

        # Setup mock failure
        mock_response_error = MagicMock()
        mock_response_error.status_code = 404
        mock_response_error.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response_error

        # Test API error handling
        result = get_model_info("1234")
        self.assertIsNone(result)


class TestUrlExtraction(unittest.TestCase):
    """
    Test suite for URL extraction functionality.
    """

    @silent_errors(logger_names=["root"])
    def test_extract_model_id(self):
        """Test model ID extraction from URL"""
        self.assertEqual(extract_model_id("https://civitai.com/models/1234"), "1234")
        self.assertIsNone(extract_model_id("https://civitai.com/images/1234"))

    @silent_errors(logger_names=["root"])
    @patch("civit.url_extraction.get_model_info")
    def test_extract_download_url(self, mock_get_model_info):
        """Test download URL extraction from model info"""
        mock_get_model_info.return_value = {
            "modelVersions": [{"downloadUrl": "https://download.url"}]
        }
        self.assertEqual(
            extract_download_url("https://civitai.com/models/1234"),
            "https://download.url",
        )
        mock_get_model_info.return_value = None
        self.assertIsNone(extract_download_url("https://civitai.com/models/1234"))


class TestLoggingSetup:
    def test_setup_logging(self):
        logger = setup_logging(level=logging.INFO, json_format=True)
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)


if __name__ == "__main__":
    unittest.main()
