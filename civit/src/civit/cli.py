# FILE: src/civit/cli.py
"""
# PURPOSE: Command-line interface for civit

## INTERFACES: main()

## DEPENDENCIES: click, logging, download_file, api_key
"""
import click
import logging
from .download_file import download_file
from .api_key import get_api_key

@click.command()
@click.argument('urls', nargs=-1, required=True)
@click.option('-o', '--output-dir', default='.', help='Directory to save downloaded files')
@click.option('-k', '--api-key', help='Optional Civitai API key (environment variable CIVITAPI takes precedence)')
@click.option('-c', '--config', help='Path to configuration file')
@click.option('--force-restart', is_flag=True, help='Force restart downloads instead of resuming')
@click.option('-q', '--quiet', is_flag=True, help='Suppress all output')
@click.option('-v', '--verbose', is_flag=True, help='Verbose output')
@click.option('-vv', '--very-verbose', is_flag=True, help='Very verbose output')
@click.option('--timeout', default=30, help='Request timeout in seconds')
def main(urls=(), output_dir='.', api_key=None, config=None, force_restart=False, quiet=False, verbose=False, very_verbose=False, timeout=30):
    """Download files from civitai.com. URLs can be model pages or direct download links.

    Example: civit https://civitai.com/models/1234

    The API key can be provided via:
    1. CIVITAPI environment variable (preferred)
    2. -k/--api-key command line option
    3. Configuration file
    """
    # Configure logging
    if very_verbose:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    elif quiet:
        log_level = logging.ERROR
    else:
        log_level = logging.WARNING  # Default log level

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)
    logger.info('Starting civit downloader')

    # Get API key with precedence: env var > command line > config
    env_api_key = get_api_key()
    if env_api_key:
        api_key = env_api_key
        if len(api_key) > 4:
            logger.debug(f"Using API key from environment (starts with: {api_key[:4]}...)")
        else:
            logger.debug("Using API key from environment")

    if not api_key:
        logger.warning("No API key provided. Downloads requiring authentication will fail.")

    # Download files from URLs
    success = True
    for url in urls:
        try:
            filepath = download_file(url, output_dir, api_key=api_key)
            logger.info(f'Downloaded file to {filepath}')
        except Exception as e:
            logger.error(f'Failed to download {url}: {e}')
            success = False

    return 0 if success else 1

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Improved API key handling and logging
- Added better error handling
- Improved logging format with timestamps

## FUTURE TODOs: Add more configuration options
"""

if __name__ == '__main__':
    main()
