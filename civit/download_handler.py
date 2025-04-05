from typing import Dict, Any, Optional
import os
import re
import logging
import requests
from urllib.parse import urlparse
from filename_generator import generate_custom_filename

logger = logging.getLogger(__name__)


class DownloadHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _get_filename(
        self,
        url: str,
        headers: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        use_custom_naming: bool = False,
    ) -> str:
        """
        Determine the filename for the download, either from Content-Disposition header,
        original URL, or custom naming pattern.

        Args:
            url: The URL being downloaded
            headers: Response headers that may contain Content-Disposition
            metadata: Optional metadata about the model from Civitai API
            use_custom_naming: Whether to use custom naming pattern

        Returns:
            Filename to use for the download
        """
        self.logger.debug(
            f"Getting filename for URL: {url}, use_custom_naming: {use_custom_naming}, metadata available: {metadata is not None}"
        )

        # If custom naming is requested and we have metadata, use the custom naming pattern
        if use_custom_naming and metadata:
            try:
                self.logger.debug(
                    f"Attempting to generate custom filename with metadata: {metadata}"
                )
                custom_filename = generate_custom_filename(url, metadata)
                if custom_filename:
                    self.logger.info(f"Using custom filename: {custom_filename}")
                    return custom_filename
            except Exception as e:
                self.logger.warning(
                    f"Failed to generate custom filename: {e}, falling back to default method"
                )
                import traceback

                self.logger.debug(
                    f"Custom filename generation error: {traceback.format_exc()}"
                )

        # Original filename determination logic
        filename = None

        # Try to get filename from Content-Disposition header
        if "Content-Disposition" in headers:
            content_disposition = headers["Content-Disposition"]
            matches = re.findall(r'filename="?([^"]+)"?', content_disposition)
            if matches:
                filename = matches[0].strip()

        # If no filename found, extract from URL
        if not filename:
            path = urlparse(url).path
            filename = os.path.basename(path)
            # Remove query parameters if present in the filename
            if "?" in filename:
                filename = filename.split("?")[0]

        self.logger.debug(f"Using default filename: {filename}")
        return filename

    def download_file(
        self,
        url: str,
        output_dir: str,
        progress_callback=None,
        metadata: Optional[Dict[str, Any]] = None,
        use_custom_naming: bool = True,
        overwrite: bool = False,
    ) -> str:
        """
        Download a file from the given URL to the output directory.

        Args:
            url: URL to download from
            output_dir: Directory to save file to
            progress_callback: Optional callback for progress updates
            metadata: Optional metadata about the model from Civitai API
            use_custom_naming: Whether to use the custom naming pattern
            overwrite: Whether to overwrite existing files

        Returns:
            Path to the downloaded file
        """
        # Start a streaming request
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Determine filename using the enhanced method
        filename = self._get_filename(
            url, response.headers, metadata, use_custom_naming
        )
        filepath = os.path.join(output_dir, filename)

        # Check if file already exists
        if os.path.exists(filepath) and not overwrite:
            self.logger.info(f"File already exists: {filepath}")
            return filepath

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Download the file with progress tracking
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

        self.logger.info(f"Downloaded {url} to {filepath}")
        return filepath
