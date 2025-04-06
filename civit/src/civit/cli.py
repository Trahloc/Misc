"""
# PURPOSE: Command-line interface for Civitai model downloader.

## INTERFACES:
    main() -> None
    parse_args(args: list[str]) -> argparse.Namespace

## DEPENDENCIES:
    argparse: Command-line argument parsing
    logging: Logging functionality
    pathlib: Path handling
    sys: System-specific parameters and functions
    glob: Wildcard pattern matching
"""

import argparse
import logging
from pathlib import Path
import sys
import glob
from typing import Optional, List
import os

from .download_handler import download_file
from .verify import verify_file, verify_directory

logger = logging.getLogger(__name__)

def setup_logging(verbosity_level: int = 0, quiet: bool = False, debug: bool = False) -> None:
    """Configure logging based on verbosity level and debug flag."""
    level = logging.WARNING
    if debug:
        level = logging.DEBUG
    elif quiet:
        level = logging.ERROR
    elif verbosity_level == 1:
        level = logging.INFO
    elif verbosity_level >= 2:
        level = logging.DEBUG
        
    logger = logging.getLogger()
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

def expand_paths(paths: list[str]) -> list[Path]:
    """Expand wildcards in paths and convert to Path objects."""
    expanded = []
    for path in paths:
        # Handle wildcards
        if '*' in path or '?' in path:
            matches = glob.glob(path)
            if not matches:
                logger.warning(f"No files match pattern: {path}")
                continue
            expanded.extend(Path(m) for m in matches)
        else:
            expanded.append(Path(path))
    return expanded

def parse_args(args: List[str] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Civitai model downloader and manager')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='Decrease verbosity')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('-k', '--api-key', help='Civitai API key')
    parser.add_argument('-o', '--output-folder', default=os.getcwd(), help='Output directory')
    parser.add_argument('--custom-naming', action='store_true', default=True, help='Use custom filename format')
    parser.add_argument('--no-custom-naming', action='store_false', dest='custom_naming', help='Do not use custom filename format')
    parser.add_argument('-r', '--resume', action='store_true', help='Resume interrupted downloads')
    parser.add_argument('urls', nargs='+', help='Civitai model URLs to download')

    return parser.parse_args(args)

def main():
    args = parse_args()

    # Set up logging
    setup_logging(verbosity_level=args.verbose, quiet=args.quiet, debug=args.debug)

    # --- API Key Handling ---
    # If API key is not provided via argument, try the environment variable
    if not args.api_key:
        args.api_key = os.environ.get('CIVITAPI')
        if args.api_key:
            logger.debug("Using API key from CIVITAPI environment variable")
        else:
            logger.debug("No API key provided via argument or CIVITAPI environment variable")
    else:
        logger.debug("Using API key provided via command-line argument")
    # ------------------------

    # Process each URL
    for url in args.urls:
        try:
            download_file(
                url,
                output_dir=args.output_folder,
                custom_name=args.custom_naming,
                api_key=args.api_key,
                resume=args.resume
            )
        except Exception as e:
            logger.error(f"Failed to download {url}: {str(e)}")
            continue

if __name__ == '__main__':
    main()
