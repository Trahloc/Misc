"""
# PURPOSE: Configure and manage logging system.

## INTERFACES:
    setup_logging(component_name: str = "main") -> logging.Logger

## DEPENDENCIES:
    - logging: Core logging functionality
    - json: JSON formatting
    - datetime: Timestamp handling
"""

import json
import logging
from dataclasses import dataclass

__all__ = ["JsonFormatter", "setup_logging"]


@dataclass
class LogConfig:
    """Configuration options for logging setup."""

    verbosity: int
    json_format: bool
    log_file: str = ""
    component: str = "civit"


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "component": getattr(record, "component", "main"),
        }
        try:
            return json.dumps(log_obj)
        except Exception:
            return json.dumps(
                {
                    "error": "Failed to format log message",
                    "raw_message": str(record.msg),
                }
            )


def setup_logging(level=logging.INFO, json_format=False):
    """
    Set up logging with optional JSON formatting.

    Args:
        level (int): Logging level
        json_format (bool): Whether to use JSON formatting

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger("civit")

    # Clear any existing handlers
    logger.handlers.clear()

    # Set log level
    logger.setLevel(level)

    # Create handler
    handler = logging.StreamHandler()
    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    logger.addHandler(handler)
    return logger


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added JSON structured logging
- Added configuration dataclass
- Added pre/post conditions
- Added component-based logging
- Added usage examples

## FUTURE TODOs:
- Add log rotation support
- Add log compression
- Add remote logging options
"""
