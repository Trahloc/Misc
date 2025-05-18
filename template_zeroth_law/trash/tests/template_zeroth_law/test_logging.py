"""
# PURPOSE: Tests for template_zeroth_law.logging.

## INTERFACES:
 - test_configure_logging(): Test logger configuration
 - test_get_logger(): Test logger retrieval
 - test_log_levels(): Test different logging levels
 - test_file_handler(): Test file logging
 - test_invalid_inputs(): Test error handling

## DEPENDENCIES:
 - pytest: Testing framework
 - template_zeroth_law.logging: Module under test
"""

import logging
from pathlib import Path
from typing import Generator

import pytest

from template_zeroth_law.logging import (DEBUG_FORMAT, LOG_LEVELS,
                                         configure_logging, get_logger)


@pytest.fixture
def temp_log_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary log file path."""
    log_file = tmp_path / "test.log"
    yield log_file
    if log_file.exists():
        log_file.unlink()


def test_configure_logging_basic():
    """Test basic logger configuration."""
    logger = configure_logging()
    assert logger.getEffectiveLevel() == logging.INFO
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)


def test_configure_logging_debug():
    """Test logger configuration with DEBUG level."""
    logger = configure_logging(level="DEBUG")
    assert logger.getEffectiveLevel() == logging.DEBUG
    handler = logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.formatter._fmt == DEBUG_FORMAT  # type: ignore


def test_configure_logging_file(temp_log_file: Path):
    """Test logger configuration with file output."""
    logger = configure_logging(log_file=temp_log_file)
    assert len(logger.handlers) == 2
    assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

    # Test logging to file
    test_message = "Test log message"
    logger.info(test_message)

    # Verify message was written
    assert temp_log_file.exists()
    log_content = temp_log_file.read_text()
    assert test_message in log_content


def test_get_logger():
    """Test get_logger function."""
    logger_name = "test_logger"
    logger = get_logger(logger_name)
    assert isinstance(logger, logging.Logger)
    assert logger.name == logger_name


def test_invalid_log_level():
    """Test handling of invalid log level."""
    with pytest.raises(ValueError, match="Invalid log level"):
        configure_logging(level="INVALID")  # type: ignore


def test_invalid_log_file():
    """Test handling of invalid log file path."""
    invalid_path = "/nonexistent/directory/log.txt"
    with pytest.raises(OSError):
        configure_logging(log_file=invalid_path)


def test_log_levels_mapping():
    """Test log level string to int mapping."""
    for level_name, level_value in LOG_LEVELS.items():
        logger = configure_logging(level=level_name)
        assert logger.getEffectiveLevel() == level_value


def test_empty_logger_name():
    """Test handling of empty logger name."""
    with pytest.raises(AssertionError):
        get_logger("")


def test_invalid_logger_name_type():
    """Test handling of invalid logger name type."""
    with pytest.raises(AssertionError):
        get_logger(123)  # type: ignore


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added comprehensive test coverage
 - Added fixture for temporary log files
 - Added tests for error cases
 - Added type annotations
 - Added docstrings

## FUTURE TODOs:
 - Add tests for custom log formats
 - Add tests for log rotation if implemented
 - Add tests for structured logging if implemented
"""
