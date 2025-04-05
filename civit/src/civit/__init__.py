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

# Create a simple facade for common functions
try:
    from .download_handler import download_file, extract_filename_from_response
except ImportError:
    # If tqdm is not available, provide a stub for testing
    def download_file(*args, **kwargs):
        raise NotImplementedError("download_file requires tqdm to be installed")

    def extract_filename_from_response(*args, **kwargs):
        raise NotImplementedError(
            "extract_filename_from_response requires request dependencies"
        )


try:
    from .filename_generator import (
        extract_model_components,
        generate_custom_filename,
        should_use_custom_filename,
    )
except ImportError:
    # Provide stubs if module not available
    def extract_model_components(*args, **kwargs):
        raise NotImplementedError(
            "extract_model_components implementation not available"
        )

    def generate_custom_filename(*args, **kwargs):
        raise NotImplementedError(
            "generate_custom_filename implementation not available"
        )

    def should_use_custom_filename(*args, **kwargs):
        raise NotImplementedError(
            "should_use_custom_filename implementation not available"
        )
