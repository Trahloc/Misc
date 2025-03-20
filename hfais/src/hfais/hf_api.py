# FILE_LOCATION: hfais/src/hfais/hf_api.py
"""
# PURPOSE: Interact with the HuggingFace API to perform searches and cache results locally.

## INTERFACES:
 - search_hf_models(query: str) -> list: Perform a search on HuggingFace.co.
 - cache_results(results: list, cache_path: str) -> None: Cache search results locally.
 - load_cached_results(cache_path: str) -> list: Load cached search results.

## DEPENDENCIES:
 - requests: For making API calls.
 - json: For handling cached data.
"""
import requests
import json
from typing import List

API_URL = "https://huggingface.co/api/models"

def search_hf_models(query: str) -> List[dict]:
    """
    PURPOSE: Perform a search on HuggingFace.co.

    PARAMS:
        query: The search query string.

    RETURNS:
        A list of model metadata matching the query.
    """
    response = requests.get(API_URL, params={"search": query})
    response.raise_for_status()
    return response.json()

def cache_results(results: List[dict], cache_path: str) -> None:
    """
    PURPOSE: Cache search results locally.

    PARAMS:
        results: The list of model metadata to cache.
        cache_path: The file path to store the cached results.

    RETURNS: None
    """
    with open(cache_path, "w") as f:
        json.dump(results, f)

def load_cached_results(cache_path: str) -> List[dict]:
    """
    PURPOSE: Load cached search results.

    PARAMS:
        cache_path: The file path to load cached results from.

    RETURNS:
        A list of cached model metadata.
    """
    with open(cache_path, "r") as f:
        return json.load(f)
"""
## KNOWN ERRORS: None

## IMPROVEMENTS: Initial implementation.

## FUTURE TODOs:
 - Add error handling for network issues.
 - Implement cache expiration.
"""