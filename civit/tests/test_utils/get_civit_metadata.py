#!/usr/bin/env python3
import requests
import os
import json
import argparse
import sys
import re
from urllib.parse import urlparse, parse_qs


def parse_civitai_url(url: str) -> tuple[str | None, str | None, str | None]:
    """
    Parses a Civitai URL to determine the API endpoint and a base filename.

    Args:
        url: The Civitai URL string.

    Returns:
        A tuple containing:
        - The target API URL (e.g., https://civitai.com/api/v1/model-versions/123)
          or None if parsing fails.
        - The base filename suggestion (e.g., "model_version_123_metadata")
          or None if parsing fails.
        - An error message string if parsing fails, otherwise None.
    """
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        path = parsed_url.path

        model_id_from_path = None
        model_version_id_from_path = None
        model_version_id_from_query = None

        # --- Extraction Phase ---

        # Priority 1: Check query parameters for modelVersionId
        if "modelVersionId" in query_params:
            try:
                # parse_qs returns a list, get the first element
                model_version_id_from_query = int(query_params["modelVersionId"][0])
                print(
                    f"Found modelVersionId={model_version_id_from_query} in query parameters."
                )
            except (ValueError, IndexError):
                return (
                    None,
                    None,
                    f"Invalid modelVersionId in query string: {query_params['modelVersionId']}",
                )

        # Priority 2: Check path for /api/download/models/(\d+)
        # This is almost certainly a model version ID
        match_download = re.search(r"/api/download/models/(\d+)", path)
        if match_download:
            try:
                model_version_id_from_path = int(match_download.group(1))
                print(
                    f"Found ID {model_version_id_from_path} in download URL path (treating as version ID)."
                )
            except ValueError:
                return (
                    None,
                    None,
                    f"Invalid ID in download path segment: {match_download.group(1)}",
                )

        # Priority 3: Check path for /models/(\d+)
        # This is usually a base model ID, but could be overridden by query/download path
        match_model = re.search(r"/models/(\d+)", path)
        if match_model:
            try:
                model_id_from_path = int(match_model.group(1))
                print(
                    f"Found ID {model_id_from_path} in model URL path (treating as model ID unless overridden)."
                )
            except ValueError:
                return (
                    None,
                    None,
                    f"Invalid ID in model path segment: {match_model.group(1)}",
                )

        # --- Decision Phase ---

        # If we got a version ID from the query string, that takes precedence
        if model_version_id_from_query is not None:
            api_url = f"https://civitai.com/api/v1/model-versions/{model_version_id_from_query}"
            filename_base = f"model_version_{model_version_id_from_query}_metadata"
            print(
                f"Using Model Version ID from query parameter: {model_version_id_from_query}"
            )
            return api_url, filename_base, None

        # If we got a version ID from the download path (and not from query), use that
        elif model_version_id_from_path is not None:
            api_url = f"https://civitai.com/api/v1/model-versions/{model_version_id_from_path}"
            filename_base = f"model_version_{model_version_id_from_path}_metadata"
            print(
                f"Using Model Version ID from download path: {model_version_id_from_path}"
            )
            return api_url, filename_base, None

        # If we only got a model ID from the model path, use that
        elif model_id_from_path is not None:
            api_url = f"https://civitai.com/api/v1/models/{model_id_from_path}"
            filename_base = f"model_{model_id_from_path}_metadata"
            print(f"Using Model ID from model path: {model_id_from_path}")
            return api_url, filename_base, None

        # If nothing was found
        else:
            return (
                None,
                None,
                "Could not extract a valid Model ID or Model Version ID from the URL path or query string.",
            )

    except Exception as e:
        return None, None, f"An unexpected error occurred during URL parsing: {e}"


# --- The rest of the script remains the same ---


