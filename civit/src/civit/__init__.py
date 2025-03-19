"""
# PURPOSE: Top-level package initialization for civit.
  Provides the main interface for downloading files from civitai.com.

## INTERFACES:
    - download_file(url: str, destination: str, api_key: Optional[str] = None) -> str:
      Downloads a file with optional API key authentication
    - get_api_key() -> Optional[str]:
      Gets the API key from environment variable

## DEPENDENCIES:
    - requests: HTTP request handling
    - click: CLI interface
    - tqdm: Progress bars
"""

from typing import List
from .download_file import download_file
from .api_key import get_api_key

__version__ = '100.0.1'

__all__: List[str] = [
    "download_file",
    "get_api_key",
]
