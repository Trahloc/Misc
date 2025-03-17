import logging


def setup_logging(verbosity: int = 0) -> None:
    """
    Configure the logging system based on verbosity level.
    PARAMS:
        verbosity (int): Logging level (0=quiet, 1=verbose, 2=very verbose)
    RETURNS:
        None
    """
    log_levels = {
        0: logging.WARNING,  # -q
        1: logging.INFO,  # -v
        2: logging.DEBUG,  # -vv
    }
    level = log_levels.get(verbosity, logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")
