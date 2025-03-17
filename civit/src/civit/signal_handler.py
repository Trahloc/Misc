import logging
import sys


def signal_handler(_signum, _frame):
    """
    Handle interrupt signals gracefully.
    PARAMS:
        signum: Signal number
        frame: Current stack frame
    """
    logging.info("\nDownload interrupted. Cleaning up...")
    sys.exit(1)
