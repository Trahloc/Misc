"""
Civit package for downloading models from Civitai.
"""

# Import public API
from .exceptions import (
    CivitError,
    NetworkError,
    FileSystemError,
    InvalidResponseError,
    InvalidPatternError,
    MetadataError,
    ModelNotFoundError,
    ModelAccessError,
    URLValidationError,
    VersionNotFoundError,
    ModelVersionError,
    DownloadError,
    AuthenticationError,
    APIError,
)

# Import core functionality
from .download_handler import download_file
from .filename_generator import (
    extract_model_components,
    generate_custom_filename,
    should_use_custom_filename,
)

# Version information
__version__ = "100.0.2"
