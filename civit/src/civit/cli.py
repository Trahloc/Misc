"""Command line interface for the civit package."""

import argparse
import logging
import sys

logger = logging.getLogger("civit")


def setup_logging(verbosity=0):
    """
    Set up logging based on verbosity level.

    Args:
        verbosity: 0=warning, 1=info, 2+=debug
    """
    if verbosity == 0:
        log_level = logging.WARNING
    elif verbosity == 1:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set the level for our package logger as well
    logger.setLevel(log_level)

    return log_level


def parse_args(args=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Civitai downloader utility")

    # Common options
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging (same as -vv)"
    )

    # Download options
    parser.add_argument(
        "-o",
        "--output",
        default="./downloads",
        help="Output directory for downloads (default: ./downloads)",
    )
    parser.add_argument(
        "-r", "--resume", action="store_true", help="Resume interrupted downloads"
    )
    parser.add_argument("-k", "--api-key", help="Civitai API key")

    # URL argument
    parser.add_argument("url", nargs="?", help="URL to download")

    return parser.parse_args(args)


def main(args=None):
    """Main entry point for the CLI."""
    parsed_args = parse_args(args)

    # Set up logging
    verbosity = parsed_args.verbose
    if parsed_args.debug:
        verbosity = 2  # Debug level

    setup_logging(verbosity)

    # If no URL provided, show help
    if not parsed_args.url and len(sys.argv) == 1:
        parse_args(["--help"])
        return

    # Just for testing, log the arguments
    logger.debug(f"Arguments: {parsed_args}")
    logger.info(f"Output directory: {parsed_args.output}")

    # Return 0 for success
    return 0


if __name__ == "__main__":
    sys.exit(main())
