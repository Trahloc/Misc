"""
Debug entry point for civit CLI with debug mode enabled.
"""

import sys
import logging
from .cli import setup_logging, parse_args, main as civit_main

logger = logging.getLogger(__name__)


def main() -> int:
    """
    Debug main entry point that forces debug mode.
    """
    try:
        # Parse command line arguments
        args = parse_args()

        # Force debug mode
        args.debug = True

        # Set up logging with debug enabled
        setup_logging(verbose=True, debug=True)

        logger.debug("Running in debug mode - detailed logging is enabled")
        logger.debug(f"Command line arguments: {vars(args)}")

        # Call the main civit function with debug enabled
        return civit_main(args)

    except Exception as e:
        logger.error(f"Error in debug mode: {e}")
        logger.exception("Detailed traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
