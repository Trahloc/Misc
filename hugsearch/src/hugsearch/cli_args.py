# FILE_LOCATION: hugsearch/src/hugsearch/cli_args.py
"""
# PURPOSE: Provide reusable command-line arguments for the hugsearch package.

## INTERFACES:
 - configure_logging(verbose: int) -> logging.Logger: Configures logging based on verbosity level.

## DEPENDENCIES:
 - logging: Standard logging functionality
"""
import logging

def configure_logging(verbose: int) -> logging.Logger:
    """
    PURPOSE: Configure logging based on verbosity level.

    PARAMS:
        verbose: Verbosity level (0=WARNING, 1=INFO, 2+=DEBUG)

    RETURNS: Configured logger instance
    """
    if verbose == 0:
        log_level = logging.WARNING
    elif verbose == 1:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger('hugsearch')
    logger.debug(f"Logging configured at level: {logging.getLevelName(log_level)}")
    return logger