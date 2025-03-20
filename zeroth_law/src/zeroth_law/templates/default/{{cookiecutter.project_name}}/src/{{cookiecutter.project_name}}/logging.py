"""
# PURPOSE: Provides unified logging configuration for the application.

## INTERFACES:
 - configure_logging(level: int, log_file: Optional[str] = None) -> logging.Logger: Set up application logging
 - get_logger(name: str) -> logging.Logger: Get a logger with the given name

## DEPENDENCIES:
 - logging: Python's built-in logging module
 - typing: Type annotations
"""
import logging
import os
import sys
from typing import Optional, Dict, Any

# Define log formats
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEBUG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
SIMPLE_FORMAT = "[%(levelname)s] %(message)s"

def configure_logging(
    level: int = logging.INFO, 
    log_file: Optional[str] = None,
    log_format: str = DEFAULT_FORMAT,
    date_format: str = "%Y-%m-%d %H:%M:%S",
) -> logging.Logger:
    """
    PURPOSE: Configure the application's logging system.
    
    PARAMS:
        level: Logging level (e.g. logging.DEBUG, logging.INFO)
        log_file: Optional file path to write logs to
        log_format: Format string for log messages
        date_format: Format string for timestamps
        
    RETURNS:
        The configured root logger
    """
    # Use more detailed format if debug level is enabled
    if level == logging.DEBUG:
        log_format = DEBUG_FORMAT
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates when reconfiguring
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)
    
    # Configure file handler if requested
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        root_logger.addHandler(file_handler)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """
    PURPOSE: Get a logger with the given name.
    
    PARAMS:
        name: Name for the logger, typically __name__ of the module
        
    RETURNS:
        A configured logger instance
    """
    return logging.getLogger(name)

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added support for file logging
 - Added different format options
 - Created helper function for getting module loggers

## FUTURE TODOs:
 - Add support for log rotation
 - Consider adding JSON logging for production environments
 - Add support for remote logging services
"""
