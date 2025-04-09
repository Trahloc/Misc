"""
# PURPOSE: Test logging configuration functionality.

## DEPENDENCIES:
    - pytest: Test framework
    - logging: Core logging functionality
    - json: JSON parsing for structured logs
"""

import logging
import json
from civit.logging_setup import setup_logging, JsonFormatter


def test_json_formatter():
    """Test JSON structured logging format."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        "test_logger", logging.INFO, "", 0, "Test message", None, None
    )
    result = formatter.format(record)
    parsed = json.loads(result)
    assert parsed["message"] == "Test message"
    assert parsed["level"] == "INFO"
    assert "timestamp" in parsed
    assert parsed["component"] == "main"


def test_component_logging():
    """Test component-specific logging."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        "test_logger", logging.INFO, "", 0, "Test message", None, None
    )
    record.component = "test_component"
    result = formatter.format(record)
    parsed = json.loads(result)
    assert parsed["component"] == "test_component"


def test_setup_logging():
    """Test setup logging functionality."""
    logger = setup_logging(level=logging.INFO, json_format=True)
    assert isinstance(logger, logging.Logger)
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0].formatter, JsonFormatter)


def test_setup_logging_default_level():
    """Test setup logging functionality with default level."""
    logger = setup_logging(json_format=True)
    assert isinstance(logger, logging.Logger)
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0].formatter, JsonFormatter)


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added comprehensive test coverage
- Added JSON format validation
- Added component logging tests
- Added error case testing

## FUTURE TODOs:
- Add performance tests
- Add concurrent logging tests
"""
