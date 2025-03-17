"""
# PURPOSE: Command-line interface for civit

## INTERFACES:
 # main()

## DEPENDENCIES:
 - argparse
 - logging
"""
import argparse
import logging

def parse_args():
    parser = argparse.ArgumentParser(description="Download files from civitai.com")
    parser.add_argument("urls", nargs="+", help="URLs to download from civitai.com")
    parser.add_argument(
        "-o", "--output-dir", default=".", help="Directory to save downloaded files"
    )
    parser.add_argument(
        "-k",
        "--api-key",
        help="Civitai API key (can also be set via CIVITAPI environment variable)",
    )
    parser.add_argument("-c", "--config", help="Path to configuration file")
    parser.add_argument(
        "--force-restart",
        action="store_true",
        help="Force restart downloads instead of resuming",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-q", "--quiet", action="store_true", help="Suppress all output")
    group.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    group.add_argument(
        "-vv", "--very-verbose", action="store_true", help="Very verbose output"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    # Configure logging
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    elif args.quiet:
        log_level = logging.ERROR
    else:
        log_level = logging.WARNING  # Default log level

    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)

    logger.info("Hello from civit")

    # Add the main logic here
    print("Main function executed")
