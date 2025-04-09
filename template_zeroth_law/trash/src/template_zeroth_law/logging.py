"""
# PURPOSE: Provides unified logging configuration for the application.

## INTERFACES:
 - configure_logging(level: int, log_file: Optional[str] = None) -> logging.Logger: Set up application logging
 - get_logger(name: str) -> logging.Logger: Get a logger with the given name

## DEPENDENCIES:
 - logging: Python's built-in logging module
 - typing: Type annotations
 - os.path: File path operations
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Literal, Union

# Define log formats and levels as constants
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEBUG_FORMAT = (
    "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
)
SIMPLE_FORMAT = "[%(levelname)s] %(message)s"

LogLevel = Union[
    Literal["DEBUG"],
    Literal["INFO"],
    Literal["WARNING"],
    Literal["ERROR"],
    Literal["CRITICAL"],
]
LOG_LEVELS: Dict[LogLevel, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(
    level: Union[int, LogLevel] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    log_format: str = DEFAULT_FORMAT,
    date_format: str = "%Y-%m-%d %H:%M:%S",
) -> logging.Logger:
    """
    PURPOSE: Configure the application's logging system.

    PRE-CONDITIONS & ASSUMPTIONS:
        - level is either an integer or a valid log level name
        - log_file path is writable if provided
        - Formats are valid logging format strings

    PARAMS:
        level: Logging level (e.g. logging.DEBUG, logging.INFO, or level name)
        log_file: Optional file path to write logs to
        log_format: Format string for log messages
        date_format: Format string for timestamps

    POST-CONDITIONS & GUARANTEES:
        - Root logger is configured with specified level
        - Console handler is always added
        - File handler is added if log_file is provided
        - All existing handlers are removed to prevent duplicates

    RETURNS:
        The configured root logger

    EXCEPTIONS:
        ValueError: If invalid log level provided
        OSError: If log file cannot be created
    """
    # Input validation
    if isinstance(level, str):
        if level not in LOG_LEVELS:
            raise ValueError(f"Invalid log level: {level}")
        level = LOG_LEVELS[level]
    assert isinstance(
        level, int
    ), f"Level must be int or valid level name, got {type(level)}"

    # Use more detailed format if debug level is enabled
    if level == logging.DEBUG:
        log_format = DEBUG_FORMAT

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)

    # Configure file handler if requested
    if log_file:
        log_path = Path(log_file)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(logging.Formatter(log_format, date_format))
            root_logger.addHandler(file_handler)
        except OSError as e:
            root_logger.error(f"Failed to create log file {log_file}: {e}")
            raise

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    PURPOSE: Get a logger with the given name.

    PRE-CONDITIONS & ASSUMPTIONS:
        - name is a non-empty string
        - Root logger is already configured

    PARAMS:
        name: Name for the logger, typically __name__ of the module

    POST-CONDITIONS & GUARANTEES:
        - Returns a logger instance with the specified name
        - Logger inherits settings from root logger

    RETURNS:
        A configured logger instance

    USAGE EXAMPLES:
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    assert name and isinstance(
        name, str
    ), f"Logger name must be non-empty string, got {name!r}"
    return logging.getLogger(name)


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added strong type hints using Union and Literal types
 - Added constants for log formats
 - Enhanced error handling for file operations
 - Added comprehensive docstrings with all required sections
 - Added input validation with assertions
 - Using pathlib for more robust path handling
 - Added proper logging of file handler creation failures

## FUTURE TODOs:
 - Add support for log rotation
 - Consider adding JSON logging for production
 - Add support for remote logging services
 - Add log message sanitization
 - Consider adding structured logging support
"""
