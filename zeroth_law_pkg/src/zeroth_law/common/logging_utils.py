"""Common logging utilities, primarily structlog setup."""

import logging
import sys
import structlog
from typing import Optional

log = structlog.get_logger()


# === Logging Setup Function (using structlog) ===
def setup_structlog_logging(level_name: str, use_color: Optional[bool]) -> None:
    """Set up structlog logging based on level and color preference."""
    # Map level names to standard logging level numbers for filtering
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    level_num = level_map.get(level_name.lower(), logging.WARNING)

    # --- Reconfigure structlog --- #
    # Determine renderer based on color preference
    should_use_color = use_color if use_color is not None else sys.stderr.isatty()
    renderer = structlog.dev.ConsoleRenderer(colors=should_use_color)

    # Restore original configuration using stdlib filtering
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,  # Can restore caching now
    )

    # Restore stdlib level setting
    root_logger = logging.getLogger()  # Get stdlib root logger
    root_logger.setLevel(level_num)

    # Restore handler check
    if not root_logger.hasHandlers():
        handler = logging.StreamHandler()
        root_logger.addHandler(handler)

    log.info(
        "structlog_reconfigured",
        min_level=level_name.upper(),
        level_num=level_num,
        color_enabled=should_use_color,
        handler_added=not root_logger.hasHandlers(),
    )


# <<< ZEROTH LAW FOOTER >>>
