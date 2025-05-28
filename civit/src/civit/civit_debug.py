#!/usr/bin/env python3
"""
Standalone debug version of the civit CLI that can be run directly.
This provides the new functionality without modifying the installed package.

Usage:
    python -m src.civit_debug -d URL
"""

import logging
import sys
from pathlib import Path

# Make sure we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our CLI modules
from src.cli import parse_args, setup_logging
from src.download_handler import download_file

logger = logging.getLogger(__name__)


def main() -> int:
    """
    Main entry point for the civit debug command-line tool.
    """
    try:
        # Parse command line arguments
        args = parse_args()

        # Set up logging
        setup_logging(
            verbose=getattr(args, "verbose", False),
            debug=getattr(args, "debug", False),
            quiet=getattr(args, "quiet", False),
        )

        # Print debug info
        logger.debug(f"Command line arguments: {vars(args)}")

        # Process URLs
        if hasattr(args, "urls") and isinstance(args.urls, list):
            urls = args.urls
        elif hasattr(args, "url"):
            urls = [args.url]
        else:
            logger.error("No URLs provided for download")
            return 1

        # Get output folder
        if hasattr(args, "output_folder"):
            output_path = args.output_folder
        elif hasattr(args, "output_dir"):
            output_path = args.output_dir
        else:
            import os

            output_path = os.getcwd()

        # Download each URL
        success = True
        for url in urls:
            logger.info(f"Downloading: {url}")
            result = download_file(url, output_path, args)
            if not result:
                success = False
                logger.error(f"Failed to download: {url}")

        return 0 if success else 1
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.exception("Detailed traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
