```python
# FILE: project_head/src/civitai_downloader/__init__.py
"""
# PURPOSE: Provides functions for interacting with the Civitai API, downloading models and images, and sanitizing filenames.

## INTERFACES:
download_civitai_model_and_cover(model_id: int, model_version_id: int, destination_folder: str, model_type: str, format: str) -> None: Downloads a model and its cover image.
sanitize_for_filename(input_string: str) -> str: Sanitizes a string for use as a filename.

## DEPENDENCIES:
requests: For making HTTP requests.
pathvalidate: For sanitizing filenames.
os: For file system operations.
re: For regular expression operations
"""

import requests
import re
import os
from pathvalidate import sanitize_filename

def download_civitai_model_and_cover(model_id: int, model_version_id: int, destination_folder: str, model_type: str = "Model", format: str = "SafeTensor") -> None:
    """
    PURPOSE: Downloads a Civitai model and its cover image. Handles different model
    types and formats.

    CONTEXT: Uses internal functions: _get_model_info, _download_file

    PARAMS:
        model_id: The ID of the model.
        model_version_id: The version ID of the model.
        destination_folder: The folder to save the files to.
        model_type: The type of model (e.g., "Model", "Checkpoint").
        format: The file format (e.g., "SafeTensor", "PickleTensor").

    RETURNS: None
    """

    def _get_model_info(model_id: int) -> dict:
        """
        # FILE: project_head/src/civitai_downloader/_get_model_info.py (Internal)

        PURPOSE: Fetches model information from the Civitai API.

        CONTEXT: None

        PARAMS:
            model_id: The ID of the model.

        RETURNS:
            A dictionary containing the model information, or None if error.
        """
        url = f"https://civitai.com/api/v1/models/{model_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    """
    ## KNOWN ERRORS: None

    ## IMPROVEMENTS:

    ## FUTURE TODOs:
    * Add retry logic.
    """

    def _download_file(url: str, destination_folder: str, filename: str = None):
        """
        # FILE: project_head/src/civitai_downloader/_download_file.py (Internal)

        PURPOSE: Downloads a file from a URL, saves to a folder, handles Content-Disposition.

        CONTEXT: None

        PARAMS:
            url: The URL of the file to download.
            destination_folder: The folder to save the file to.
            filename (optional): The name to save the file as. If None, use filename from Content-Disposition or generate one.

        RETURNS: None
        """
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)

        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes

        if filename is None:
            # Try to get filename from Content-Disposition header
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                filename = re.findall("filename=(.+)", content_disposition)
                if filename:
                    filename = filename[0].strip('"') #remove quotes if present.
            if not filename:
              filename = "downloaded_file" #Fallback.

        filepath = os.path.join(destination_folder, filename)

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded '{filename}' to '{destination_folder}'")
    """
        ## KNOWN ERRORS: None

        ## IMPROVEMENTS:

        ## FUTURE TODOs:
        *  Consider adding a progress bar.
        *  Implement more robust error handling (e.g., retries).
    """

    model_info = _get_model_info(model_id)
    if not model_info:
        return

    model_name = model_info['name']
    sanitized_model_name = sanitize_for_filename(model_name)


    # Find the specific model version.
    model_version = None
    for version in model_info['modelVersions']:
      if version['id'] == model_version_id:
        model_version = version
        break

    if model_version is None:
      print (f"Could not find model version ID: {model_version_id}")
      return

    #Construct download URL.
    download_url = f"https://civitai.com/api/download/models/{model_version_id}"
    if model_type or format:
      download_url += "?"
    if model_type:
      download_url += f"type={model_type}"
    if format:
        download_url += f"&format={format}"


    # Get cover image URL
    cover_image_url = model_version['images'][0]['url']  # Use the first image as the cover
    sanitized_image_filename = sanitize_for_filename(f"{sanitized_model_name}_cover.png")
    _download_file(cover_image_url, destination_folder, sanitized_image_filename)

    #Download model, use the filename provided by the server
    _download_file(download_url, destination_folder)
    print(f"Model download URL: {download_url}")

"""
    ## KNOWN ERRORS: None

    ## IMPROVEMENTS:
        2025-03-17: Refactored into separate internal functions for clarity and SRP.

    ## FUTURE TODOs:
        *  Add support for authenticated downloads (using API keys).
        *  Consider adding a command-line interface.
"""
def sanitize_for_filename(input_string: str) -> str:
    """
    # FILE: project_head/src/civitai_downloader/sanitize_for_filename.py

    PURPOSE: Sanitizes a string for use in a filename, using pathvalidate and additional replacements.

    CONTEXT: None

    PARAMS:
        input_string: The string to sanitize.

    RETURNS:
        The sanitized string.
    """
    s = sanitize_filename(input_string)

    # pathvalidate handles most cases, but add a few more specific replacements:
    s = s.replace(" ", "_")  # Replace spaces with underscores
    s = s.replace(":", "-") # Replace colons
    s = s.replace('"', "")  # Remove double quotes
    s = s.replace("'", "")  # Remove single quotes
    s = re.sub(r'[\\/*?<>|]', '', s) # Remove remaining special characters
    s = s.strip(" .") #Remove leading/trailing spaces or dots.

    return s
"""
    ## KNOWN ERRORS: None

    ## IMPROVEMENTS:
    ## FUTURE TODOs: None
"""


# Example usage (would be in a separate script, importing from __init__.py):
# # FILE: project_head/examples/download_example.py
# from civitai_downloader import download_civitai_model_and_cover
#
# model_id = 1544458
# model_version_id = 1748884
# download_folder = "downloads"
#
# download_civitai_model_and_cover(model_id, model_version_id, download_folder)

"""
## KNOWN ERRORS: None.

## IMPROVEMENTS:
    2025-03-17: Initial implementation.

## FUTURE TODOs:
    * Add unit tests.
"""
```