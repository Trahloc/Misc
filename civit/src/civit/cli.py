"""
# PURPOSE: Command-line interface for Civitai model downloader.

## INTERFACES:
    main() -> None

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
from typing import Optional

from .download_handler import download_file
from .verify import verify_file, verify_directory

logger = logging.getLogger(__name__)

def setup_logging(verbose: int) -> None:
    """Configure logging based on verbosity level."""
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG
        
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

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

def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Download models from Civitai")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                      help='Increase verbosity (can be used multiple times)')
    parser.add_argument('--api-key', help='Civitai API key')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download a model')
    download_parser.add_argument('url', help='Model download URL')
    download_parser.add_argument('--output', '-o', type=Path, help='Output directory')
    download_parser.add_argument('--resume', action='store_true', help='Resume interrupted downloads')
    download_parser.add_argument('--custom-naming', action='store_true',
                               help='Use custom filename format')
    download_parser.add_argument('--force-delete', action='store_true',
                               help='Delete corrupted files without confirmation')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify and optionally rename files')
    verify_parser.add_argument('paths', nargs='+', help='Files or directories to verify (supports wildcards)')
    verify_parser.add_argument('--rename', action='store_true',
                             help='Rename files that don\'t match the custom format')
    verify_parser.add_argument('--extensions', nargs='+', default=['.safetensors', '.pt', '.ckpt', '.pth'],
                             help='File extensions to process (default: .safetensors .pt .ckpt .pth)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    if args.command == 'download':
        try:
            success = download_file(
                args.url,
                output_dir=args.output,
                resume=args.resume,
                custom_naming=args.custom_naming,
                api_key=args.api_key,
                force_delete=args.force_delete
            )
            sys.exit(0 if success else 1)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            sys.exit(1)
    elif args.command == 'verify':
        try:
            paths = expand_paths(args.paths)
            if not paths:
                logger.error("No valid files or directories specified")
                sys.exit(1)
                
            all_success = True
            for path in paths:
                if path.is_file():
                    # Force process explicitly named files
                    success = verify_file(path, args.api_key, args.rename, args.extensions, force_process=True)
                    if not success:
                        all_success = False
                else:
                    results = verify_directory(path, args.api_key, args.rename, args.extensions)
                    if not results:
                        logger.error(f"No files were verified in {path}")
                        all_success = False
                    else:
                        failed = [f for f, s in results.items() if not s]
                        if failed:
                            logger.error(f"Verification failed for: {', '.join(failed)}")
                            all_success = False
                            
            sys.exit(0 if all_success else 1)
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
