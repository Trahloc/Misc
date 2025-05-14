"""
# PURPOSE: Civitai model downloader and verifier.

## INTERFACES:
    download_file(url: str, output_dir: Optional[Path] = None, resume: bool = False,
                 custom_naming: bool = False, api_key: Optional[str] = None,
                 force_delete: bool = False) -> bool
    verify_file(filepath: Path, api_key: Optional[str] = None, rename: bool = False) -> bool
    verify_directory(directory: Path, api_key: Optional[str] = None, rename: bool = False) -> Dict[str, bool]

## DEPENDENCIES:
    pathlib: Path handling
    typing: Type hints
"""

from pathlib import Path
from typing import Dict, Optional

from .download_handler import download_file
from .verify import verify_directory, verify_file

__all__ = ["download_file", "verify_file", "verify_directory"]

# Import public API
from .exceptions import (
    APIError,
    AuthenticationError,
    CivitError,
    DownloadError,
    FileSystemError,
    InvalidPatternError,
    InvalidResponseError,
    MetadataError,
    ModelAccessError,
    ModelNotFoundError,
    ModelVersionError,
    NetworkError,
    URLValidationError,
    VersionNotFoundError,
)

# Import core functionality
from .filename_generator import (
    extract_model_components,
    generate_custom_filename,
    should_use_custom_filename,
)

# Version information
__version__ = "100.0.2"
