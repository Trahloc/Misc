import argparse
import logging
import os
import sys
from typing import List, Optional


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
        help="Civitai API key for authenticated downloads",
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

    # Set default for custom naming
    parser.set_defaults(custom_naming=True)

    # Verbosity options in a mutually exclusive group
    verbosity_group = parser.add_argument_group("verbosity")

    # Create mutually exclusive group for verbosity options
    verbosity = verbosity_group.add_mutually_exclusive_group()

    verbosity.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    verbosity.add_argument(
        "-q", "--quiet", action="store_true", help="Disable all output except errors"
    )

    # Debug option
    verbosity_group.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable detailed debug output (implies verbose)",
    )

    return parser.parse_args(args)


def setup_logging(
    verbose: bool = False, debug: bool = False, quiet: bool = False
) -> None:
    """
    Configure logging based on verbosity level.

    Args:
        verbose: Whether to enable verbose logging
        debug: Whether to enable debug level logging
        quiet: Whether to disable all but error logging
    """
    logger = logging.getLogger()

    if debug:
        log_level = logging.DEBUG
        # Create a more detailed formatter for debug mode
        log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    elif verbose:
        log_level = logging.INFO
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
    elif quiet:
        log_level = logging.ERROR
        log_format = "%(levelname)s: %(message)s"
    else:
        log_level = logging.WARNING
        log_format = "%(levelname)s: %(message)s"

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Clear any existing handlers
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.setLevel(log_level)


def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Configure logging based on verbosity flags
    setup_logging(
        verbose=args.verbose,
        debug=args.debug,
        quiet=args.quiet
    )

    # Import here to avoid circular imports
    from src.download_handler import download_file

    # Process each URL
    for url in args.urls:
        try:
            result = download_file(
                url=url,
                output_folder=args.output_folder,
                api_key=args.api_key,
                custom_filename=args.custom_naming
            )
            if result:
                logging.info(f"Successfully downloaded: {result}")
            else:
                logging.error(f"Failed to download: {url}")
        except Exception as e:
            logging.error(f"Error downloading {url}: {e}")


if __name__ == "__main__":
    main()