def fetch_civitai_metadata(api_url: str, api_key: str) -> dict:
    """
    Fetches metadata from a specific Civitai API endpoint.

    Args:
        api_url: The full URL of the API endpoint to fetch.
        api_key: The Civitai API key.

    Returns:
        A dictionary containing the metadata.

    Raises:
        requests.exceptions.RequestException: If the API request fails.
        ValueError: If the API response is not valid JSON.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print(f"Fetching metadata from: {api_url}")

    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()  # Check for 4xx/5xx errors
        metadata = response.json()
        print("Successfully fetched metadata.")
        return metadata

    except requests.exceptions.HTTPError as e:
        print(
            f"HTTP Error: {e.response.status_code} {e.response.reason}", file=sys.stderr
        )
        print(f"Response body: {e.response.text}", file=sys.stderr)
        if e.response.status_code == 401:
            print(
                "Error 401: Unauthorized. Check if your API key is correct and has permissions.",
                file=sys.stderr,
            )
        elif e.response.status_code == 404:
            print(
                f"Error 404: Not Found. Check if the ID derived from the URL exists at the determined endpoint ({api_url}).",
                file=sys.stderr,
            )
        raise
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON response: {e}", file=sys.stderr)
        print(f"Response text: {response.text}", file=sys.stderr)
        raise ValueError("Invalid JSON received from API") from e


def save_metadata_to_json(metadata: dict, filename: str):
    """
    Saves the metadata dictionary to a JSON file.

    Args:
        metadata: The dictionary containing the metadata.
        filename: The name of the file to save the JSON data to.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        print(f"Metadata successfully saved to: {filename}")
    except IOError as e:
        print(f"Error saving file {filename}: {e}", file=sys.stderr)
        sys.exit(1)  # Exit if we can't save


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Civitai model or model version metadata from a URL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  ./civdata "https://civitai.com/models/12345/cool-model-name"
  ./civdata "https://civitai.com/models/12345?modelVersionId=67890"
  ./civdata "https://civitai.com/api/download/models/67890?type=Model&format=SafeTensor"
  ./civdata "https://civitai.com/models/12345/cool-model-name?modelVersionId=67890" -o my_metadata.json
""",
    )
    parser.add_argument(
        "url", help="The Civitai URL (e.g., for a model page or a download link)"
    )
    parser.add_argument("-o", "--output", help="Optional output JSON filename.")

    args = parser.parse_args()

    # --- Get API Key ---
    api_key = os.getenv("CIVITAPI")
    if not api_key:
        print("Error: CIVITAPI environment variable not set.", file=sys.stderr)
        print(
            "Please set the environment variable: export CIVITAPI='your_api_key_here'",
            file=sys.stderr,
        )
        sys.exit(1)
    # print("Using API key from CIVITAPI environment variable.") # Can uncomment for verbosity

    # --- Parse URL ---
    target_api_url, filename_base, error_msg = parse_civitai_url(args.url)

    if error_msg:
        print(f"Error parsing URL: {error_msg}", file=sys.stderr)
        sys.exit(1)
    if not target_api_url or not filename_base:
        print(
            f"Error: Could not determine API endpoint from URL: {args.url}",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Determine Output Filename ---
    output_filename = args.output or f"{filename_base}.json"

    # --- Fetch and Save Metadata ---
    try:
        metadata = fetch_civitai_metadata(target_api_url, api_key)

        # Create a more descriptive filename if we have model version metadata
        if not args.output and "model" in metadata and "type" in metadata["model"]:
            # Use model.type instead of files.type for the model type
            model_type = metadata["model"]["type"].lower()
            model_id = metadata.get("id", "unknown")
            output_filename = f"{model_type}_{model_id}_metadata.json"
            print(
                f"Using auto-generated filename based on model type: {output_filename}"
            )

        save_metadata_to_json(metadata, output_filename)
    except (requests.exceptions.RequestException, ValueError):
        # Specific errors are already printed in the fetching function
        print("\nFailed to retrieve or process metadata.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # Catch any other unexpected errors
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
