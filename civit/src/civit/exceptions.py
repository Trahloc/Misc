"""
Custom exceptions for the Civit package.
"""


class CivitError(Exception):
    """Base class for all Civit exceptions."""

    pass


class NetworkError(CivitError):
    """Raised when a network operation fails."""

    pass


class FileSystemError(CivitError):
    """Raised when a file system operation fails."""

    pass


class InvalidResponseError(CivitError):
    """Raised when a response from an API is invalid or unexpected."""

    pass


class InvalidPatternError(CivitError):
    """Raised when a filename pattern is invalid."""

    pass


class MetadataError(CivitError):
    """Raised when metadata is invalid or missing required fields."""

    pass


class ModelNotFoundError(CivitError):
    """Raised when a model cannot be found on Civitai."""

    pass


class ModelAccessError(CivitError):
    """Raised when there's an issue accessing model data."""

    pass


class URLValidationError(CivitError):
    """Raised when a URL fails validation."""

    pass


class VersionNotFoundError(CivitError):
    """Raised when a model version cannot be found."""

    pass


class ModelVersionError(VersionNotFoundError):
    """Raised when a model version has an issue."""

    pass


class DownloadError(CivitError):
    """Raised when a download fails."""

    pass


class AuthenticationError(CivitError):
    """Raised when authentication fails."""

    pass


class APIError(CivitError):
    """Raised when an API request fails."""

    pass
