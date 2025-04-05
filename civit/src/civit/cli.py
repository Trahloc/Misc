"""Command line interface for the civit package."""

import argparse
import logging
import os
import signal
import sys
from typing import List, Optional

logger = logging.getLogger("civit")


def handle_interrupt(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("", file=sys.stderr)
    logger.warning("Download interrupted by user (Ctrl+C).")
    sys.exit(1)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments.

    Args:
        args: Command line arguments to parse

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Download models from Civitai")

    # Positional arguments
    parser.add_argument("urls", nargs="+", help="URLs of the models to download")

    # Output options
    parser.add_argument(
        "-o",
        "--output-folder",
        help="Output folder for downloaded files",
        default=os.getcwd(),
    )

    parser.add_argument(
        "-k",
        "--api-key",
        help="Civitai API key for authenticated downloads (can also use CIVITAPI env var)",
        default=os.getenv("CIVITAPI"),  # Use CIVITAPI environment variable
    )

    # Add custom filename options
    parser.add_argument(
        "--custom-naming",
        action="store_true",
        help="Use custom naming pattern for downloaded files",
        dest="custom_naming",
    )

    parser.add_argument(
        "--no-custom-naming",
        action="store_false",
        dest="custom_naming",
        help="Disable custom naming pattern (use original filenames)",
    )

    # Add resume option
    parser.add_argument(
        "-r",
        "--resume",
        action="store_true",
        help="Attempt to resume interrupted downloads",
    )

    # Set default for custom naming
    parser.set_defaults(custom_naming=True)

    # Verbosity and Debugging options
    verbosity_group = parser.add_argument_group("verbosity and debugging")
    verbosity_group.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity level (-v for INFO, -vv for DEBUG)",
    )
    verbosity_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output except errors (overrides -v)",
    )
    verbosity_group.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable detailed debug output (equivalent to -vv, overrides -v and -q)",
    )

    return parser.parse_args(args)


def setup_logging(
    verbosity_level: int = 0, debug: bool = False, quiet: bool = False
) -> None:
    """
    Configure logging based on verbosity level.

    Args:
        verbosity_level: Level of verbosity (0=WARN, 1=INFO, 2+=DEBUG).
        debug: Whether to force debug level logging.
        quiet: Whether to disable all but error logging.
    """
    logger = logging.getLogger() # Get root logger to configure handlers

    # Determine log level and format based on flags (precedence: debug > quiet > verbosity)
    if debug:
        log_level = logging.DEBUG
        log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    elif quiet:
        log_level = logging.ERROR
        log_format = "%(levelname)s: %(message)s"
    elif verbosity_level >= 2:
        log_level = logging.DEBUG
        log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    elif verbosity_level == 1:
        log_level = logging.INFO
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
    else:  # Default (verbosity_level == 0)
        log_level = logging.WARNING
        log_format = "%(levelname)s: %(message)s"

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Clear any existing handlers on the root logger and add ours
    # This prevents potential duplicate logging if the function is called multiple times
    # or if other libraries configure the root logger.
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.setLevel(log_level)

    # Optionally set level for specific package loggers if needed
    # logging.getLogger('civit').setLevel(log_level)


def main() -> None:
    """Main entry point for the CLI."""
    # Register the interrupt handler
    signal.signal(signal.SIGINT, handle_interrupt)

    args = parse_args()

    # Configure logging based on verbosity flags
    setup_logging(
        verbosity_level=args.verbose, debug=args.debug, quiet=args.quiet
    )

    # Import download_handler dynamically AFTER logging is set up,
    # and potentially within the function to avoid top-level import issues
    # if download_handler itself logs at import time.
    try:
        # Assuming download_handler is in the same package level or src level
        # Adjust the import path based on your actual structure
        from .download_handler import download_file # Use relative import
    except ImportError:
        logging.error("Failed to import download_handler. Check project structure and installation.")
        sys.exit(1)


    # Process each URL
    for url in args.urls:
        try:
            logging.debug(f"Processing URL: {url}") # Add debug log
            result = download_file(
                url=url,
                output_folder=args.output_folder,
                api_key=args.api_key,
                custom_filename=args.custom_naming,
                resume=args.resume
            )
            if result:
                logging.info(f"Successfully downloaded: {result}")
            else:
                # download_file logs errors internally, but we can add a summary error
                logging.error(f"Failed to download: {url}")
        except Exception as e:
            # Catch any unexpected errors during the download process for a specific URL
            logging.exception(f"Unexpected error downloading {url}: {e}")


if __name__ == "__main__":
    # This allows running the script directly, e.g., python src/civit/cli.py
    main()
