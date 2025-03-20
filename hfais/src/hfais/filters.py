# FILE_LOCATION: hfais/src/hfais/filters.py
"""
# PURPOSE: Provide advanced filtering capabilities for HuggingFace model search results.

## INTERFACES:
 - filter_by_size(models: list, min_size: int, max_size: int) -> list: Filter models by size range.
 - filter_by_creator(models: list, creator: str) -> list: Filter models by creator.

## DEPENDENCIES:
 - typing: For type annotations.
"""
from typing import List, Dict

def filter_by_size(models: List[Dict], min_size: int, max_size: int) -> List[Dict]:
    """
    PURPOSE: Filter models by size range.

    PARAMS:
        models: A list of model metadata.
        min_size: The minimum size (in billions of parameters).
        max_size: The maximum size (in billions of parameters).

    RETURNS:
        A list of models within the specified size range.
    """
    return [
        model for model in models
        if min_size <= model.get("size", 0) <= max_size
    ]

def filter_by_creator(models: List[Dict], creator: str) -> List[Dict]:
    """
    PURPOSE: Filter models by creator.

    PARAMS:
        models: A list of model metadata.
        creator: The creator's name to filter by.

    RETURNS:
        A list of models created by the specified creator.
    """
    return [
        model for model in models
        if model.get("creator", "").lower() == creator.lower()
    ]
"""
## KNOWN ERRORS: None

## IMPROVEMENTS: Initial implementation.

## FUTURE TODOs:
 - Add more filtering criteria (e.g., tags, architecture).
 - Handle cases where metadata is incomplete.
"""