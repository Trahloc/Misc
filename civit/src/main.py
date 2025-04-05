import logging
import sys
from .cli import parse_args, setup_logging
from .download_handler import download_file

logger = logging.getLogger(__name__)


def main() -> int:
    """
    Main entry point for the civit command-line tool.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Parse command line arguments
        args = parse_args()

        # Set up logging - adjust for actual arguments available
        # Try to use the new arguments, but fall back to older argument names if needed
        verbose = getattr(args, "verbose", False)
        debug = getattr(args, "debug", False)
        quiet = getattr(args, "quiet", False)

        setup_logging(verbose=verbose, debug=debug, quiet=quiet)

        # Print the actual command line arguments in debug mode to help diagnose problems
        # This will help us see what arguments are actually available
        logger.debug(f"Command line arguments available: {dir(args)}")
        logger.debug(f"Command line arguments values: {vars(args)}")

        # Log using custom naming or not
        if getattr(args, "custom_naming", True):
            logger.info("Using custom naming pattern for downloaded files")
        else:
            logger.warning(
                "Custom naming disabled. Using custom naming is recommended for better organization."
            )

        # Handle URLs differently depending on which args structure we have
        if hasattr(args, "urls") and isinstance(args.urls, list):
            urls = args.urls
            logger.debug(f"Processing multiple URLs: {urls}")
        elif hasattr(args, "url"):
            urls = [args.url]
            logger.debug(f"Processing single URL: {urls[0]}")
        else:
            # Try to find any positional arguments
            urls = []
            for attr in dir(args):
                if not attr.startswith("_") and attr not in (
                    "verbose",
                    "debug",
                    "quiet",
                    "custom_naming",
                    "output_folder",
                    "output_dir",
                    "api_key",
                ):
                    value = getattr(args, attr)
                    if isinstance(value, str) and (
                        "civitai.com" in value or value.startswith("http")
                    ):
                        urls.append(value)
            logger.debug(f"Extracted URLs from arguments: {urls}")

        if not urls:
            logger.error("No URLs provided for download")
            return 1

        # Get output path, supporting both output_folder and output_dir
        output_path = None
        for attr_name in ("output_folder", "output_dir"):
            if hasattr(args, attr_name):
                output_path = getattr(args, attr_name)
                break

        logger.debug(f"Output path: {output_path}")

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
