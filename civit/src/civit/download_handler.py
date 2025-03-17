"""
# PURPOSE

  Handles file download operations with progress tracking.

## 1. INTERFACES

  download_with_progress(response, filepath: Path, total_size: int, existing_size: int = 0, mode: str = 'wb') -> bool:
    Downloads file content with progress bar tracking

## 2. DEPENDENCIES

  tqdm: Progress bar functionality
  pathlib: Path operations
  logging: Logging functionality
  requests: HTTP response handling

"""

import logging
from pathlib import Path
from tqdm import tqdm
from requests import Response


def download_with_progress(
    response: Response,
    filepath: Path,
    total_size: int,
    existing_size: int = 0,
    mode: str = "wb",
) -> bool:
    """
    Downloads file content with progress tracking.

    PARAMS:
        response (Response): HTTP response object with content
        filepath (Path): Path where file will be saved
        total_size (int): Total expected file size
        existing_size (int): Size of existing file if resuming
        mode (str): File open mode ('wb' or 'ab')

    RETURNS:
        bool: True if download successful, False otherwise
    """
    try:
        with open(filepath, mode, encoding=None if "b" in mode else "utf-8") as f, tqdm(
            desc=filepath.name,
            total=total_size,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
            initial=existing_size,
        ) as pbar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                pbar.update(size)

        logging.info("Downloaded %s successfully", filepath.name)
        return True

    except IOError as e:
        logging.error("Failed to write file: %s", str(e))
        return False
    except MemoryError as e:
        logging.error("Memory error during download: %s", str(e))
        return False


"""
## Current Known Errors

None

## Improvements Made

- Initial implementation
- Clean separation of download and progress tracking logic

## Future TODOs

- Add support for custom chunk sizes
- Add download speed calculation
- Add ETA estimation improvements
"""
